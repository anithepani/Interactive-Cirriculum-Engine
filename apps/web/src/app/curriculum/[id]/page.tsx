"use client";

import { useCallback, useState, useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import LoadingSpinner from "@/components/LoadingSpinner";
import { Checkpoint, CurriculumDetail, ExercisePayload } from "@/lib/types";
import { usePlayerStore } from "@/lib/store";
import ExerciseModal from "@/components/ExerciseModal";
import CheckpointMarker from "@/components/CheckpointMarker";
import { authFetcher, authFetch } from "@/lib/auth";

const fetcher = authFetcher;

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
  const [iframeKey, setIframeKey] = useState(0);
  const [loadingTimeout, setLoadingTimeout] = useState(false);
  const [playerReady, setPlayerReady] = useState(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

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

  useEffect(() => {
    setLoadingTimeout(false);
    setPlayerReady(false);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setLoadingTimeout(true);
    }, 15000);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [iframeKey]);

  const handleIframeLoad = () => {
    setPlayerReady(true);
    if (timerRef.current) clearTimeout(timerRef.current);
  };

  const handleRetry = () => {
    setIframeKey((prev) => prev + 1);
  };

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

  const videoUrl = data.video_url || "https://www.youtube.com/watch?v=dQw4w9WgXcQ";

  const getEmbedUrl = (url: string): string | null => {
    const match = url.match(/(?:v=|youtu\.be\/|\/embed\/)([^&?\/]+)/);
    if (!match) return null;
    const videoId = match[1];
    return `https://www.youtube.com/embed/${videoId}?rel=0&modestbranding=1`;
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

        <div className="mt-4 rounded-lg overflow-hidden bg-black aspect-video relative">
          {embedUrl ? (
            <>
              <iframe
                key={iframeKey}
                src={embedUrl}
                className="w-full h-full"
                allowFullScreen
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                referrerPolicy="strict-origin"
                title="YouTube video player"
                frameBorder="0"
                onLoad={handleIframeLoad}
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