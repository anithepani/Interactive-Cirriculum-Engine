import React from "react";

interface CheckpointMarkerProps {
  left: number; // percentage position (0-100)
  label?: string;
  onClick?: () => void;
}

export default function CheckpointMarker({ left, onClick, label }: CheckpointMarkerProps) {
  return (
    <button
      title={label}
      onClick={onClick}
      className="absolute top-1/2 left-0 h-9 -translate-x-1/2 -translate-y-1/2 rounded-full bg-indigo-500 px-3 py-1 text-[11px] font-semibold text-white shadow-xl shadow-black/30 transition hover:bg-indigo-400"
      style={{ left: `${Math.min(100, Math.max(0, left))}%` }}
    >
      {label}
    </button>
  );
}