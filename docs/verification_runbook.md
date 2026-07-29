# Verification Runbook — Performance, Upload & Difficulty (Phases 1–5)

This runbook describes how to manually verify the features delivered on the
`feat/performance-upload-difficulty` branch (Phases 1–5) before merging. Each
section lists the steps to trigger the feature, the logs/DB fields to confirm
it worked, and the expected result.

> **Scope:** manual verification only. No code changes are required — all
> features are behind the existing stack and are zero-regression (existing
> YouTube curricula and pre-migration rows keep working unchanged).

---

## 0. Branch state & included commits

The branch should be clean and contain the Phase 1–5 commits below (plus any
bug-fix commits). Confirm with:

```bash
git status                         # working tree clean
git log --oneline main..HEAD
```

Expected commits (hashes may differ after rebase):

| Phase | Commit message |
| --- | --- |
| 1 | `perf: fix signal video trigger + optimise vision pipeline` |
| 2 | `feat: local video file upload pipeline (Phase 2)` |
| 3 | `feat: HTML5 player for uploads + wire frontend submit + presigned video endpoint` |
| 4 | `feat: add difficulty selector + exercise grounding with transcript` |
| 5 | `feat: dynamic exercise type relevance with content classifier` |

Files touched (summary): `apps/api/.../curricula.py`, `apps/web/.../upload/page.tsx`,
`apps/web/.../curriculum/[id]/page.tsx`, `apps/worker/.../generate_curriculum.py`,
`apps/worker/.../signal_video.py`, `apps/worker/.../recap.py`,
`libs/ai/ingestion/.../downloader.py`, `libs/ai/vision/.../extractor.py`,
`libs/ai/checkpoints/.../{placer,classifier}.py`,
`libs/ai/exercise_gen/.../generator.py`, `libs/shared/.../settings.py`,
and the additive migration `add_curriculum_difficulty.py`.

---

## 1. Prerequisites — migrations & restart

### 1.1 Apply the difficulty migration

Phase 4 adds a nullable `difficulty` column to `curricula` (default `'medium'`).
A standalone, idempotent migration script ships at the repo root:

```bash
# From the repo root (or the space-free junction D:\ice on Windows)
python add_curriculum_difficulty.py
```

What it does (safe to run multiple times):

- `ALTER TABLE curricula ADD COLUMN IF NOT EXISTS difficulty VARCHAR DEFAULT 'medium'`
- `UPDATE curricula SET difficulty = 'medium' WHERE difficulty IS NULL`

> The worker also calls `Base.metadata.create_all` on startup, which creates
> any *new* tables but does **not** alter existing tables — so run the script
> above for an existing DB. The `signal_status` / `signal_video_url` columns
> (Phase 1) and `source_type` / `source_ref` (Phase 2) are additive and are
> created by `create_all` on fresh DBs; on long-lived dev DBs run the matching
> additive scripts if those columns are missing (`add_columns.py`,
> `add_recap_columns.py`, etc.).

### 1.2 Restart the stack

```bash
# space-free junction on Windows (recommended):
D:\ice\dev.ps1 down
D:\ice\dev.ps1            # up -d + status

# or, from a space-free path where make is available:
make dev
```

Confirm the services are up:

- API: http://localhost:8000/docs
- Web: http://localhost:3000
- MinIO console: http://localhost:9001 (creds in `.env`)

### 1.3 Required env vars

No new env vars are **required** to run the features. The defaults work for a
local dev stack. Two optional variables are useful for local testing:

| Variable | Default | Purpose |
| --- | --- | --- |
| `MINIO_EXTERNAL_ENDPOINT` | `http://localhost:9000` | Browser-reachable MinIO endpoint used to sign presigned URLs for the HTML5 player + signal/recap video. Set to the host:port your browser can reach MinIO on (e.g. `http://localhost:9000` when running the stack locally, or your LAN IP when testing from another device). |
| `SIGNAL_VIDEO_ENABLED` | `true` | Master toggle for the signal video. `false` skips the task and marks `signal_status=skipped` so the nice-to-have can't block curriculum readiness on a CPU-only host. |
| `SIGNAL_VIDEO_ENGINE` | `remotion` | `remotion` (animated; needs `npx`/Node on PATH) or `ffmpeg` (static slideshow). |
| `SIGNAL_VIDEO_TTS_COMMAND` | `edge-tts` | TTS binary; preflighted at task start so a missing binary fails fast with a clear log. |
| `SIGNAL_VIDEO_REMOTION_COMMAND` | `npx` | Remotion binary; preflighted only when `engine=remotion`. |

Optional vision-tuning knobs (all have safe defaults; see `.env.example` and
`libs/shared/src/ice_shared/settings.py`):

`VISION_EXTRACT_RATE_SEC` (5.0), `VISION_MAX_FRAMES` (60),
`VISION_MAX_WORKERS`, `VISION_DEDUP_THRESHOLD` (0.06),
`VISION_OCR_CONFIDENCE_THRESHOLD`,
`VISION_ENABLE_HEAVY_FALLBACKS`, `VISION_OCR_MAX_WIDTH` (768),
`VISION_ONNX_INTRA_OP_THREADS` (1), `VISION_MAX_FALLBACK_FRAMES` (3).

---

## 2. Signal Video (Phase 1)

The "signal video" is a short cinematic summary (Edge-TTS narration over
Remotion-rendered slides) auto-generated once a curriculum is ready. It can
also be triggered manually from the curriculum page.

### 2.1 Auto-generation

1. Upload a curriculum (YouTube URL **or** local file, see §4) and let it
   finish — wait until the curriculum `status` becomes `ready`.
2. On `ready`, the worker auto-dispatches the `ice.worker.generate_signal_video`
   Celery task (idempotent: it skips if `signal_status` is already
   `queued`/`processing`/`ready`, e.g. if the manual button was pressed first).

**Confirm in the worker logs:**

```
auto-triggered signal video for curriculum <id>
generate_signal_video: cid=<id> tenant=<tid>
Sending prompt to Gemini for signal video (Max words: ...)
Rendering Remotion video... npx remotion render ...
```

**Confirm in the DB / API:**

- `GET /api/v1/curricula/{id}` → `signal_status` transitions
  `none` → `processing` → `ready`.
- When `ready`, `signal_video_url` is populated with a presigned MinIO URL
  (signed against `MINIO_EXTERNAL_ENDPOINT`, valid 7 days).
- On failure, `signal_status` becomes `failed` and the curriculum itself is
  **not** affected (the auto-trigger is fully isolated; failures only log).

### 2.2 Manual trigger

1. Open a ready curriculum at `/curriculum/{id}`.
2. In the supplemental-media tabs (Cinematic / Recap / Study Guide), press the
   **Signal** button.
3. This calls `POST /api/v1/curricula/{id}/signal`, which sets
   `signal_status = "queued"` and dispatches the same task.

**Confirm:** the page polls (SWR `refreshInterval` while
`signal_status === "processing"`), the tab shows a processing state, then the
cinematic video appears and plays once `signal_status === "ready"`.

### 2.3 Failure / no-op cases

- `SIGNAL_VIDEO_ENABLED=false` → task marks `signal_status=skipped` and exits without calling Gemini/Remotion/TTS.
- `edge-tts` or `npx` (when `engine=remotion`) not on PATH → preflight fails fast, `signal_status` → `failed` with a clear log (no swallowed subprocess error).
- Gemini model unavailable → `get_gemini_model` lists models + falls back; if all
  fail, `signal_status` → `failed` (see §7 to retry).

---

## 3. Vision Pipeline Performance (Phase 1)

The M3 vision extractor (frame sampling + OCR + region classification) was
rewritten for CPU throughput. Verify the latency improvement against a known
baseline.

### 3.1 Trigger + measure

1. Process a ~10-minute screen-recording/tutorial video (the longest common
   case) via either upload or YouTube.
2. Tail the worker logs during the M3 stage.

**Logs to look for:**

```
Extracting visuals from <video_path> at <rate>s intervals (device=cpu)
Running OCR on <N> frames with <W> threads        # or: "Running OCR sequentially (max_workers=1)"
Extracted <M> visual items
M3 visuals: <M> items (<C> code regions) for curriculum <id>
```

3. Note the wall-clock time between the `Extracting visuals...` line and the
   `Extracted ... visual items` line.

### 3.2 Acceptance

- **Target:** < 2 minutes total for a 10-minute video on a CPU dev laptop.
- **Compare with previous logs** (pre-branch) to confirm improvement. The wins
  come from:
  - Seek-based frame extraction (decode ~1 frame per sample instead of every
    frame) with a `grab()`-based fallback for containers that can't seek.
  - Near-duplicate dedup over a wider window (8 kept frames) of recent frames.
  - Downscaling wide frames before OCR (`VISION_OCR_MAX_WIDTH`, default 768).
  - Threaded OCR via `ThreadPoolExecutor` (`VISION_MAX_WORKERS`, default
    `min(cpu_count, 4)`); RapidOCR/ONNX Runtime releases the GIL so threads give
    real parallelism without the Celery daemon-process crash a process pool
    would cause.
  - ONNX intra-op thread cap (`VISION_ONNX_INTRA_OP_THREADS=1`) to avoid core
    oversubscription, and a module-global warm OCR engine (no per-frame cold start).
  - A `VISION_MAX_FALLBACK_FRAMES` cap so the heavy upscale/TrOCR path can't
    blow the latency budget on a single bad video.

### 3.3 Regression sanity

- Confirm `M3 visuals: ... (C code regions)` reports a non-zero `C` for a
  programming video (OCR code items feed coding/debug grounding in §6). A zero
  count on a code-heavy video usually means the source codec couldn't be
  decoded (e.g. AV1 on CPU) — the YouTube downloader now prefers H.264 (avc1).

---

## 4. Local Video Upload (Phases 2 & 3)

### 4.1 Upload a local file

1. Go to `/upload`.
2. Drag a valid `.mp4` (≤ 2 GiB) onto the drop zone (or pick `.mov/.mkv/.webm/
   .avi/.m4v`). The URL field greys out when a file is selected.
3. (Optional) choose a difficulty (see §5).
4. Press **Generate curriculum**.

The page submits `multipart/form-data` to `POST /api/v1/curricula/upload` with
`file`, `title`, and `difficulty`. The API validates the extension
(`PIPELINE_UPLOAD_ALLOWED_EXTS`) and size (`PIPELINE_UPLOAD_MAX_BYTES`, 2 GiB),
streams the file to MinIO at `tenants/<tid>/curricula/<cid>/source_video<ext>`,
creates the row with `source_type="upload"`, and dispatches the same
`generate_curriculum` pipeline. The worker routes on the ref shape (S3 key →
`ingest_upload`), which downloads from MinIO, probes duration, extracts a WAV,
and runs the rest of the pipeline source-agnostically (no captions → Whisper ASR).

### 4.2 Verify

1. The curriculum appears on the dashboard and the page redirects to
   `/curriculum/{id}`.
2. **Player:** the video area renders an **HTML5 `<video>` element** (native
   controls), **not** a YouTube iframe. The presigned URL is fetched from
   `GET /api/v1/curricula/{id}/video` (only for `source_type=="upload"`; YouTube
   rows never hit it). If the URL is slow/fails, a "Video taking too long to
   load" overlay with a **Retry** button appears after 15s.
3. **Progress tracking:** play the video; heartbeats fire to
   `POST /api/v1/curricula/{id}/progress` (~every 10s + on pause/unload). Reload
   the page — playback resumes at the saved position (resume_ts), and the
   anti-scrub ceiling (max-watched) is enforced (forward seeks past it snap back).
4. **Checkpoints:** as the playhead crosses each checkpoint `ts`, the player
   auto-pauses and opens the exercise modal — identical to the YouTube path
   (the HTML5 element is wired into the same `PlayerHandle` interface).
5. **Exercises:** submit an answer; the `/evaluate` endpoint grades it (MCQ,
   conceptual similarity, or code execution against hidden tests) and the
   donut + marker update. Reload — the persisted verdict + your answer are
   shown in locked Review Mode.

### 4.3 Validation rejections

- Unsupported extension → `400` with the allowed list.
- File > 2 GiB → `413` ("File exceeds the maximum allowed size").
- Duration outside `[MIN_VIDEO_DURATION_SEC, MAX_VIDEO_DURATION_SEC]` → the
  worker fails the curriculum with a clear duration-window error.

---

## 5. Difficulty Selector (Phase 4)

### 5.1 Choose a difficulty on upload

1. On `/upload`, the **Difficulty** segmented control (Easy / Medium / Hard,
   default Medium) sits above the submit button.
2. Select Easy / Medium / Hard, then submit (works for both YouTube and local
   upload — the value is sent as the `difficulty` field on either endpoint).
3. The API clamps it to `easy|medium|hard` (default `medium`) and stores it on
   `curricula.difficulty`.

### 5.2 Verify the effect

The worker reads `difficulty` off the row (medium fallback for missing column /
legacy rows) and tunes two things in `place_checkpoints`:

| Difficulty | Checkpoint min gap | Numeric difficulty stamped |
| --- | --- | --- |
| Easy | 150 s | 2 |
| Medium | 90 s | 3 |
| Hard | 60 s | 4 |

- **Checkpoint frequency:** open the generated curriculum. Easy → fewer, more
  spread-out checkpoints; Hard → more, tightly-spaced checkpoints (compare the
  marker count on the progress bar for the same video at each difficulty).
- **Exercise complexity:** the numeric difficulty (1–5) is threaded into the M7
  exercise prompts, so Hard exercises should read tougher than Easy for the same
  segment.

### 5.3 Existing curricula

- Pre-migration curricula (no `difficulty` column, or `NULL`) default to
  **Medium**. The migration backfills `NULL → 'medium'`, and the pipeline's
  fallback is medium, so existing rows behave exactly as before (zero-regression).

---

## 6. Dynamic Exercise Types (Phase 5)

A content classifier labels each curriculum once
(`programming` | `theory` | `conceptual` | `motivational` | `mixed`); the
checkpoint placer and exercise generator pick exercise types appropriate to
that category, with a per-segment "grounding guarantee" for code tasks.

### 6.1 Classification log

During generation, confirm the classification in the worker logs:

```
classify_content: LLM -> <category> (conf=0.xx)         # or: classify_content: fallback -> ...
Phase 5 content category=<category> (conf=0.xx) for curriculum <id>
```

The classifier tries an LLM call once per curriculum and falls back to a
deterministic keyword heuristic if the LLM is unavailable/unparseable (never
breaks the pipeline).

### 6.2 Test matrix

Process one video of each kind and inspect the generated exercises
(`GET /api/v1/curricula/{id}` → `checkpoints[].exercise_type` and the exercise
`type`), or use the donut/modal on the player:

| Upload this… | Expected category | Expected exercise types | Must NOT appear |
| --- | --- | --- | --- |
| A **programming** tutorial (code on screen) | `programming` (or `mixed`) | `coding`, `debug`, `mcq`, `conceptual` | — |
| A **motivational** speech | `motivational` | `conceptual`, `mcq` only | `coding`, `debug` |
| A **theory** video (e.g. history / proofs) | `theory` | `mcq`, `conceptual` | `coding`, `debug` |

### 6.3 Grounding guarantee

Even inside a `programming` curriculum, a `coding`/`debug` exercise is only
produced for a segment that is **code-grounded** — i.e. M3 vision OCR found
on-screen code for that segment **or** the segment's transcript text carries
technical programming signal. Intro/outro segments with no code fall back to
`mcq`/`conceptual`. Confirm: in a programming curriculum, a non-technical
segment (e.g. a pure intro) does **not** get a coding task.

### 6.4 Relevance safety net

The exercise generator also has a `_remap_non_technical` safety net: if a
checkpoint's concept is non-technical, any `coding`/`debug` request is remapped
to `mcq`/`conceptual` and logged:

```
Remapping non-technical 'coding' exercise -> 'mcq' (segment=... concept=...)
```

So even stale/externally-produced checkpoints can't yield irrelevant code tasks.

---

## 7. Rollback / Troubleshooting

All features are additive and zero-regression; reverting is incremental.

### 7.1 Disable a feature without reverting code

| Feature | How to disable / revert behaviour |
| --- | --- |
| **Difficulty** | `ALTER TABLE curricula DROP COLUMN difficulty;` (or set all rows to `'medium'`). The pipeline falls back to medium everywhere, matching pre-Phase-4 behaviour. |
| **Dynamic exercise types** | No env toggle. The classifier already falls back to keywords if the LLM is down; an unknown/`None` category falls back to the non-technical pool (`mcq`/`conceptual`). To fully revert, `git revert` the Phase 5 commit (`4da748a`-equivalent). |
| **Vision perf** | `VISION_MAX_WORKERS=1` → sequential OCR (no thread pool). `VISION_OCR_MAX_WIDTH=0` → disables pre-OCR downscaling. `VISION_EXTRACT_RATE_SEC=2` + `VISION_MAX_FRAMES=150` restore the older (slower) sampling. These restore older behaviour at the cost of latency. |
| **Signal video auto-trigger** | `SIGNAL_VIDEO_ENABLED=false` → skips the task and marks `signal_status=skipped` (no Gemini/Remotion/TTS work). Fully isolated; a failure only logs and never affects the curriculum. To stop auto-generation while keeping the manual button, revert the auto-dispatch block at the end of `generate_curriculum.py` (`_run`). |
| **Local upload** | Simply don't use the drop zone — the YouTube path is untouched. If the presigned video URL won't play in the browser, set `MINIO_EXTERNAL_ENDPOINT` to the host:port your browser can reach MinIO on (default `http://localhost:9000`). |

### 7.2 Replay a failed stage

- **Signal video:** press the Signal button on the curriculum page
  (`POST /curricula/{id}/signal`) — it re-queues from any non-`ready` state.
- **Whole curriculum:** delete the row (`DELETE /api/v1/curricula/{id}`) and
  re-upload; the cascade purge removes all children (checkpoints, exercises,
  attempts, sessions, artifacts) so a clean regeneration runs.

### 7.3 Common symptoms

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `signal_status = failed` right after `ready` | Gemini API key/quotas, or Remotion/edge-tts missing in the worker image | Check worker logs for `Gemini failed:` / `Remotion render error`. Re-press the Signal button once deps are present. |
| Upload plays but video is blank / `ERR_SIGNATURE` | Presigned URL signed against an internal endpoint the browser can't reach | Set `MINIO_EXTERNAL_ENDPOINT` to the browser-reachable MinIO URL and reload. |
| `M3 visuals: 0 code regions` on a code-heavy video | Source codec (AV1) couldn't decode on CPU | Use an H.264 upload; YouTube downloads already prefer `avc1`. |
| Coding exercise appears under a non-code segment | Stale checkpoint data pre-Phase-5 | Re-process the curriculum; the placer + `_remap_non_technical` now gate code tasks. |

---

## 8. Quick verification checklist

Run through this before merging:

- [ ] `git status` clean; `main..HEAD` shows Phase 1–5 commits.
- [ ] `python add_curriculum_difficulty.py` ran; `curricula.difficulty` column exists.
- [ ] Stack restarted; API + web + worker + MinIO reachable.
- [ ] Signal video: auto-generated after a curriculum goes `ready`
      (`signal_status → ready`, `signal_video_url` present); manual button also works.
- [ ] Vision: < 2 min for a 10-min video; `M3 visuals: ... (N code regions)` non-zero for code video.
- [ ] Local upload: HTML5 `<video>` plays, progress/checkpoints/exercises work.
- [ ] Difficulty: Easy vs Hard produce visibly different checkpoint counts.
- [ ] Existing curricula default to Medium.
- [ ] Programming video → coding/debug/mcq/conceptual; motivational/theory → mcq/conceptual only.
- [ ] No irrelevant exercise types appear (grounding + remap hold).
