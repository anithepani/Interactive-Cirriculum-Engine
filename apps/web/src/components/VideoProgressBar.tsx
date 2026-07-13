"use client";

import { Checkpoint } from "@/lib/types";

export type CheckpointStatus = "pending" | "correct" | "incorrect";
export type StatusMap = Record<string | number, CheckpointStatus>;

interface VideoProgressBarProps {
  duration: number;
  currentTime: number;
  checkpoints: Checkpoint[];
  statusMap?: StatusMap;
  onMarkerClick?: (index: number) => void;
}

const STATUS_COLOR: Record<CheckpointStatus, string> = {
  pending: "#f5b50a", // yellow
  correct: "#22c55e", // green
  incorrect: "#ef4444", // red
};

export default function VideoProgressBar({
  duration,
  currentTime,
  checkpoints,
  statusMap = {},
  onMarkerClick,
}: VideoProgressBarProps) {
  const safeDuration = Math.max(duration, 1);
  const progress = Math.min(100, Math.max(0, (currentTime / safeDuration) * 100));

  return (
    <div className="mt-4 select-none">
      <div className="relative h-3 rounded-full bg-white/10 overflow-visible">
        {/* Filled progress */}
        <div
          className="absolute top-0 left-0 h-full rounded-full bg-indigo-500/80 transition-[width] duration-150 ease-linear"
          style={{ width: `${progress}%` }}
        />
        {/* Playhead */}
        <div
          className="absolute top-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white shadow ring-2 ring-indigo-500"
          style={{ left: `${progress}%` }}
        />
        {/* Checkpoint markers */}
        {checkpoints.map((cp, index) => {
          const left = Math.min(100, Math.max(0, (cp.ts / safeDuration) * 100));
          const status = statusMap[cp.id] ?? "pending";
          return (
            <button
              key={cp.id}
              type="button"
              title={`@${Math.round(cp.ts)}s (${status})`}
              aria-label={`Checkpoint at ${Math.round(cp.ts)} seconds`}
              onClick={() => onMarkerClick?.(index)}
              className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-black/40 shadow-md transition hover:scale-125"
              style={{ left: `${left}%`, backgroundColor: STATUS_COLOR[status] }}
            />
          );
        })}
      </div>
      <div className="mt-1.5 flex justify-between text-[11px] text-gray-400">
        <span>{formatTime(currentTime)}</span>
        <span>{formatTime(duration)}</span>
      </div>
    </div>
  );
}

function formatTime(sec: number): string {
  if (!Number.isFinite(sec) || sec < 0) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
