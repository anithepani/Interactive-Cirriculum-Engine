import React from "react";
import LoadingSpinner from "@/components/LoadingSpinner";

interface RecapPlayerProps {
  curriculumId: number | string;
  recapStatus: "none" | "processing" | "ready" | "failed";
  recapUrl: string | null;
  onTrigger: () => void;
}

export default function RecapPlayer({
  curriculumId,
  recapStatus,
  recapUrl,
  onTrigger,
}: RecapPlayerProps) {
  if (recapStatus === "none") {
    return (
      <div className="mt-8 rounded-[2rem] border border-ink/10 bg-white p-8 text-center shadow-sm">
        <h2 className="font-display text-xl font-bold text-ink">
          Want a quick summary?
        </h2>
        <p className="mt-2 text-ink-soft max-w-lg mx-auto">
          Generate a 5-minute video supercut containing the most important
          concepts and takeaways from this curriculum.
        </p>
        <button
          onClick={onTrigger}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 font-semibold text-white transition hover:bg-indigo-700"
        >
          <span>✨</span> Generate Recap Video
        </button>
      </div>
    );
  }

  if (recapStatus === "processing") {
    return (
      <div className="mt-8 rounded-[2rem] border border-ink/10 bg-white p-8 text-center shadow-sm">
        <h2 className="font-display text-xl font-bold text-ink">
          Generating Recap Video…
        </h2>
        <p className="mt-2 text-ink-soft mb-6 max-w-lg mx-auto">
          We are extracting the top sentences and rendering your supercut. This
          takes about 1-2 minutes.
        </p>
        <LoadingSpinner size={32} />
      </div>
    );
  }

  if (recapStatus === "failed") {
    return (
      <div className="mt-8 rounded-[2rem] border border-rose-200 bg-rose-50 p-8 text-center text-rose-700">
        <h2 className="font-display text-xl font-bold">
          Failed to generate recap
        </h2>
        <p className="mt-2">There was an issue creating the video recap.</p>
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
  if (recapUrl) {
    return (
      <div className="mt-8 rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm">
        <h2 className="font-display text-xl font-bold text-ink mb-4">
          ✨ Recap Video
        </h2>
        <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black">
          <video
            src={recapUrl}
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
