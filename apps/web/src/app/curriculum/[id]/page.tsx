"use client";

import { useCallback, useState, useEffect, useRef, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import YouTube from "react-youtube";
import LoadingSpinner from "@/components/LoadingSpinner";
import { Checkpoint, CurriculumDetail, ExercisePayload } from "@/lib/types";
import { usePlayerStore } from "@/lib/store";
import MediaTabs from "@/components/MediaTabs";
import ExerciseModal from "@/components/ExerciseModal";
import VideoProgressBar, { StatusMap } from "@/components/VideoProgressBar";
import CheckpointDonut from "@/components/CheckpointDonut";
import { authFetcher, authFetch } from "@/lib/auth";

import { ArrowLeft, Maximize, Minimize, PenSquare, Save, CheckCircle } from "lucide-react";
import Link from "next/link";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = authFetcher;

// `disablekb: 1` removes the native keyboard seek shortcuts; the poll-loop
// snap-back handles mouse scrubbing. `rel: 0` keeps related videos scoped.
const PLAYER_OPTS = {
  playerVars: { rel: 0, modestbranding: 1, disablekb: 1 },
} as const;

interface PlayerHandle {
  getCurrentTime(): number;
  getDuration(): number;
  pauseVideo(): void;
  playVideo(): void;
  seekTo(seconds: number, allowSeekAhead?: boolean): void;
}

function getYouTubeId(url: string): string | null {
  const match = url.match(/(?:v=|youtu\.be\/|\/embed\/)([^&?\/]+)/);
  return match ? match[1] : null;
}

export default function CurriculumPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id;
  const { data, error, mutate } = useSWR<CurriculumDetail>(
    id ? `/api/v1/curricula/${id}` : null,
    fetcher,
    { refreshInterval: (latest) => (latest && (latest.status === "processing" || latest.status === "queued" || latest.recap_status === "processing") ? 5000 : 0) }
  );

  const [selectedExercise, setSelectedExercise] = useState<ExercisePayload | null>(null);
  const [selectedCheckpointId, setSelectedCheckpointId] = useState<number | string | null>(null);
  const { setCurrentCheckpointIndex, isExerciseOpen, openExercise, closeExercise } = usePlayerStore();
  const [iframeKey, setIframeKey] = useState(0);
  const [loadingTimeout, setLoadingTimeout] = useState(false);
  const [playerReady, setPlayerReady] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [statusMap, setStatusMap] = useState<StatusMap>({});
  // Presigned MinIO URL for locally-uploaded source videos (source_type ==
  // "upload"). Fetched lazily below; YouTube curricula never set this.
  const [uploadVideoUrl, setUploadVideoUrl] = useState<string | null>(null);
  // Session-scoped store of the learner's last submitted answer per checkpoint,
  // used to pre-fill the locked editor in Review Mode (resets on reload, like
  // statusMap). Keyed by checkpoint id.
  const [submissionMap, setSubmissionMap] = useState<Record<string | number, string>>({});
  const [completedSnapshot, setCompletedSnapshot] = useState<"correct" | "incorrect" | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const [isTheaterMode, setIsTheaterMode] = useState(false);
  const [isNotesOpen, setIsNotesOpen] = useState(false);
  const [notesText, setNotesText] = useState("");
  const [notesInitialized, setNotesInitialized] = useState(false);
  const [savedNotes, setSavedNotes] = useState(false);

  const playerRef = useRef<PlayerHandle | null>(null);
  // Underlying HTML5 <video> element for uploaded curricula. The poll loop
  // interacts only with the PlayerHandle wrapper (playerRef), so all existing
  // checkpoint / anti-scrub / heartbeat / resume logic works unchanged.
  const videoElRef = useRef<HTMLVideoElement | null>(null);
  const lastTimeRef = useRef(0);
  const triggeredRef = useRef<Set<string | number>>(new Set());
  const checkpointsRef = useRef<Checkpoint[]>([]);
  // Feature 7 — watch tracking + anti-scrub state.
  // maxWatchedRef is the furthest timestamp the learner has legitimately
  // reached; forward seeks beyond it (+tolerance) are snapped back.
  const maxWatchedRef = useRef(0);
  const resumeAppliedRef = useRef(false);
  const resumeTargetRef = useRef(0); // backend resume_ts to seek to on ready
  const watchAccumRef = useRef(0); // seconds watched since last heartbeat flush
  const lastHeartbeatRef = useRef(0); // wall-clock ms of last flush

  const checkpoints = useMemo(() => data?.checkpoints ?? [], [data?.checkpoints]);
  useEffect(() => {
    checkpointsRef.current = checkpoints;
  }, [checkpoints]);

  // Hydrate the in-memory status/submission maps from the backend-persisted
  // attempts (Answer 2) so the donut markers + locked review survive reloads.
  // Backend is the source of truth; we merge (never clobber) an in-session
  // answer the learner just submitted with the same run.
  useEffect(() => {
    if (!checkpoints.length) return;
    const hydratedStatus: StatusMap = {};
    const hydratedSubmissions: Record<string | number, string> = {};
    for (const cp of checkpoints) {
      if (cp.status === "correct" || cp.status === "incorrect") {
        hydratedStatus[cp.id] = cp.status;
      }
      if (typeof cp.submitted_answer === "string" && cp.submitted_answer.length) {
        hydratedSubmissions[cp.id] = cp.submitted_answer;
      }
    }
    if (Object.keys(hydratedStatus).length) {
      setStatusMap((prev) => ({ ...hydratedStatus, ...prev }));
    }
    if (Object.keys(hydratedSubmissions).length) {
      setSubmissionMap((prev) => ({ ...prev, ...hydratedSubmissions }));
    }
  }, [checkpoints]);

  useEffect(() => {
    if (data && !notesInitialized) {
      if (data.learner_notes) {
        setNotesText(data.learner_notes);
      }
      setNotesInitialized(true);
    }
  }, [data, notesInitialized]);

  const openExerciseModal = useCallback(
    (checkpoint: Checkpoint, index: number) => {
      // Guard: if the checkpoint has no exercise data, don't open the modal
      // (prevents a stuck state where isExerciseOpen=true but no modal
      // renders, freezing the auto-pause poll).
      if (!checkpoint.exercise) return;
      setCurrentCheckpointIndex(index);
      setSelectedCheckpointId(checkpoint.id);
      setSelectedExercise(checkpoint.exercise);
      const st = statusMap[checkpoint.id];
      setCompletedSnapshot(st === "correct" ? "correct" : st === "incorrect" ? "incorrect" : null);
      openExercise();
    },
    [openExercise, setCurrentCheckpointIndex, statusMap]
  );

  const closeExerciseModal = useCallback(() => {
    setSelectedExercise(null);
    setSelectedCheckpointId(null);
    setCompletedSnapshot(null);
    closeExercise();
  }, [closeExercise]);

  // Feature 7 — flush a progress heartbeat to the backend (resume position +
  // max-watched ceiling + accrued watch-time). Fire-and-forget; failures are
  // non-fatal to playback.
  const flushHeartbeat = useCallback(
    (position: number) => {
      if (!id) return;
      const delta = watchAccumRef.current;
      watchAccumRef.current = 0;
      lastHeartbeatRef.current = Date.now();
      void authFetch(`/api/v1/curricula/${id}/progress`, {
        method: "POST",
        body: JSON.stringify({
          position: Math.max(0, position),
          max_watched: maxWatchedRef.current,
          watched_delta: delta,
        }),
      }).catch(() => {
        /* non-fatal */
      });
    },
    [id]
  );

  // Fetch the persisted resume position + max-watched ceiling once, so the
  // player resumes where the learner left off and the anti-scrub floor is
  // seeded across sessions.
  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await authFetch(`/api/v1/curricula/${id}/progress`);
        if (!res.ok) return;
        const p = await res.json();
        if (cancelled) return;
        maxWatchedRef.current = Math.max(
          maxWatchedRef.current,
          Number(p?.max_watched_ts) || 0
        );
        // Stash resume target; applied in onReady once the player exists.
        resumeTargetRef.current = Number(p?.resume_ts) || 0;
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  // For locally-uploaded curricula, fetch the presigned MinIO URL so the
  // HTML5 <video> element can stream it. No-op for YouTube curricula (the
  // react-youtube player streams directly and never hits this endpoint).
  useEffect(() => {
    if (!id || data?.source_type !== "upload") return;
    let cancelled = false;
    (async () => {
      try {
        const res = await authFetch(`/api/v1/curricula/${id}/video`);
        if (!res.ok) return;
        const body = await res.json();
        if (cancelled) return;
        if (body?.video_url) setUploadVideoUrl(String(body.video_url));
      } catch {
        /* non-fatal: player shows a load error via the timeout path */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, data?.source_type]);

  useEffect(() => {
    setPlayerReady(false);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setLoadingTimeout(true), 15000);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [iframeKey]);

  // Poll the player's playhead and auto-pause at the first un-triggered
  // checkpoint whose timestamp is crossed. Crossing detection (last < ts <= t)
  // means backward seeks never re-trigger; triggeredRef double-guards it.
  useEffect(() => {
    if (!playerReady) return;
    const interval = setInterval(() => {
      const player = playerRef.current;
      if (!player) return;
      if (usePlayerStore.getState().isExerciseOpen) return;

      let t = 0;
      try {
        t = player.getCurrentTime() || 0;
      } catch {
        return;
      }
      if (!duration) {
        try {
          const d = player.getDuration() || 0;
          if (d) setDuration(d);
        } catch {
          /* ignore */
        }
      }

      const last = lastTimeRef.current;

      // Feature 7 — anti-scrub: block forward seeks past the furthest
      // legitimately-watched timestamp. A jump of >1.5s beyond both `last` and
      // the max-watched ceiling is treated as a skip and snapped back. Backward
      // seeks (rewatching) are always allowed.
      const SCRUB_TOL = 1.5;
      const ceiling = Math.max(maxWatchedRef.current, last);
      if (t > ceiling + SCRUB_TOL) {
        try {
          player.seekTo(ceiling, true);
        } catch {
          /* ignore */
        }
        lastTimeRef.current = ceiling;
        setCurrentTime(ceiling);
        return;
      }

      // Accrue real watch-time only for normal forward playback (small steps),
      // never for seeks/pauses, so hours reflect genuine engagement.
      const step = t - last;
      if (step > 0 && step < 2) {
        watchAccumRef.current += step;
        if (t > maxWatchedRef.current) maxWatchedRef.current = t;
      }
      // Periodic heartbeat (~every 10s of wall-clock).
      if (Date.now() - lastHeartbeatRef.current > 10000) {
        flushHeartbeat(t);
      }

      const cps = checkpointsRef.current;
      for (let i = 0; i < cps.length; i++) {
        const cp = cps[i];
        if (triggeredRef.current.has(cp.id)) continue;
        if (last < cp.ts && cp.ts <= t) {
          triggeredRef.current.add(cp.id);
          try {
            player.pauseVideo();
          } catch {
            /* ignore */
          }
          // If the user seeked well past the checkpoint, snap back to it.
          if (Math.abs(t - cp.ts) > 2) {
            try {
              player.seekTo(cp.ts, true);
            } catch {
              /* ignore */
            }
          }
          lastTimeRef.current = cp.ts;
          setCurrentTime(cp.ts);
          flushHeartbeat(cp.ts);
          openExerciseModal(cp, i);
          return;
        }
      }
      lastTimeRef.current = t;
      setCurrentTime(t);
    }, 250);
    return () => clearInterval(interval);
  }, [playerReady, openExerciseModal, duration, flushHeartbeat]);

  // Flush a final heartbeat on unmount / tab close so watch-time isn't lost.
  useEffect(() => {
    const onHide = () => {
      if (playerRef.current) {
        try {
          flushHeartbeat(playerRef.current.getCurrentTime() || 0);
        } catch {
          /* ignore */
        }
      }
    };
    window.addEventListener("beforeunload", onHide);
    document.addEventListener("visibilitychange", onHide);
    return () => {
      window.removeEventListener("beforeunload", onHide);
      document.removeEventListener("visibilitychange", onHide);
      onHide();
    };
  }, [flushHeartbeat]);

  const handleRetry = () => {
    setIframeKey((prev) => prev + 1);
    lastTimeRef.current = 0;
  };

  // Wire the HTML5 <video> element into the same PlayerHandle interface the
  // YouTube player exposes, so the poll loop, anti-scrub, heartbeat and resume
  // logic all work unchanged for uploaded curricula. Mirrors the YouTube
  // onReady handler: builds the handle, marks the player ready, seeds duration,
  // and applies the persisted resume position once.
  const handleVideoReady = useCallback(() => {
    const el = videoElRef.current;
    if (!el) return;
    const handle: PlayerHandle = {
      getCurrentTime: () => el.currentTime || 0,
      getDuration: () => el.duration || 0,
      pauseVideo: () => el.pause(),
      playVideo: () => {
        void el.play().catch(() => {
          /* autoplay may be blocked; user can press play */
        });
      },
      seekTo: (seconds: number) => {
        el.currentTime = Math.max(0, seconds);
      },
    };
    playerRef.current = handle;
    setPlayerReady(true);
    if (timerRef.current) clearTimeout(timerRef.current);
    try {
      setDuration(el.duration || 0);
    } catch {
      /* ignore */
    }
    if (!resumeAppliedRef.current) {
      resumeAppliedRef.current = true;
      const target = resumeTargetRef.current;
      if (target > 1) {
        try {
          el.currentTime = target;
        } catch {
          /* ignore */
        }
        lastTimeRef.current = target;
        maxWatchedRef.current = Math.max(maxWatchedRef.current, target);
        setCurrentTime(target);
      }
    }
  }, []);

  if (error) return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <div className="flex items-center gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        <span className="font-semibold">Failed to load curriculum:</span> {(error as Error).message}
      </div>
    </div>
  );
  if (!data) return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <LoadingSpinner size={36} />
    </div>
  );

  if (data.status === "queued" || data.status === "processing") {
    return (
      <div className="mx-auto max-w-4xl px-6 py-10">
        <div className="flex flex-col items-center gap-6 rounded-[2rem] border border-ink/10 bg-white py-20 text-center shadow-sm">
          <h2 className="font-display text-2xl font-bold text-ink">Generating curriculum…</h2>
          <p className="text-sm text-ink-soft">This may take a minute.</p>
          <LoadingSpinner size={32} />
        </div>
      </div>
    );
  }

  const videoUrl = data.video_url || "https://www.youtube.com/watch?v=dQw4w9WgXcQ";
  const videoId = getYouTubeId(videoUrl);
  // Uploaded curricula stream a local file via the presigned MinIO URL and an
  // HTML5 <video> element; YouTube curricula keep the react-youtube player
  // path completely unchanged.
  const isUpload = data.source_type === "upload";

  return (
    <AppLayout>
      <div className={`space-y-6 px-6 py-8 mx-auto transition-all duration-500 ${isTheaterMode ? 'max-w-[95%]' : 'max-w-5xl'}`}>
        <div className="flex items-center mb-2">
        <button 
          onClick={() => router.back()}
          className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-ink shadow-sm ring-1 ring-inset ring-ink/10 transition hover:bg-indigo-50 hover:text-indigo-600 hover:ring-indigo-200"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
      </div>
      
      <div className="rounded-[2rem] border border-ink/10 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-2xl font-bold text-ink">{data.title}</h1>
            <p className="mt-1 text-sm text-ink-soft">Status: {data.status}</p>
          </div>
          <CheckpointDonut checkpoints={checkpoints} statusMap={statusMap} />
        </div>

        <div className="mt-6 flex flex-col gap-6">
          {/* Main Video & Progress */}
          <div className="flex-1 space-y-4">
            <div className="flex items-center justify-end gap-3 mb-2">
              <button
                onClick={() => setIsNotesOpen(!isNotesOpen)}
                className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${
                  isNotesOpen ? "bg-indigo-100 text-indigo-700" : "bg-ink/5 text-ink-soft hover:bg-ink/10"
                }`}
              >
                <PenSquare className="h-4 w-4" />
                {isNotesOpen ? "Close Notes" : "Take Notes"}
              </button>
              <button
                onClick={() => setIsTheaterMode(!isTheaterMode)}
                className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold transition ${
                  isTheaterMode ? "bg-indigo-100 text-indigo-700" : "bg-ink/5 text-ink-soft hover:bg-ink/10"
                }`}
              >
                {isTheaterMode ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
                {isTheaterMode ? "Exit Theater" : "Theater Mode"}
              </button>
            </div>
            <div className={`rounded-[2rem] overflow-hidden bg-black relative transition-all duration-500 shadow-lg ${isTheaterMode ? 'h-[75vh]' : 'aspect-video'}`}>
              {isUpload ? (
                /* ── Uploaded video: HTML5 <video> (same styling as the
                   MediaTabs/Recap players). The onLoadedMetadata handler wires
                   it into the shared PlayerHandle so every existing feature
                   (checkpoint poll, anti-scrub, heartbeat, resume) is reused. */
                <>
                  {uploadVideoUrl ? (
                    <video
                      ref={videoElRef}
                      key={iframeKey}
                      src={uploadVideoUrl}
                      controls
                      controlsList="nodownload noplaybackrate"
                      disablePictureInPicture
                      className="h-full w-full object-contain"
                      onLoadedMetadata={handleVideoReady}
                      onError={() => setLoadingTimeout(true)}
                      onEnded={() => {
                        if (usePlayerStore.getState().isExerciseOpen) return;
                        const cps = checkpointsRef.current;
                        for (let i = cps.length - 1; i >= 0; i--) {
                          const cp = cps[i];
                          if (triggeredRef.current.has(cp.id)) continue;
                          if (duration > 0 && cp.ts >= duration - 2) {
                            triggeredRef.current.add(cp.id);
                            openExerciseModal(cp, i);
                            return;
                          }
                        }
                      }}
                    />
                  ) : (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <LoadingSpinner size={32} />
                    </div>
                  )}
                  {loadingTimeout && !playerReady && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 p-4">
                      <p className="text-white text-sm text-center mb-3">
                        Video taking too long to load.
                      </p>
                      <button
                        onClick={handleRetry}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-white font-medium transition"
                      >
                        🔄 Retry
                      </button>
                    </div>
                  )}
                </>
              ) : videoId ? (
                <>
                  <YouTube
                    key={iframeKey}
                    videoId={videoId}
                    className="w-full h-full"
                    iframeClassName="w-full h-full"
                    opts={PLAYER_OPTS as unknown as Record<string, unknown>}
                    title="YouTube video player"
                    onReady={(e: { target: PlayerHandle }) => {
                      const handle: PlayerHandle = e.target;
                      playerRef.current = handle;
                      setPlayerReady(true);
                      if (timerRef.current) clearTimeout(timerRef.current);
                      try {
                        setDuration(handle.getDuration() || 0);
                      } catch {
                        /* ignore */
                      }
                      // Resume where the learner left off (Feature 7). Applied
                      // once; seek to the persisted resume position and seed the
                      // anti-scrub ceiling + poll baseline so it isn't flagged
                      // as a forward skip.
                      if (!resumeAppliedRef.current) {
                        resumeAppliedRef.current = true;
                        const target = resumeTargetRef.current;
                        if (target > 1) {
                          try {
                            handle.seekTo(target, true);
                          } catch {
                            /* ignore */
                          }
                          lastTimeRef.current = target;
                          maxWatchedRef.current = Math.max(maxWatchedRef.current, target);
                          setCurrentTime(target);
                        }
                      }
                    }}
                    onError={() => setLoadingTimeout(true)}
                    onEnd={() => {
                      if (usePlayerStore.getState().isExerciseOpen) return;
                      const cps = checkpointsRef.current;
                      for (let i = cps.length - 1; i >= 0; i--) {
                        const cp = cps[i];
                        if (triggeredRef.current.has(cp.id)) continue;
                        if (duration > 0 && cp.ts >= duration - 2) {
                          triggeredRef.current.add(cp.id);
                          openExerciseModal(cp, i);
                          return;
                        }
                      }
                    }}
                  />
                  {loadingTimeout && !playerReady && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/80 p-4">
                      <p className="text-white text-sm text-center mb-3">
                        Video taking too long to load.
                      </p>
                      <button
                        onClick={handleRetry}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 rounded-lg text-white font-medium transition"
                      >
                        🔄 Retry
                      </button>
                      <a
                        href={videoUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 text-xs text-gray-400 hover:text-white underline"
                      >
                        Watch on YouTube
                      </a>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex flex-col items-center justify-center h-full p-4 text-center text-gray-400">
                  <p className="text-sm">Invalid YouTube URL.</p>
                </div>
              )}
            </div>

            <VideoProgressBar
              duration={duration}
              currentTime={currentTime}
              checkpoints={checkpoints}
              statusMap={statusMap}
              onMarkerClick={(index) => openExerciseModal(checkpoints[index], index)}
            />
          </div>

          {/* Floating Widget for Notes */}
          {isNotesOpen && (
            <div className="fixed bottom-6 right-6 z-50 w-full max-w-sm bg-white dark:bg-zinc-900 shadow-2xl border border-ink/10 flex flex-col rounded-3xl overflow-hidden animate-in slide-in-from-bottom-8 duration-300">
              <div className="p-4 border-b border-ink/10 flex justify-between items-center bg-canvas">
                <h2 className="font-display text-md font-bold text-ink flex items-center gap-2">
                  <PenSquare className="w-4 h-4 text-indigo-500" />
                  My Notes
                </h2>
                <button 
                  onClick={() => setIsNotesOpen(false)}
                  className="p-1.5 rounded-full hover:bg-ink/5 transition text-ink-soft hover:text-ink"
                >
                  <Minimize className="w-4 h-4" />
                </button>
              </div>
              
              <div className="flex flex-col bg-canvas p-4 max-h-[50vh] overflow-y-auto custom-scrollbar">
                <textarea
                  ref={(el) => {
                    if (el) {
                      el.style.height = 'auto';
                      el.style.height = `${el.scrollHeight}px`;
                    }
                  }}
                  value={notesText}
                  onChange={(e) => {
                    setNotesText(e.target.value);
                    e.target.style.height = 'auto';
                    e.target.style.height = `${e.target.scrollHeight}px`;
                  }}
                  placeholder="Type your notes here... (Markdown supported)"
                  className="w-full resize-none rounded-xl border-none bg-white dark:bg-black/20 p-4 text-sm text-ink outline-none focus:ring-2 focus:ring-indigo-500/50 shadow-inner overflow-hidden min-h-[100px]"
                />
                <div className="mt-4 flex items-center justify-between">
                  <p className="text-xs text-ink-soft">
                    Auto-timestamps to current time.
                  </p>
                  <button
                    onClick={async () => {
                      setSavedNotes(true);
                      setTimeout(() => setSavedNotes(false), 2000);
                      try {
                        await fetch(`/api/v1/curricula/${params.id}/notes`, {
                          method: "PUT",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ notes: notesText }),
                        });
                      } catch (e) {
                        console.error("Failed to save notes:", e);
                      }
                    }}
                    className="flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-700 bg-indigo-50 px-4 py-2 rounded-full transition-all active:scale-95"
                  >
                    {savedNotes ? <CheckCircle className="h-3 w-3" /> : <Save className="h-3 w-3" />}
                    {savedNotes ? "Saved!" : "Save Notes"}
                  </button>
                </div>
              </div>
            </div>
          )}

        {/* Unified Supplemental Content: Cinematic Video, Recap Video, Study Guide */}
          <MediaTabs
            recapStatus={data.recap_status || "none"}
            recapUrl={data.recap_url ?? null}
            studyGuideHtml={data.recap_transcript_html ?? null}
            onTriggerRecap={async () => {
              try {
                const res = await authFetch(`/api/v1/curricula/${data.id}/recap`, { method: "POST" });
                if (!res.ok) throw new Error("Failed to trigger recap");
                mutate();
              } catch (err) {
                console.error(err);
                alert("Failed to start recap generation.");
              }
            }}
            signalStatus={data.signal_status || "none"}
            signalUrl={data.signal_video_url ?? null}
            onTriggerSignal={async () => {
              try {
                const res = await authFetch(`/api/v1/curricula/${data.id}/signal`, { method: "POST" });
                if (!res.ok) throw new Error("Failed to trigger signal video");
                mutate();
              } catch (err) {
                console.error(err);
                alert("Failed to start signal video generation.");
              }
            }}
          />
        </div>
      </div>

      {isExerciseOpen && selectedExercise && (
        <ExerciseModal
          isOpen={isExerciseOpen}
          onClose={closeExerciseModal}
          exercise={selectedExercise}
          completedStatus={completedSnapshot}
          submittedAnswer={
            selectedCheckpointId != null ? submissionMap[selectedCheckpointId] ?? null : null
          }
          onRun={async (answer: string) => {
            // Trial run only: /execute compiles + runs the code without the
            // hidden test suite and never touches the skill model or markers.
            const response = await fetch("/api/v1/execute", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                code: answer,
                language: selectedExercise.language || "python",
                stdin: "",
              }),
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
              const message =
                payload?.detail || payload?.error || payload?.message || `Server error: ${response.status}`;
              return { passed: false, stderr: String(message) };
            }
            return {
              passed: Boolean(payload?.passed),
              stdout: payload?.stdout ? String(payload.stdout) : "",
              stderr: payload?.stderr ? String(payload.stderr) : "",
            };
          }}
          onSubmit={async (answer: string) => {
            if (selectedCheckpointId == null) return { passed: false };
            const response = await authFetch("/api/v1/curricula/evaluate", {
              method: "POST",
              body: JSON.stringify({ checkpoint_id: selectedCheckpointId, answer }),
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload?.detail || "Evaluation failed");
            const passed = Boolean(payload?.passed);
            setStatusMap((prev) => ({
              ...prev,
              [selectedCheckpointId]: (passed ? "correct" : "incorrect") as
                | "correct"
                | "incorrect",
            }));
            // Persist the learner's answer (session-scoped) so re-opening the
            // checkpoint shows it in locked Review Mode.
            setSubmissionMap((prev) => ({ ...prev, [selectedCheckpointId]: answer }));
            await mutate();
            return {
              passed,
              message: passed ? "Correct!" : "Incorrect.",
              stdout: payload?.stdout ? String(payload.stdout) : "",
              stderr: payload?.stderr ? String(payload.stderr) : "",
            };
          }}
        />
      )}
      </div>
    </AppLayout>
  );
}
