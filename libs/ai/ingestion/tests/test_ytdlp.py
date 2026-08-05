"""Tests for yt-dlp auth + client rotation logic (ice_ingestion._ytdlp)."""
import os
from unittest.mock import patch

import pytest

from ice_ingestion._ytdlp import (
    YouTubeBotBlockError,
    classify_block,
    is_bot_block,
    is_login_required,
    run_with_client_rotation,
)


def test_rotation_uses_fresh_nested_options():
    """Client rotation must not mutate the caller's base_opts dict."""
    with patch.dict(os.environ, {"YT_PLAYER_CLIENTS": "mweb,tv", "YT_POT_PROVIDER_BASE_URL": "http://provider:4416"}):
        seen = []

        def run(options):
            seen.append(options)
            if len(seen) == 1:
                raise RuntimeError("Sign in to confirm you're not a bot")
            return "ok"

        base = {"extractor_args": {"custom": ["unchanged=true"]}}
        assert run_with_client_rotation(run, base, operation="test") == "ok"
        # Base must remain untouched.
        assert base == {"extractor_args": {"custom": ["unchanged=true"]}}
        # Each call got its own player_client.
        assert seen[0]["extractor_args"]["youtube"] == ["player_client=mweb"]
        assert seen[1]["extractor_args"]["youtube"] == ["player_client=tv"]


def test_classify_login_required_takes_precedence():
    """LOGIN_REQUIRED is classified even when the error text also contains the bot marker."""
    # YouTube often renders LOGIN_REQUIRED as the generic bot-check string.
    exc_both = RuntimeError("Sign in to confirm you're not a bot. playability status: LOGIN_REQUIRED")
    assert classify_block(exc_both) == "login_required"
    assert is_login_required(exc_both)
    assert is_bot_block(exc_both)  # still matches, but classify chose login_required


def test_classify_bot_blocked():
    """A pure bot-check error is classified as bot_blocked."""
    exc = RuntimeError("Sign in to confirm you're not a bot. This helps protect our community.")
    assert classify_block(exc) == "bot_blocked"
    assert is_bot_block(exc)
    assert not is_login_required(exc)


def test_classify_unrelated_error():
    """An unrelated error is not classified as either block type."""
    exc = RuntimeError("HTTP 500 internal server error")
    assert classify_block(exc) is None
    assert not is_bot_block(exc)
    assert not is_login_required(exc)


def test_rotation_exhausted_bot_blocked():
    """When every client is bot-blocked, YouTubeBotBlockError carries reason=bot_blocked."""
    with patch.dict(os.environ, {"YT_PLAYER_CLIENTS": "mweb,tv"}):
        def run(opts):
            raise RuntimeError("Sign in to confirm you're not a bot")

        with pytest.raises(YouTubeBotBlockError) as exc_info:
            run_with_client_rotation(run, {}, operation="test")

        exc = exc_info.value
        assert exc.reason == "bot_blocked"
        assert "blocked this download" in str(exc)


def test_rotation_exhausted_login_required():
    """When every client returns LOGIN_REQUIRED, the reason is login_required."""
    with patch.dict(os.environ, {"YT_PLAYER_CLIENTS": "mweb,tv"}):
        def run(opts):
            raise RuntimeError("playability status: LOGIN_REQUIRED")

        with pytest.raises(YouTubeBotBlockError) as exc_info:
            run_with_client_rotation(run, {}, operation="test")

        exc = exc_info.value
        assert exc.reason == "login_required"
        assert "requires sign-in" in str(exc)


def test_rotation_mixed_blocks_prefers_login_required():
    """When one client is bot-blocked and another is LOGIN_REQUIRED, reason=login_required."""
    with patch.dict(os.environ, {"YT_PLAYER_CLIENTS": "mweb,tv"}):
        call_count = [0]

        def run(opts):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Sign in to confirm you're not a bot")
            raise RuntimeError("playability status: LOGIN_REQUIRED")

        with pytest.raises(YouTubeBotBlockError) as exc_info:
            run_with_client_rotation(run, {}, operation="test")

        exc = exc_info.value
        assert exc.reason == "login_required"


def test_rotation_succeeds_second_client():
    """When the first client is blocked and the second succeeds, the result is returned."""
    with patch.dict(os.environ, {"YT_PLAYER_CLIENTS": "mweb,tv"}):
        call_count = [0]

        def run(opts):
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Sign in to confirm you're not a bot")
            return {"id": "test", "title": "Test video"}

        result = run_with_client_rotation(run, {}, operation="metadata")
        assert result["id"] == "test"


def test_rotation_reraises_non_recoverable_error():
    """A non-recoverable error (not bot-block / LOGIN_REQUIRED) is immediately re-raised."""
    with patch.dict(os.environ, {"YT_PLAYER_CLIENTS": "mweb,tv"}):
        def run(opts):
            raise ValueError("Invalid video ID")

        with pytest.raises(ValueError, match="Invalid video ID"):
            run_with_client_rotation(run, {}, operation="test")


def test_expanded_client_list():
    """The new default client list includes tv_embedded and android_vr."""
    with patch.dict(os.environ, {}, clear=True):
        # No YT_PLAYER_CLIENTS set → should use the new default.
        from ice_ingestion._ytdlp import get_clients

        clients = get_clients()
        assert "mweb" in clients
        assert "tv_embedded" in clients
        assert "android_vr" in clients
        assert "web_safari" in clients
        assert "tv" in clients
        # Order matters: tv_embedded should come before web_safari to survive waves longer.
        assert clients.index("tv_embedded") < clients.index("web_safari")
