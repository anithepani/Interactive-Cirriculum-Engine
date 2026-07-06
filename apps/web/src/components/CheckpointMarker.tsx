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
      className="absolute top-0 h-4 w-4 -translate-x-1/2 rounded-full bg-indigo-500 shadow-[0_0_0_6px_rgba(79,70,229,0.12)] hover:scale-110 transition-transform"
      style={{ left: `${left}%` }}
    />
  );
}