import React from "react";
import LoadingSpinner from "@/components/LoadingSpinner";

interface SignalPlayerProps {
  curriculumId: number | string;
  signalStatus: "none" | "queued" | "processing" | "ready" | "failed";
  signalUrl: string | null;
  onTrigger: () => void;
}

export default function SignalPlayer({
  curriculumId,
  signalStatus,
  signalUrl,
  onTrigger,
}: SignalPlayerProps) {
  if (signalStatus === "none") {
    return (
      <div className="mt-8 rounded-[2rem] border border-ink/10 bg-white p-8 text-center shadow-sm">
        <h2 className="font-display text-xl font-bold text-ink">
          Want a Cinematic Summary?
        </h2>
        <p className="mt-2 text-ink-soft max-w-lg mx-auto">
          Generate a high-quality "Signal-to-Noise" video featuring professional voiceover and dynamic moving visuals.
        </p>
        <button
          onClick={onTrigger}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-purple-600 px-6 py-3 font-semibold text-white transition hover:bg-purple-700"
        >
          <span>🎬</span> Generate Cinematic Video
        </button>
      </div>
    );
  }

  if (signalStatus === "queued" || signalStatus === "processing") {
    return (
      <div className="mt-8 rounded-[2rem] border border-ink/10 bg-white p-8 text-center shadow-sm">
        <h2 className="font-display text-xl font-bold text-ink">
          Generating Cinematic Video…
        </h2>
        <p className="mt-2 text-ink-soft mb-6 max-w-lg mx-auto">
          We are analyzing the transcript, generating voiceovers, and fetching HD B-roll. This takes about 2-3 minutes.
        </p>
        <LoadingSpinner size={32} />
      </div>
    );
  }

  if (signalStatus === "failed") {
    return (
      <div className="mt-8 rounded-[2rem] border border-rose-200 bg-rose-50 p-8 text-center text-rose-700">
        <h2 className="font-display text-xl font-bold">
          Failed to generate video
        </h2>
        <p className="mt-2">There was an issue creating the cinematic recap.</p>
        <button
          onClick={onTrigger}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-rose-600 px-6 py-3 font-semibold text-white transition hover:bg-rose-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  // ready
  if (signalUrl) {
    return (
      <div className="mt-8 rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm">
        <h2 className="font-display text-xl font-bold text-ink mb-4">
          🎬 Cinematic Summary
        </h2>
        <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black">
          <video
            src={signalUrl}
            controls
            className="h-full w-full object-contain"
            controlsList="nodownload"
          />
        </div>
      </div>
    );
  }

  return null;
}
