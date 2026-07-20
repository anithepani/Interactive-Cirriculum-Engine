"use client";

import { Checkpoint } from "@/lib/types";
import { StatusMap, CheckpointStatus } from "@/components/VideoProgressBar";

interface CheckpointDonutProps {
  checkpoints: Checkpoint[];
  statusMap?: StatusMap;
}

const STATUS_COLOR: Record<CheckpointStatus, string> = {
  pending: "#f5b50a", // yellow
  correct: "#22c55e", // green
  incorrect: "#ef4444", // red
};
const TRACK_COLOR = "rgba(255,255,255,0.08)";

const SIZE = 56;
const STROKE = 7;
const RADIUS = (SIZE - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export default function CheckpointDonut({ checkpoints, statusMap = {} }: CheckpointDonutProps) {
  const total = checkpoints.length;
  const correct = checkpoints.filter((cp) => statusMap[cp.id] === "correct").length;
  const incorrect = checkpoints.filter((cp) => statusMap[cp.id] === "incorrect").length;
  const answered = correct + incorrect;

  if (total === 0) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-300">
        <span className="rounded-full bg-white/5 px-2 py-1">No checkpoints</span>
      </div>
    );
  }

  // Each checkpoint gets an equal arc of the donut. We render each arc as a
  // full circle stroke with a dasharray spanning only its slice, plus a
  // tiny gap between slices for visual separation.
  const sliceLen = CIRCUMFERENCE / total;
  const gap = total > 1 ? Math.min(2, sliceLen * 0.08) : 0;
  const drawLen = sliceLen - gap;

  return (
    <div className="flex items-center gap-3">
      <svg
        width={SIZE}
        height={SIZE}
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="-rotate-90 shrink-0"
        role="img"
        aria-label={`${answered} of ${total} checkpoints answered`}
      >
        {/* Faint track ring */}
        <circle
          cx={SIZE / 2}
          cy={SIZE / 2}
          r={RADIUS}
          fill="none"
          stroke={TRACK_COLOR}
          strokeWidth={STROKE}
        />
        {/* One arc per checkpoint, colored by status */}
        {checkpoints.map((cp, idx) => {
          const status = statusMap[cp.id] ?? "pending";
          const offset = CIRCUMFERENCE - idx * sliceLen;
          return (
            <circle
              key={cp.id}
              cx={SIZE / 2}
              cy={SIZE / 2}
              r={RADIUS}
              fill="none"
              stroke={STATUS_COLOR[status]}
              strokeWidth={STROKE}
              strokeDasharray={`${drawLen} ${CIRCUMFERENCE - drawLen}`}
              strokeDashoffset={offset}
              style={{ transition: "stroke 0.4s ease" }}
              strokeLinecap="round"
            />
          );
        })}
      </svg>
      <div className="flex flex-col leading-tight">
        <span className="text-sm font-semibold text-white">{answered}/{total}</span>
        <span className="text-[10px] uppercase tracking-wider text-gray-400">answered</span>
        {answered > 0 && (
          <span className="text-[10px] mt-0.5">
            <span className="text-green-400">{correct} correct</span>
            <span className="text-gray-500"> · </span>
            <span className="text-red-400">{incorrect} wrong</span>
          </span>
        )}
      </div>
    </div>
  );
}
