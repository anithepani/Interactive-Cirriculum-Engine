"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import LoadingSpinner from "@/components/LoadingSpinner";
import { Checkpoint, CurriculumDetail, ExercisePayload } from "@/lib/types";
import { usePlayerStore } from "@/lib/store";
import ExerciseModal from "@/components/ExerciseModal";
import CheckpointMarker from "@/components/CheckpointMarker";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function CurriculumPage() {
  const params = useParams();
  const id = params?.id;
  const { data, error, mutate } = useSWR<CurriculumDetail>(
    id ? `/api/v1/curricula/${id}` : null,
    fetcher,
    { refreshInterval: 5000 }
  );

  const [selectedExercise, setSelectedExercise] = useState<ExercisePayload | null>(null);
  const [selectedCheckpointId, setSelectedCheckpointId] = useState<number | string | null>(null);
  const { currentCheckpointIndex, setCurrentCheckpointIndex, isExerciseOpen, openExercise, closeExercise } = usePlayerStore();

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

  // Get YouTube embed URL
  const videoUrl = data.video_url || "https://www.youtube.com/watch?v=dQw4w9WgXcQ";
  const getEmbedUrl = (url: string) => {
    const match = url.match(/(?:v=|youtu\.be\/)([^&]+)/);
    return match ? `https://www.youtube.com/embed/${match[1]}?autoplay=1&rel=0` : null;
  };
  const embedUrl = getEmbedUrl(videoUrl);

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

        <div className="mt-4 rounded-lg overflow-hidden bg-black aspect-video">
          {embedUrl ? (
            <iframe
              src={embedUrl}
              className="w-full h-full"
              allowFullScreen
              allow="autoplay; encrypted-media; picture-in-picture"
              title="Video player"
              // If autoplay fails, the user can click the play button inside the iframe
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              Video unavailable
            </div>
          )}
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
            const response = await fetch("/api/v1/evaluate", {
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