"use client";

import { useCallback, useState, useEffect, useRef, useMemo } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import YouTube from "react-youtube";
import LoadingSpinner from "@/components/LoadingSpinner";
import { Checkpoint, CurriculumDetail, ExercisePayload } from "@/lib/types";
import { usePlayerStore } from "@/lib/store";
import ExerciseModal from "@/components/ExerciseModal";
import VideoProgressBar, { StatusMap } from "@/components/VideoProgressBar";
import CheckpointDonut from "@/components/CheckpointDonut";
import { authFetcher, authFetch } from "@/lib/auth";
import RecapPlayer from "@/components/RecapPlayer";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import AppLayout from "@/components/layout/AppLayout";

const fetcher = authFetcher;

const PLAYER_OPTS = { playerVars: { rel: 0, modestbranding: 1 } } as const;

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
  // Session-scoped store of the learner's last submitted answer per checkpoint,
  // used to pre-fill the locked editor in Review Mode (resets on reload, like
  // statusMap). Keyed by checkpoint id.
  const [submissionMap, setSubmissionMap] = useState<Record<string | number, string>>({});
  const [completedSnapshot, setCompletedSnapshot] = useState<"correct" | "incorrect" | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const playerRef = useRef<PlayerHandle | null>(null);
  const lastTimeRef = useRef(0);
  const triggeredRef = useRef<Set<string | number>>(new Set());
  const checkpointsRef = useRef<Checkpoint[]>([]);

  const checkpoints = useMemo(() => data?.checkpoints ?? [], [data?.checkpoints]);
  useEffect(() => {
    checkpointsRef.current = checkpoints;
  }, [checkpoints]);

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

  useEffect(() => {
    setLoadingTimeout(false);
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
          openExerciseModal(cp, i);
          return;
        }
      }
      lastTimeRef.current = t;
      setCurrentTime(t);
    }, 250);
    return () => clearInterval(interval);
  }, [playerReady, openExerciseModal, duration]);

  const handleRetry = () => {
    setIframeKey((prev) => prev + 1);
    lastTimeRef.current = 0;
  };

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

  return (
    <AppLayout>
      <div className="space-y-6 px-6 py-8 mx-auto max-w-5xl">
        <div className="flex items-center mb-2">
        <Link 
          href="/dashboard"
          className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-2.5 text-sm font-semibold text-ink shadow-sm ring-1 ring-inset ring-ink/10 transition hover:bg-indigo-50 hover:text-indigo-600 hover:ring-indigo-200"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Link>
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
          <div className="space-y-4">
            <div className="rounded-lg overflow-hidden bg-black aspect-video relative">
              {videoId ? (
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

          {/* Recap Video Player */}
          <RecapPlayer
            curriculumId={data.id}
            recapStatus={data.recap_status || "none"}
            recapUrl={data.recap_url ?? null}
            onTrigger={async () => {
              try {
                const res = await authFetch(`/api/v1/curricula/${data.id}/recap`, { method: "POST" });
                if (!res.ok) throw new Error("Failed to trigger recap");
                mutate();
              } catch (err) {
                console.error(err);
                alert("Failed to start recap generation.");
              }
            }}
          />

          {/* Study Guide Document */}
          {data.recap_transcript_html && (
            <div className="study-guide-content bg-white p-8 rounded-[2rem] border border-ink/10 shadow-sm mt-4">
              <h2 className="font-display text-2xl font-bold text-ink mb-6">Study Guide</h2>
              <div dangerouslySetInnerHTML={{ __html: data.recap_transcript_html }} />
            </div>
          )}
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
