"""Shared yt-dlp option helpers: cookie auth + observable fallback.

Server IPs (e.g. the production Azure VM) are aggressively bot-detected by
YouTube. Passing a logged-in ``cookies.txt`` (Netscape format) is the only
reliable way to download / read captions from those hosts. The cookie path is
resolved from the ``YT_COOKIE_FILE`` environment variable (default
``/app/cookies.txt``) so it can be mounted read-only into the worker container
without living in the git checkout.

When no cookie file is present we log a loud warning and fall back to the
anonymous ``player_client=android`` extractor. That fallback is now routinely
blocked by YouTube ("Sign in to confirm you're not a bot"); callers should use
:func:`is_bot_block` to turn that raw error into an actionable failure.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

DEFAULT_COOKIE_PATH = "/app/cookies.txt"

# Substring of YouTube's bot-detection error, matched case-insensitively.
_BOT_BLOCK_MARKER = "sign in to confirm you"


def cookie_path() -> str:
    """Return the configured cookie path (env ``YT_COOKIE_FILE`` or default)."""
    return os.environ.get("YT_COOKIE_FILE", DEFAULT_COOKIE_PATH)


def cookie_file() -> str | None:
    """Return the cookie path if it exists on disk, else ``None``."""
    path = cookie_path()
    return path if path and os.path.exists(path) else None


def apply_auth(opts: dict) -> dict:
    """Attach cookie auth to *opts*; else warn loudly and use the anon client.

    Mutates and returns *opts* so it can be used inline::

        opts = apply_auth(opts)
    """
    cf = cookie_file()
    if cf:
        opts["cookiefile"] = cf
    else:
        logger.warning(
            "YT_COOKIE_FILE not found (looked at %s) — falling back to the "
            "anonymous youtube client. YouTube may reject this with a "
            "bot-check; refresh cookies.txt to restore authenticated access.",
            cookie_path(),
        )
        opts["extractor_args"] = {"youtube": ["player_client=android"]}
    return opts


def is_bot_block(exc: BaseException) -> bool:
    """True when *exc* is YouTube's "confirm you're not a bot" rejection."""
    return _BOT_BLOCK_MARKER in str(exc).lower()


__all__ = [
    "DEFAULT_COOKIE_PATH",
    "apply_auth",
    "cookie_file",
    "cookie_path",
    "is_bot_block",
]
