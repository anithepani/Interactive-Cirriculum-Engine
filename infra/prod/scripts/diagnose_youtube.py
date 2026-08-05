"""Run a per-video, per-client yt-dlp diagnostic from the worker container."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

import yt_dlp

from ice_ingestion._ytdlp import apply_auth, is_bot_block


def _result(video: str, client: str, phase: str, **details) -> None:
    print(json.dumps({"video": video, "client": client, "phase": phase, **details}))


def _metadata(video: str, client: str, verbose: bool) -> dict | None:
    opts = apply_auth(
        {
            "skip_download": True,
            "noplaylist": True,
            "quiet": not verbose,
            "verbose": verbose,
        },
        client=client,
    )
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video, download=False) or {}
        _result(
            video,
            client,
            "metadata",
            status="ok",
            id=info.get("id"),
            title=info.get("title"),
            availability=info.get("availability"),
            age_limit=info.get("age_limit"),
            playable_in_embed=info.get("playable_in_embed"),
            live_status=info.get("live_status"),
            format_count=len(info.get("formats") or []),
        )
        return info
    except Exception as exc:  # diagnostic must continue through the matrix
        _result(
            video,
            client,
            "metadata",
            status="bot_blocked" if is_bot_block(exc) else "failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return None


def _sample(video: str, client: str, verbose: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="ice_youtube_diag_") as tmp:
        output = str(Path(tmp) / "sample.%(ext)s")
        opts = apply_auth(
            {
                "format": "best[height<=480]/best",
                "download_sections": ["*0-3"],
                "force_keyframes_at_cuts": True,
                "outtmpl": output,
                "noplaylist": True,
                "quiet": not verbose,
                "verbose": verbose,
            },
            client=client,
        )
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([video])
            files = [p for p in Path(tmp).iterdir() if p.is_file()]
            _result(
                video,
                client,
                "media_sample",
                status="ok",
                bytes=sum(p.stat().st_size for p in files),
            )
        except Exception as exc:
            _result(
                video,
                client,
                "media_sample",
                status="bot_blocked" if is_bot_block(exc) else "failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("videos", nargs="+")
    parser.add_argument(
        "--clients",
        default=os.getenv("YT_PLAYER_CLIENTS", "mweb,web_safari,tv"),
    )
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print(json.dumps({"yt_dlp_version": yt_dlp.version.__version__}))
    for video in args.videos:
        for client in (c.strip() for c in args.clients.split(",") if c.strip()):
            info = _metadata(video, client, args.verbose)
            if args.sample and info is not None:
                _sample(video, client, args.verbose)


if __name__ == "__main__":
    main()
