/**
 * StatusBadge — light-theme version
 * ----------------------------------
 * Pill badge matching the site's LIGHT design system (bg-canvas = #f4f4f4,
 * text-ink = #111). Uses soft coloured backgrounds on white surfaces.
 */

import { cn } from "@/lib/utils";

type Status = "queued" | "processing" | "ready" | "failed" | string;

interface StatusBadgeProps {
  status: Status;
  className?: string;
}

const STATUS_CONFIG: Record<
  string,
  { label: string; bg: string; text: string; dot: string; pulse: boolean }
> = {
  ready: {
    label: "Ready",
    bg: "bg-emerald-100",
    text: "text-emerald-700",
    dot: "bg-emerald-500",
    pulse: false,
  },
  processing: {
    label: "Processing",
    bg: "bg-blue-100",
    text: "text-blue-700",
    dot: "bg-blue-500",
    pulse: true,
  },
  queued: {
    label: "Queued",
    bg: "bg-amber-100",
    text: "text-amber-700",
    dot: "bg-amber-500",
    pulse: true,
  },
  failed: {
    label: "Failed",
    bg: "bg-rose-100",
    text: "text-rose-700",
    dot: "bg-rose-500",
    pulse: false,
  },
};

export default function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? {
    label: status,
    bg: "bg-ink/10",
    text: "text-ink-soft",
    dot: "bg-ink-soft",
    pulse: false,
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold capitalize tracking-wide",
        config.bg,
        config.text,
        className
      )}
    >
      {/* Animated status dot */}
      <span className="relative flex h-2 w-2 shrink-0">
        {config.pulse && (
          <span
            className={cn(
              "absolute inline-flex h-full w-full animate-ping rounded-full opacity-50",
              config.dot
            )}
          />
        )}
        <span
          className={cn("relative inline-flex h-2 w-2 rounded-full", config.dot)}
        />
      </span>
      {config.label}
    </span>
  );
}
