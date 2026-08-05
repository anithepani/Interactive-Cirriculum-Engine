"""Shared yt-dlp option helpers: PO Token auth + client rotation.

YouTube enforces Proof-of-Origin (PO) Tokens for datacenter IPs. We use the
bgutil-ytdlp-pot-provider sidecar (http://pot-provider:4416) which auto-generates
per-video PO tokens via BgUtils. yt-dlp's bgutil plugin picks up the base URL
from the extractor arg and handles token injection transparently.

Cookies are NOT used — they kept getting rotated/invalidated on the server. A
dedicated-service-account cookie tier is planned (see docs) but not wired here.

Two distinct YouTube rejections are handled separately:

  bot_blocked     — "Sign in to confirm you're not a bot": an IP/heuristic
                    block on the datacenter egress. The PO token bypasses this.
  login_required  — the video's playability status is LOGIN_REQUIRED for that
                    client: YouTube demands an authenticated session. The PO
                    token does NOT bypass this; only a different (still-trusted)
                    client or cookies can. We rotate clients hoping one is still
                    trusted anonymously.

Both are recoverable by trying the next client, so rotation advances on either.
They are classified and logged separately so metrics can tell an IP-reputation
block apart from an auth-required video (they need different escalations).

Client rotation order (YT_PLAYER_CLIENTS env, default below):
  mweb        — maintainer-recommended with PO token (GVS)
  tv_embedded — survives LOGIN_REQUIRED waves longest; PO token compatible
  web_safari  — HLS formats, no GVS PO token required
  android_vr  — often still trusted anonymously when web clients are escalated
  tv          — no PO token required; DRM'd if no cookies (acceptable for public)
"""
from __future__ import annotations

import copy
import logging
import os
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

# Default player clients, tried in order on a recoverable block. Expanded beyond
# the original mweb,web_safari,tv to add tv_embedded + android_vr, which tend to
# stay anonymously trusted through the LOGIN_REQUIRED enforcement waves that
# escalate the web-family clients. Overridable via YT_PLAYER_CLIENTS.
_DEFAULT_CLIENTS = "mweb,tv_embedded,web_safari,android_vr,tv"

# User-facing guidance appended when every player client is exhausted. The
# worker surfaces one of these so the user can fall back to direct file upload
# (Tier 3). The message differs by failure class so the user understands why.
UPLOAD_FALLBACK_HINT = (
    "YouTube blocked this download from our server (bot-check / PO-token "
    "enforcement) across all available methods. Please download the video "
    "and use the direct file upload option instead."
)
LOGIN_REQUIRED_FALLBACK_HINT = (
    "YouTube requires sign-in to fetch this particular video from our server, "
    "so it can't be downloaded automatically. Please download the video and "
    "use the direct file upload option instead."
)

# Substrings of YouTube's rejections, matched case-insensitively.
_BOT_BLOCK_MARKER = "sign in to confirm you"
# yt-dlp surfaces the playability status in the error text when a client is
# escalated to an authenticated session (e.g. "... playability status:
# LOGIN_REQUIRED" / "This video requires payment"/ members-only).
_LOGIN_REQUIRED_MARKERS = (
    "login_required",
    "sign in to confirm your age",
    "this video is only available to members",
    "join this channel",
    "video is private",
)


def _pot_base_url() -> str | None:
    """PO Token provider sidecar base URL, read at call time."""
    return os.environ.get("YT_POT_PROVIDER_BASE_URL") or None


def get_clients() -> list[str]:
    """Return the ordered list of player clients to try (read at call time)."""
    raw = os.environ.get("YT_PLAYER_CLIENTS", _DEFAULT_CLIENTS)
    return [c.strip() for c in raw.split(",") if c.strip()]


def apply_auth(opts: dict, client: str | None = None) -> dict:
    """Attach PO Token provider + player client to *opts*.

    Uses the first configured client when *client* is None. Mutates and
    returns *opts* so it can be used inline: ``opts = apply_auth(opts)``.
    """
    ea = opts.setdefault("extractor_args", {})
    yt_args: list[str] = ea.setdefault("youtube", [])

    clients = get_clients()
    chosen = client or (clients[0] if clients else "mweb")
    yt_args.append(f"player_client={chosen}")

    pot_base = _pot_base_url()
    if pot_base:
        # bgutil plugin reads this extractor arg to locate the HTTP sidecar.
        ea.setdefault("youtubepot-bgutilhttp", []).append(f"base_url={pot_base}")
    else:
        logger.warning(
            "YT_POT_PROVIDER_BASE_URL is not set — PO Token provider sidecar "
            "is unavailable. YouTube may block downloads from this datacenter "
            "IP. Set YT_POT_PROVIDER_BASE_URL=http://pot-provider:4416 in the "
            "worker environment."
        )

    return opts


def is_bot_block(exc: BaseException) -> bool:
    """True when *exc* is YouTube's 'confirm you're not a bot' rejection."""
    return _BOT_BLOCK_MARKER in str(exc).lower()


def is_login_required(exc: BaseException) -> bool:
    """True when *exc* is a LOGIN_REQUIRED / members-only auth rejection.

    Note: YouTube frequently renders a LOGIN_REQUIRED playability status as the
    generic bot-check string, so a bot-block match does not rule this out. Use
    :func:`classify_block` for the precedence-correct label.
    """
    text = str(exc).lower()
    return any(marker in text for marker in _LOGIN_REQUIRED_MARKERS)


def classify_block(exc: BaseException) -> str | None:
    """Classify *exc* as ``"login_required"``, ``"bot_blocked"`` or ``None``.

    LOGIN_REQUIRED takes precedence over the generic bot-check string because
    YouTube renders an auth-required video using the same "confirm you're not a
    bot" text — the specific marker is the more accurate signal. Returns
    ``None`` when *exc* is neither (caller should re-raise).
    """
    if is_login_required(exc):
        return "login_required"
    if is_bot_block(exc):
        return "bot_blocked"
    return None


class YouTubeBotBlockError(RuntimeError):
    """Raised when every player client is exhausted by YouTube.

    Carries a user-facing hint so the worker can surface the direct-upload
    fallback (Tier 3) instead of a raw stack trace. :attr:`reason` records the
    dominant failure class (``"bot_blocked"`` or ``"login_required"``) so the
    worker can tailor the message and metrics can attribute the failure.
    """

    def __init__(self, message: str, reason: str = "bot_blocked") -> None:
        super().__init__(message)
        self.reason = reason


def run_with_client_rotation(
    run: Callable[[dict], _T],
    base_opts: dict,
    operation: str = "extract",
) -> _T:
    """Run *run(opts)* across the configured player clients until one works.

    *run* receives a fresh copy of *base_opts* with auth applied for each
    client and should perform the yt-dlp call. On a recoverable block
    (bot-block or LOGIN_REQUIRED) it advances to the next client; on any other
    error it re-raises immediately. If every client is exhausted it raises
    :class:`YouTubeBotBlockError`, whose ``reason`` reflects the last block
    class seen (login_required is preferred so the user gets the accurate hint).
    """
    clients = get_clients() or [None]  # type: ignore[list-item]
    last_exc: BaseException | None = None
    saw_login_required = False
    for client in clients:
        opts = apply_auth(copy.deepcopy(base_opts), client=client)
        try:
            result = run(opts)
        except Exception as exc:  # noqa: BLE001 — inspected below
            block = classify_block(exc)
            if block is not None:
                saw_login_required = saw_login_required or block == "login_required"
                logger.warning(
                    "youtube operation=%s player_client=%s result=%s; trying next client",
                    operation,
                    client,
                    block,
                )
                last_exc = exc
                continue
            logger.warning(
                "youtube operation=%s player_client=%s result=failed error_type=%s error=%s",
                operation,
                client,
                type(exc).__name__,
                exc,
            )
            raise
        else:
            logger.info(
                "youtube operation=%s player_client=%s result=ok",
                operation,
                client,
            )
            return result

    reason = "login_required" if saw_login_required else "bot_blocked"
    hint = LOGIN_REQUIRED_FALLBACK_HINT if saw_login_required else UPLOAD_FALLBACK_HINT
    logger.error(
        "youtube operation=%s result=exhausted reason=%s clients=%s",
        operation,
        reason,
        ",".join(str(c) for c in clients),
    )
    raise YouTubeBotBlockError(hint, reason=reason) from last_exc


__all__ = [
    "LOGIN_REQUIRED_FALLBACK_HINT",
    "UPLOAD_FALLBACK_HINT",
    "YouTubeBotBlockError",
    "apply_auth",
    "classify_block",
    "get_clients",
    "is_bot_block",
    "is_login_required",
    "run_with_client_rotation",
]
