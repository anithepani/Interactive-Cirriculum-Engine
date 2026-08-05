# Runbook / Plan: YouTube cookie-auth tier (Phase 2 — NOT YET IMPLEMENTED)

Status: **Planning only.** This document describes a proposed escalation tier for
YouTube videos that return `LOGIN_REQUIRED` on *every* anonymous player client.
No cookie code is wired into the ingestion path today. Decide whether to
implement based on the residual failure rate after Phase 1 (expanded client
rotation) is in production.

## When this tier is needed

Phase 1 recovers videos where at least one player client
(`mweb,tv_embedded,web_safari,android_vr,tv`) is still anonymously trusted with
the PO token. A video reaches this tier only when **all** clients return
`login_required` — i.e. YouTube demands an authenticated session for that
specific video/IP combination. The worker currently surfaces the
`LOGIN_REQUIRED_FALLBACK_HINT` (direct upload) for these. This tier would try
authenticated extraction before falling back to user upload.

## Why the previous cookie attempt failed (and what's different here)

The prior approach (commits `d93e943` → reverted in `845b9f1`) used **personal
Google-account cookies** sent on **every** request. It failed because:

1. YouTube ties session cookies to the origin IP/session and **revokes them**
   when it detects datacenter reuse — cookies "expired" within hours/days.
2. Nobody refreshed the cookie file, so once invalidated the whole YT path broke.
3. Sending cookies on every request maximized exposure and invalidation rate.

This plan differs on three axes:

- **Dedicated throwaway service account** — never used interactively elsewhere,
  low value if burned, isolated from any real user.
- **Cookies paired with the PO token** — bgutil can mint a GVS token bound to the
  authenticated `visitor_data`, which is markedly more stable than cookies alone.
- **Cookies used only as the final rotation step** — invoked *only* after all
  anonymous clients report `login_required`, minimizing exposure/invalidation.

Cookies remain a genuine liability; treat this tier as a targeted escalation,
not a default.

## Proposed design

### Trigger point
In `run_with_client_rotation` (`libs/ai/ingestion/src/ice_ingestion/_ytdlp.py`),
after the anonymous client loop is exhausted with `reason == "login_required"`,
attempt one additional pass with `web` (and/or `mweb`) using a cookiefile —
**only** if `YT_COOKIEFILE` env is set. If unset (default), behavior is exactly
as today (raise `YouTubeBotBlockError`). Bot-blocked exhaustion does NOT trigger
the cookie tier (the PO token already handles bot-detection).

### Code sketch (do not commit until approved)
```python
def _cookiefile() -> str | None:
    path = os.environ.get("YT_COOKIEFILE")
    return path if path and os.path.exists(path) else None

# inside run_with_client_rotation, after the anonymous loop, before raising:
if saw_login_required and _cookiefile():
    for client in ("web", "mweb"):
        opts = apply_auth(copy.deepcopy(base_opts), client=client)
        opts["cookiefile"] = _cookiefile()
        try:
            result = run(opts)
        except Exception as exc:
            if classify_block(exc) is not None:
                logger.warning("youtube cookie-tier client=%s still blocked", client)
                continue
            raise
        else:
            logger.info("youtube cookie-tier client=%s result=ok", client)
            return result
```

### Account & cookie provisioning
1. Create a throwaway Google account used *only* for ICE ingestion. Enable no 2FA
   recovery tied to real identities.
2. Export cookies **from the same egress path as production** (ideally from the
   VM itself or a proxy sharing its IP) using a browser extension or
   `yt-dlp --cookies-from-browser` on a controlled machine. Save as Netscape
   `cookies.txt` format.
3. Store as a **Docker secret / bind-mounted file**, never in the image or git:
   ```yaml
   # docker-compose.prod.yml (worker service) — proposed
   secrets:
     - yt_cookies
   environment:
     - YT_COOKIEFILE=/run/secrets/yt_cookies
   # top-level:
   secrets:
     yt_cookies:
       file: /opt/ice/secrets/yt_cookies.txt   # 0600, root-owned, on VM only
   ```

### Cookie freshness automation (the part that was missing last time)
Cookies "expiring on the server" was the root operational failure. Options,
cheapest first:
- **Manual monthly rotation** driven by an alert: extend `check_youtube.sh` to
  probe a known `LOGIN_REQUIRED` video via the cookie tier and alert when it
  fails, prompting a re-export. Lowest effort, human in the loop.
- **Scheduled headless re-export**: a small sidecar/cron running an authenticated
  headless session that re-exports cookies to the mounted secret on a schedule.
  Higher effort, higher reliability. Requires storing account credentials as a
  separate secret — increases blast radius; weigh carefully.

Recommendation: start with manual rotation + alerting; automate only if the
`login_required` volume justifies it.

## Security considerations
- Cookies grant access to the service account — scope it to nothing valuable.
- Secret file: `0600`, root-owned, on the VM only, never committed (already
  covered by `.gitignore`: `cookies.txt`, `*.cookies`, `yt_cookies*.txt`).
- Rotate/revoke by signing the account out of all sessions (invalidates the file).
- Log only that the cookie tier ran and its outcome — never cookie contents.

## Observability additions (when implemented)
- Emit `youtube tier=cookie result=<ok|blocked|failed>` so dashboards show how
  often the cookie tier carries load — a rising trend signals the anonymous
  clients are being escalated en masse (next enforcement wave).
- Track cookie age; alert before the typical invalidation horizon.

## Decision checklist before implementing
- [ ] Residual `login_required` exhaustion rate after Phase 1 is high enough to justify cookie risk.
- [ ] A throwaway account is provisioned and isolated.
- [ ] Cookie export path shares the production egress IP.
- [ ] Freshness/rotation process (manual or automated) is agreed and owned.
- [ ] Secret mounting reviewed (no image/git exposure).

## Related
- Phase 1 (implemented): `libs/ai/ingestion/src/ice_ingestion/_ytdlp.py` —
  `classify_block`, expanded client rotation, `YouTubeBotBlockError.reason`.
- Phase 3 (implemented): reason-specific user hints + structured logging.
- Terminal fallback (implemented): direct file upload
  (`apps/worker/src/ice_worker/tasks/generate_curriculum.py`).
