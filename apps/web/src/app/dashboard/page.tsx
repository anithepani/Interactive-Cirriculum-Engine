/**
 * Dashboard Page — /dashboard (light-theme redesign)
 * ----------------------------------------------------
 * Fully aligned with the site's light design system:
 *   - Background: bg-canvas (#f4f4f4)
 *   - Text: text-ink (#111111), text-ink-soft (#4b4b4b)
 *   - Cards: bg-white border border-ink/10 rounded-[2rem]
 *   - Accents: indigo-500 → purple-600 gradient
 *   - Typography: font-display (Space Grotesk) + font-body (Inter)
 *   - Framer Motion: stagger entrance, hover lift
 *   - Delete: each card exposes a trash icon; confirm modal guards the action
 */

"use client";

import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Video, RefreshCw, AlertTriangle, Trash2, X } from "lucide-react";
import LoadingSpinner from "@/components/LoadingSpinner";
import CurriculumCard from "@/components/CurriculumCard";
import { authFetcher, authFetch } from "@/lib/auth";
import { staggerContainer } from "@/lib/motion";
import type { CurriculumSummary } from "@/lib/types";

/* ── Polling ──────────────────────────────────────────────────────────── */
const POLL_INTERVAL = 5_000;

const refreshInterval = (latest?: CurriculumSummary[]) => {
  if (!latest || latest.length === 0) return 0;
  const pending = latest.some(
    (c) => c.status !== "ready" && c.status !== "failed"
  );
  return pending ? POLL_INTERVAL : 0;
};

/* ── Delete confirmation modal ─────────────────────────────────────────── */
function DeleteModal({
  title,
  onConfirm,
  onCancel,
  deleting,
}: {
  title: string;
  onConfirm: () => void;
  onCancel: () => void;
  deleting: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/30 px-4 backdrop-blur-sm"
      onClick={onCancel}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0, y: 16 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.95, opacity: 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 24 }}
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-sm rounded-[2rem] border border-ink/10 bg-white p-8 shadow-2xl"
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-100 text-rose-600">
          <Trash2 className="h-6 w-6" />
        </div>

        <h2 className="mt-5 font-display text-xl font-bold text-ink">
          Delete curriculum?
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-ink-soft">
          <span className="font-medium text-ink">&ldquo;{title}&rdquo;</span>{" "}
          will be permanently deleted and cannot be recovered.
        </p>

        <div className="mt-7 flex gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={deleting}
            className="flex-1 rounded-full border border-ink/15 bg-white px-4 py-2.5
                       text-sm font-semibold text-ink transition hover:bg-ink/5
                       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/20
                       disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={deleting}
            className="flex flex-1 items-center justify-center gap-2 rounded-full
                       bg-rose-600 px-4 py-2.5 text-sm font-semibold text-white
                       transition hover:bg-rose-700 focus-visible:outline-none
                       focus-visible:ring-2 focus-visible:ring-rose-400 disabled:opacity-50"
          >
            {deleting ? (
              <LoadingSpinner size={16} />
            ) : (
              <>
                <Trash2 className="h-4 w-4" />
                Delete
              </>
            )}
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

/* ── Section header ────────────────────────────────────────────────────── */
function PageHeader({ count }: { count?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" as const }}
      className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between"
    >
      <div>
        {/* Overline */}
        <p className="font-mono text-xs uppercase tracking-widest text-indigo-500">
          My workspace
        </p>

        {/* Heading — uses font-display (Space Grotesk) like the landing page h1 */}
        <h1 className="mt-2 font-display text-4xl font-black text-ink md:text-5xl">
          Your Curricula
        </h1>

        {/* Gradient underline bar */}
        <div className="mt-3 h-1 w-20 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500" />

        <p className="mt-4 text-sm text-ink-soft">
          {typeof count === "number" && count > 0
            ? `${count} curriculum${count !== 1 ? "a" : ""} generated from video tutorials.`
            : "Generate interactive curricula from any YouTube video or local file."}
        </p>
      </div>

      {/* CTA button */}
      <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
        <Link
          href="/upload"
          id="new-curriculum-btn"
          className="inline-flex items-center gap-2 rounded-full
                     bg-gradient-to-r from-indigo-500 to-purple-600
                     px-6 py-3 text-sm font-semibold text-white shadow-md
                     shadow-indigo-200 transition-shadow duration-200
                     hover:shadow-indigo-300 focus-visible:outline-none
                     focus-visible:ring-2 focus-visible:ring-indigo-400"
        >
          <Plus className="h-4 w-4" />
          New curriculum
        </Link>
      </motion.div>
    </motion.div>
  );
}

/* ── Empty state ───────────────────────────────────────────────────────── */
function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" as const }}
      className="flex flex-col items-center justify-center gap-6 rounded-[2rem]
                 border border-ink/10 bg-white py-20 px-8 text-center shadow-sm"
    >
      {/* Floating icon */}
      <motion.div
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        className="flex h-20 w-20 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-500"
        aria-hidden="true"
      >
        <Video className="h-10 w-10" />
      </motion.div>

      <div className="max-w-xs space-y-2">
        <p className="font-display text-xl font-bold text-ink">
          No curricula yet
        </p>
        <p className="text-sm leading-relaxed text-ink-soft">
          Upload your first video to get started — paste a YouTube URL or drop a
          local file.
        </p>
      </div>

      <motion.div whileHover={{ scale: 1.04 }} whileTap={{ scale: 0.97 }}>
        <Link
          href="/upload"
          id="empty-state-upload-btn"
          className="inline-flex items-center gap-2 rounded-full
                     bg-gradient-to-r from-indigo-500 to-purple-600
                     px-6 py-3 text-sm font-semibold text-white shadow-md
                     shadow-indigo-200 hover:shadow-indigo-300
                     transition-shadow duration-200 focus-visible:outline-none
                     focus-visible:ring-2 focus-visible:ring-indigo-400"
        >
          <Plus className="h-4 w-4" />
          Get started
        </Link>
      </motion.div>
    </motion.div>
  );
}

/* ── Error state ───────────────────────────────────────────────────────── */
function ErrorState({ message }: { message: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-start gap-4 rounded-[2rem] border border-rose-200
                 bg-rose-50 px-6 py-5 text-rose-700"
      role="alert"
    >
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-500" />
      <div>
        <p className="font-semibold text-rose-700">Failed to load curricula</p>
        <p className="mt-1 text-sm text-rose-600">{message}</p>
      </div>
    </motion.div>
  );
}

/* ── Loading skeleton ──────────────────────────────────────────────────── */
function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
      {[...Array(3)].map((_, i) => (
        <div
          key={i}
          className="h-64 animate-pulse rounded-[2rem] border border-ink/10 bg-ink/5"
          style={{ animationDelay: `${i * 0.1}s` }}
        />
      ))}
    </div>
  );
}

/* ── Inline delete error toast ────────────────────────────────────────── */
function DeleteErrorToast({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="flex items-center gap-3 rounded-2xl border border-rose-200
                 bg-rose-50 px-4 py-3 text-rose-700 shadow-sm"
      role="alert"
    >
      <AlertTriangle className="h-4 w-4 shrink-0 text-rose-500" />
      <p className="flex-1 text-sm">{message}</p>
      <button
        type="button"
        onClick={onDismiss}
        className="text-rose-400 transition hover:text-rose-600"
        aria-label="Dismiss"
      >
        <X className="h-4 w-4" />
      </button>
    </motion.div>
  );
}

/* ── Page ──────────────────────────────────────────────────────────────── */
export default function DashboardPage() {
  const { data, error, isLoading, isValidating, mutate } =
    useSWR<CurriculumSummary[]>("/api/v1/curricula", authFetcher, {
      refreshInterval,
    });

  // Delete flow state
  const [pendingDelete, setPendingDelete] = useState<CurriculumSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDeleteConfirm = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      const res = await authFetch(`/api/v1/curricula/${pendingDelete.id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Server error ${res.status}`);
      }
      // Optimistically remove from cache
      await mutate(
        (prev) => prev?.filter((c) => c.id !== pendingDelete.id),
        { revalidate: false }
      );
      setPendingDelete(null);
    } catch (err) {
      setDeleteError((err as Error).message || "Failed to delete curriculum.");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-6 py-10 md:py-16">
      <PageHeader count={data?.length} />

      {/* Polling indicator */}
      <AnimatePresence>
        {isValidating && !isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mt-3 flex items-center gap-2 text-xs text-ink-soft/60"
          >
            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            Checking for updates…
          </motion.div>
        )}
      </AnimatePresence>

      {/* Delete error */}
      <AnimatePresence>
        {deleteError && (
          <div className="mt-4">
            <DeleteErrorToast
              message={deleteError}
              onDismiss={() => setDeleteError(null)}
            />
          </div>
        )}
      </AnimatePresence>

      <div className="mt-10">
        {isLoading ? (
          <LoadingSkeleton />
        ) : error ? (
          <ErrorState message={(error as Error).message} />
        ) : !data || data.length === 0 ? (
          <EmptyState />
        ) : (
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3"
          >
            {data.map((curriculum, index) => (
              <CurriculumCard
                key={curriculum.id}
                curriculum={curriculum}
                index={index}
                onDelete={(id) => {
                  const target = data.find((c) => c.id === id) ?? null;
                  setPendingDelete(target);
                }}
              />
            ))}
          </motion.div>
        )}
      </div>

      {/* Delete confirm modal */}
      <AnimatePresence>
        {pendingDelete && (
          <DeleteModal
            title={pendingDelete.title}
            onConfirm={handleDeleteConfirm}
            onCancel={() => {
              if (!deleting) {
                setPendingDelete(null);
                setDeleteError(null);
              }
            }}
            deleting={deleting}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
