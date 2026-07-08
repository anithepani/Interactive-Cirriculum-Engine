"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import dynamic from "next/dynamic";
import LoadingSpinner from "@/components/LoadingSpinner";
import { Checkpoint, CurriculumDetail, ExercisePayload } from "@/lib/types";
import { usePlayerStore } from "@/lib/store";
import ExerciseModal from "@/components/ExerciseModal";
import CheckpointMarker from "@/components/CheckpointMarker";

// Dynamic import for plyr-react
const Plyr = dynamic(
  () => import("plyr-react").then((mod) => mod.Plyr),
  { ssr: false }
);

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function CurriculumPage() {
  const params = useParams();
  const id = params?.id;

  // Use SWR with a refresh interval (no delay)
  const { data, error, mutate } = useSWR<CurriculumDetail>(
    id ? `/api/v1/curricula/${id}` : null,
    fetcher,
    { refreshInterval: 5000 } // refresh every 5 seconds
  );

  const [player, setPlayer] = useState<any>(null);
  const [selectedExercise, setSelectedExercise] = useState<ExercisePayload | null>(null);
  const [selectedCheckpointId, setSelectedCheckpointId] = useState<number | string | null>(null);
  const plyrRef = useRef<any>(null);
  const { currentCheckpointIndex, setCurrentCheckpointIndex, isExerciseOpen, openExercise, closeExercise } = usePlayerStore();

  // Store plyr instance when ready
  useEffect(() => {
    if (plyrRef.current) {
      setPlayer(plyrRef.current);
    }
  }, []);

  // Open exercise modal for a specific checkpoint
  const openExerciseModal = useCallback(
    (checkpoint: Checkpoint, index: number) => {
      setCurrentCheckpointIndex(index);
      setSelectedCheckpointId(checkpoint.id);
      setSelectedExercise(checkpoint.exercise ?? null);
      openExercise();
    },
    [openExercise, setCurrentCheckpointIndex]
  );

  const closeExerciseModal = useCallback(() => {
    setSelectedExercise(null);
    setSelectedCheckpointId(null);
    closeExercise();
  }, [closeExercise]);

  // Auto‑pause at checkpoints
  useEffect(() => {
    if (!data || !player || !data.checkpoints) return;
    const interval = window.setInterval(() => {
      const t = player?.currentTime ?? 0;
      const arrived = data.checkpoints.findIndex((cp) => Math.abs(cp.ts - t) < 0.3);
      if (arrived !== -1 && arrived !== currentCheckpointIndex) {
        player.pause();
        openExerciseModal(data.checkpoints[arrived], arrived);
      }
    }, 300);
    return () => window.clearInterval(interval);
  }, [data, player, currentCheckpointIndex, openExerciseModal]);

  // Loading / error states
  if (error) return <div className="glass p-6">Failed to load curriculum: {(error as Error).message}</div>;
  if (!data) return <div className="glass p-6"><LoadingSpinner /></div>;

  // Waiting for pipeline to finish
  if (data.status === "queued" || data.status === "processing") {
    return (
      <div className="glass p-8 text-center">
        <h2 className="text-2xl font-semibold">Generating curriculum…</h2>
        <p className="mt-2 text-gray-300">This may take a minute. Refresh to check status.</p>
        <div className="mt-6 mx-auto w-20"><LoadingSpinner size={32} /></div>
      </div>
    );
  }

  // Use the actual YouTube video URL (or blank if missing)
  const videoSrc = data.video_url ?? "https://cdn.plyr.io/static/blank.mp4";
  const plyrSource = {
    type: "video" as const,
    sources: [{ src: videoSrc, provider: "html5" as const }],
  };

  // Safely access checkpoints
  const checkpoints = data.checkpoints ?? [];

  return (
    <div className="space-y-6 p-6">
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold">{data.title}</h1>
            <p className="text-sm text-gray-300">Status: {data.status}</p>
          </div>
          <div className="text-sm text-gray-200">
            Checkpoints: {checkpoints.length}
          </div>
        </div>

        <div className="mt-4 rounded-lg overflow-hidden">
          <Plyr
            ref={plyrRef}
            source={plyrSource}
            options={{ controls: ['play', 'progress', 'current-time', 'duration', 'mute', 'volume', 'fullscreen'] }}
          />
        </div>

        <div className="mt-4 relative h-6 rounded-full bg-white/6">
          {checkpoints.map((cp, index) => {
            const maxTs = Math.max(...checkpoints.map((c) => c.ts), 180);
            const left = (cp.ts / maxTs) * 100;
            return (
              <CheckpointMarker
                key={cp.id}
                left={Number(left)}
                label={`@${cp.ts}s`}
                onClick={() => {
                  setCurrentCheckpointIndex(index);
                  if (player) {
                    player.currentTime = cp.ts;
                    player.play();
                  }
                  openExerciseModal(cp, index);
                }}
              />
            );
          })}
        </div>
      </div>

      {isExerciseOpen && selectedExercise && (
        <ExerciseModal
          isOpen={isExerciseOpen}
          onClose={closeExerciseModal}
          exercise={selectedExercise}
          onSubmit={async (answer: string) => {
            if (!selectedCheckpointId) return { passed: false };
            const response = await fetch("/api/v1/curricula/evaluate", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ checkpoint_id: selectedCheckpointId, answer }),
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) throw new Error(payload?.detail || "Evaluation failed");
            await mutate();
            return { passed: Boolean(payload?.passed) };
          }}
        />
      )}
    </div>
  );
}