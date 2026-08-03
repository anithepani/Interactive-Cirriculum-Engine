"""Shared yt-dlp option helpers: PO Token auth + client rotation.

YouTube enforces Proof-of-Origin (PO) Tokens for datacenter IPs. We use the
bgutil-ytdlp-pot-provider sidecar (http://pot-provider:4416) which auto-generates
per-video PO tokens via BgUtils. yt-dlp's bgutil plugin picks up the base URL
from the extractor arg and handles token injection transparently.

Cookies are NOT used — they kept getting rotated/invalidated on the server.

Client rotation order (YT_PLAYER_CLIENTS env, default: mweb,web_safari,tv):
  mweb       — maintainer-recommended with PO token (GVS)
  web_safari — HLS formats, no GVS PO token required
  tv         — no PO token required; DRM'd if no cookies (acceptable for public)
"""
from __future__ import annotations

import logging
import os
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

# User-facing guidance appended when every player client is bot-blocked. The
# worker surfaces this so the user can fall back to direct file upload (Tier 3).
UPLOAD_FALLBACK_HINT = (
    "YouTube blocked this download from our server (bot-check / PO-token "
    "enforcement) across all available methods. Please download the video "
    "and use the direct file upload option instead."
)

# Substring of YouTube's bot-detection error, matched case-insensitively.
_BOT_BLOCK_MARKER = "sign in to confirm you"

# PO Token provider sidecar base URL (set via YT_POT_PROVIDER_BASE_URL in compose).
_POT_BASE_URL: str | None = os.environ.get("YT_POT_PROVIDER_BASE_URL")

# Ordered player clients to try on bot-block.
_CLIENTS: list[str] = [
    c.strip()
    for c in os.environ.get("YT_PLAYER_CLIENTS", "mweb,web_safari,tv").split(",")
    if c.strip()
]


def get_clients() -> list[str]:
    """Return the ordered list of player clients to try."""
    return _CLIENTS


def apply_auth(opts: dict, client: str | None = None) -> dict:
    """Attach PO Token provider + player client to *opts*.

    Uses the first configured client when *client* is None. Mutates and
    returns *opts* so it can be used inline: ``opts = apply_auth(opts)``.
    """
    ea = opts.setdefault("extractor_args", {})
    yt_args: list[str] = ea.setdefault("youtube", [])

    chosen = client or (_CLIENTS[0] if _CLIENTS else "mweb")
    yt_args.append(f"player_client={chosen}")

    if _POT_BASE_URL:
        # bgutil plugin reads this extractor arg to locate the HTTP sidecar.
        ea.setdefault("youtubepot-bgutilhttp", []).append(
            f"base_url={_POT_BASE_URL}"
        )
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


class YouTubeBotBlockError(RuntimeError):
    """Raised when every player client is bot-blocked by YouTube.

    Carries the user-facing :data:`UPLOAD_FALLBACK_HINT` so the worker can
    surface the direct-upload fallback (Tier 3) instead of a raw stack trace.
    """


def run_with_client_rotation(
    run: Callable[[dict], _T],
    base_opts: dict,
) -> _T:
    """Run *run(opts)* across the configured player clients until one works.

    *run* receives a fresh copy of *base_opts* with auth applied for each
    client and should perform the yt-dlp call. On a bot-block it advances to
    the next client; on any other error it re-raises immediately. If every
    client is bot-blocked it raises :class:`YouTubeBotBlockError`.
    """
    clients = get_clients() or [None]  # type: ignore[list-item]
    last_exc: BaseException | None = None
    for client in clients:
        opts = apply_auth(dict(base_opts), client=client)
        try:
            return run(opts)
        except Exception as exc:  # noqa: BLE001 — inspected below
            if is_bot_block(exc):
                logger.warning(
                    "player_client=%s bot-blocked by YouTube; trying next client",
                    client,
                )
                last_exc = exc
                continue
            raise
    raise YouTubeBotBlockError(UPLOAD_FALLBACK_HINT) from last_exc


__all__ = [
    "UPLOAD_FALLBACK_HINT",
    "YouTubeBotBlockError",
    "apply_auth",
    "get_clients",
    "is_bot_block",
    "run_with_client_rotation",
]
