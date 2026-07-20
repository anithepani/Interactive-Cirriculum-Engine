/**
 * CurriculumCard — light-theme version
 * --------------------------------------
 * White card on the site's light canvas background (bg-canvas = #f4f4f4).
 * Uses the same design language as the landing page's light cards:
 *   bg-white border border-ink/10 rounded-xl2 shadow-card
 *
 * Delete button added so users can remove curricula directly from the dashboard.
 */

"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, BookOpen, Clock, Trash2 } from "lucide-react";
import StatusBadge from "@/components/StatusBadge";
import type { CurriculumSummary } from "@/lib/types";

interface CurriculumCardProps {
  curriculum: CurriculumSummary;
  /** Stagger index for the entrance animation delay */
  index: number;
  /** Called when the delete button is clicked */
  onDelete?: (id: number) => void;
  /** Optional prefix for the curriculum link */
  hrefPrefix?: string;
}

/** Entrance variants — matches the landing page fadeUp motion */
const cardVariants = {
  hidden: { opacity: 0, y: 28 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: i * 0.07,
      duration: 0.45,
      ease: "easeOut" as const,
    },
  }),
};

function formatDate(iso?: string): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function CurriculumCard({
  curriculum,
  index,
  onDelete,
  hrefPrefix = "/curriculum",
}: CurriculumCardProps) {
  const isReady = curriculum.status === "ready";

  return (
    <motion.div
      custom={index}
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      whileHover={{
        y: -4,
        boxShadow: "0 16px 40px rgba(0,0,0,0.10)",
        transition: { type: "spring", stiffness: 260, damping: 22 },
      }}
      className="group relative flex flex-col overflow-hidden rounded-[2rem]
                 border border-ink/10 bg-white shadow-sm
                 transition-shadow duration-300"
    >
      {/* Top accent stripe — indigo → purple gradient */}
      <div
        className="h-1 w-full bg-gradient-to-r from-indigo-500 via-purple-500 to-hotpink
                    opacity-70 transition-opacity duration-300 group-hover:opacity-100"
        aria-hidden="true"
      />

      <div className="flex flex-1 flex-col gap-4 p-6">
        {/* Header row: status badge + delete */}
        <div className="flex items-start justify-between gap-3">
          <StatusBadge status={curriculum.status} />

          {onDelete && (
            <button
              type="button"
              onClick={() => onDelete(curriculum.id)}
              aria-label={`Delete ${curriculum.title}`}
              title="Delete curriculum"
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full
                         text-ink-soft/40 transition hover:bg-rose-50 hover:text-rose-500
                         focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-300"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        {/* Icon + title */}
        <div className="flex items-start gap-3">
          <div
            className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl
                         bg-indigo-50 text-indigo-600"
          >
            <BookOpen className="h-4 w-4" />
          </div>
          <h2
            className="line-clamp-2 font-display text-base font-bold leading-snug text-ink"
            title={curriculum.title}
          >
            {curriculum.title}
          </h2>
        </div>

        {/* Date meta */}
        {(curriculum.created_at || curriculum.ready_at) && (
          <div className="flex items-center gap-1.5 text-xs text-ink-soft">
            <Clock className="h-3.5 w-3.5 shrink-0" />
            {curriculum.ready_at
              ? `Ready ${formatDate(curriculum.ready_at)}`
              : `Created ${formatDate(curriculum.created_at)}`}
          </div>
        )}

        {/* Progress bar (Feature 9) — real watch-completion % for ready courses.
            Tied to the watch-tracking data from Feature 7 via the stats/list
            endpoints. Hidden until the curriculum is ready. */}
        {isReady && typeof curriculum.progress === "number" && (
          <div className="space-y-1">
            <div className="flex items-center justify-between text-[11px] font-medium text-ink-soft">
              <span>Progress</span>
              <span>{Math.round(curriculum.progress)}%</span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-ink/10">
              <motion.div
                className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-600"
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(100, Math.max(0, curriculum.progress))}%` }}
                transition={{ duration: 0.6, ease: "easeOut" }}
              />
            </div>
          </div>
        )}

        <div className="flex-1" />

        {/* CTA */}
        {isReady ? (
          <Link
            href={`${hrefPrefix}/${curriculum.id}`}
            aria-label={`Open curriculum: ${curriculum.title}`}
            className="group/btn inline-flex items-center justify-center gap-2 rounded-full
                       bg-gradient-to-r from-indigo-500 to-purple-600 px-5 py-2.5
                       text-sm font-semibold text-white shadow-sm shadow-indigo-200
                       transition-all duration-200 hover:shadow-indigo-300
                       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-300"
          >
            Open curriculum
            <ArrowRight className="h-4 w-4 transition-transform group-hover/btn:translate-x-1" />
          </Link>
        ) : (
          <div className="inline-flex items-center justify-center gap-2 rounded-full
                          border border-ink/10 bg-ink/5 px-5 py-2.5
                          text-sm font-medium text-ink-soft">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
            Processing…
          </div>
        )}
      </div>
    </motion.div>
  );
}
