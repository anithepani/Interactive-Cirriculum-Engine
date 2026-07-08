"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import LoadingSpinner from "@/components/LoadingSpinner";
import { Checkpoint, CurriculumDetail, ExercisePayload } from "@/lib/types";
import { usePlayerStore } from "@/lib/store";
import ExerciseModal from "@/components/ExerciseModal";
import CheckpointMarker from "@/components/CheckpointMarker";
import ReactPlayer from "react-player";
import { authFetcher, authFetch } from "@/lib/auth";

const Player = ReactPlayer as any;

const fetcher = authFetcher;

export default function CurriculumPage() {
  const params = useParams();
  const id = params?.id;
  const { data, error, mutate } = useSWR<CurriculumDetail>(
    id ? `/api/v1/curricula/${id}` : null,
    fetcher,
    { refreshInterval: 5000 }
  );

  const [player, setPlayer] = useState<any>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [selectedExercise, setSelectedExercise] = useState<ExercisePayload | null>(null);
  const [selectedCheckpointId, setSelectedCheckpointId] = useState<number | string | null>(null);
  const { currentCheckpointIndex, setCurrentCheckpointIndex, isExerciseOpen, openExercise, closeExercise } = usePlayerStore();

  const openExerciseModal = useCallback(
    (checkpoint: Checkpoint, index: number) => {
      setCurrentCheckpointIndex(index);
      setSelectedCheckpointId(checkpoint.id);
      setSelectedExercise(checkpoint.exercise ?? null);
      openExercise();
      setIsPlaying(false);
    },
    [openExercise, setCurrentCheckpointIndex]
  );

  const closeExerciseModal = useCallback(() => {
    setSelectedExercise(null);
    setSelectedCheckpointId(null);
    closeExercise();
    setIsPlaying(true);
  }, [closeExercise]);

  // Check for checkpoints on each time update
  useEffect(() => {
    if (!data || !data.checkpoints || !isPlaying) return;
    const cp = data.checkpoints.find((c) => Math.abs(c.ts - currentTime) < 0.3);
    if (cp) {
      const idx = data.checkpoints.indexOf(cp);
      if (idx !== currentCheckpointIndex) {
        openExerciseModal(cp, idx);
      }
    }
  }, [currentTime, data, isPlaying, currentCheckpointIndex, openExerciseModal]);

  if (error) return <div className="glass p-6">Failed to load curriculum: {(error as Error).message}</div>;
  if (!data) return <div className="glass p-6"><LoadingSpinner /></div>;

  if (data.status === "queued" || data.status === "processing") {
    return (
      <div className="glass p-8 text-center">
        <h2 className="text-2xl font-semibold">Generating curriculum…</h2>
        <p className="mt-2 text-gray-300">This may take a minute.</p>
        <div className="mt-6 mx-auto w-20"><LoadingSpinner size={32} /></div>
      </div>
    );
  }

  let videoUrl = data.video_url || "https://www.youtube.com/watch?v=dQw4w9WgXcQ";
  if (videoUrl && !videoUrl.includes("youtube.com") && !videoUrl.includes("youtu.be")) {
    videoUrl = `https://www.youtube.com/watch?v=${videoUrl}`;
  }

  const checkpoints = data.checkpoints ?? [];

  const handleCheckpointClick = (cp: Checkpoint, index: number) => {
    setCurrentCheckpointIndex(index);
    if (player) {
      player.seekTo(cp.ts);
      setIsPlaying(true);
    }
    openExerciseModal(cp, index);
  };

  const handleProgress = (state: any) => {
    setCurrentTime(state.playedSeconds);
  };

  const onReady = (playerInstance: any) => {
    setPlayer(playerInstance);
  };

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

        <div className="mt-4 rounded-lg overflow-hidden bg-black aspect-video">
          <Player
            url={videoUrl}
            width="100%"
            height="100%"
            controls={true}
            playing={isPlaying}
            onPlay={() => setIsPlaying(true)}
            onPause={() => setIsPlaying(false)}
            onProgress={handleProgress}
            onReady={onReady}
            config={{
              youtube: {
                playerVars: { modestbranding: 1, rel: 0 },
              },
            }}
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
                onClick={() => handleCheckpointClick(cp, index)}
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
            const response = await authFetch("/api/v1/curricula/evaluate", {
              method: "POST",
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