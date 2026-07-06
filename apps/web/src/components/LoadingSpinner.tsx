import React from "react";

export default function LoadingSpinner({ size = 24 }: { size?: number }) {
  return (
    <div className="flex items-center justify-center">
      <div
        className="rounded-full border-4 border-white/10 border-t-indigo-500 animate-spin"
        style={{ width: `${size}px`, height: `${size}px` }}
      />
    </div>
  );
}
