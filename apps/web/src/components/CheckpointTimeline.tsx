import { Checkpoint } from "@/lib/types";

interface CheckpointTimelineProps {
  checkpoints: Checkpoint[];
  duration: number;
  onMarkerClick: (index: number) => void;
}

export default function CheckpointTimeline({ checkpoints, duration, onMarkerClick }: CheckpointTimelineProps) {
  return (
    <div className="mt-6 space-y-4 rounded-3xl border border-white/10 bg-slate-950 p-4">
      <div className="text-sm uppercase tracking-[0.2em] text-gray-400">Checkpoint timeline</div>
      <div className="relative h-4 rounded-full bg-white/10">
        {checkpoints.map((checkpoint, index) => {
          const left = Math.min(100, Math.max(0, (checkpoint.ts / Math.max(duration, 1)) * 100));
          return (
            <button
              key={checkpoint.id}
              type="button"
              className="absolute top-0 h-4 w-4 -translate-x-1/2 rounded-full bg-blue-400 shadow-[0_0_0_4px_rgba(59,130,246,0.18)] transition hover:scale-110"
              style={{ left: `${left}%` }}
              aria-label={`Checkpoint at ${checkpoint.ts}s`}
              onClick={() => onMarkerClick(index)}
            />
          );
        })}
      </div>
      <div className="grid gap-3 text-sm text-gray-300 sm:grid-cols-2">
        {checkpoints.map((checkpoint, index) => (
          <div key={checkpoint.id} className="rounded-2xl border border-white/10 bg-slate-900 p-3">
            <div className="font-semibold text-white">Checkpoint {index + 1}</div>
            <div className="text-xs text-gray-400">{checkpoint.exercise_type.toUpperCase()}</div>
            <div className="text-xs text-gray-400">{checkpoint.ts.toFixed(1)}s</div>
            <div className="truncate text-sm text-gray-200">Concept: {checkpoint.concept_id}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
