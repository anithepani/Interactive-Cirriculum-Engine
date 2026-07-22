"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Video, RefreshCw, AlertTriangle, Trash2, X, ChevronRight, BookOpen, Clock, Activity, Flame } from "lucide-react";
import Link from "next/link";
import LoadingSpinner from "@/components/LoadingSpinner";
import CurriculumCard from "@/components/CurriculumCard";
import AppLayout from "@/components/layout/AppLayout";

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

/* ── Empty & Error States ──────────────────────────────────────────────── */
function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center gap-6 rounded-[2rem] border border-ink/10 bg-white py-20 px-8 text-center shadow-sm"
    >
      <motion.div
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        className="flex h-20 w-20 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-500"
      >
        <Video className="h-10 w-10" />
      </motion.div>
      <div className="max-w-xs space-y-2">
        <p className="font-display text-xl font-bold text-ink">No curricula yet</p>
        <p className="text-sm leading-relaxed text-ink-soft">
          Upload your first video to get started — paste a YouTube URL or drop a local file.
        </p>
      </div>
    </motion.div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-4 rounded-[2rem] border border-rose-200 bg-rose-50 px-6 py-5 text-rose-700">
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-500" />
      <div>
        <p className="font-semibold text-rose-700">Failed to load curricula</p>
        <p className="mt-1 text-sm text-rose-600">{message}</p>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="h-64 animate-pulse rounded-[2rem] border border-ink/10 bg-ink/5" style={{ animationDelay: `${i * 0.1}s` }} />
      ))}
    </div>
  );
}

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
            className="flex-1 rounded-full border border-ink/15 bg-white px-4 py-2.5 text-sm font-semibold text-ink transition hover:bg-ink/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ink/20 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={deleting}
            className="flex flex-1 items-center justify-center gap-2 rounded-full bg-rose-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-rose-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-400 disabled:opacity-50"
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

export default function MyCurriculaPage() {
  const { data, error, isLoading, isValidating, mutate } =
    useSWR<CurriculumSummary[]>("/api/v1/curricula", authFetcher, {
      refreshInterval,
    });

  const [pendingDelete, setPendingDelete] = useState<CurriculumSummary | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDeleteConfirm = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      const res = await authFetch(`/api/v1/curricula/${pendingDelete.id}`, { method: "DELETE" });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Server error ${res.status}`);
      }
      await mutate((prev) => prev?.filter((c) => c.id !== pendingDelete.id), { revalidate: false });
      setPendingDelete(null);
    } catch (err) {
      setDeleteError((err as Error).message || "Failed to delete curriculum.");
    } finally {
      setDeleting(false);
    }
  };

  const [sortOption, setSortOption] = useState<"newest" | "oldest" | "progress">("newest");

  const sortedData = data ? [...data].sort((a, b) => {
    if (sortOption === "newest") {
      return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
    }
    if (sortOption === "oldest") {
      return new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime();
    }
    if (sortOption === "progress") {
      return (b.progress || 0) - (a.progress || 0);
    }
    return 0;
  }) : [];

  return (
    <AppLayout>
      <div className="mx-auto max-w-6xl">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="font-display text-3xl font-bold text-ink">My Curricula</h1>
            <p className="mt-2 text-ink-soft">
              All of the interactive courses you have generated.
            </p>
          </div>
          
          <div className="flex items-center gap-4">
            <AnimatePresence>
              {isValidating && !isLoading && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex items-center gap-1 text-xs text-ink-soft">
                  <RefreshCw className="h-3 w-3 animate-spin" />
                  Syncing
                </motion.div>
              )}
            </AnimatePresence>
            
            <div className="relative">
              <select
                value={sortOption}
                onChange={(e) => setSortOption(e.target.value as any)}
                className="appearance-none rounded-full border border-ink/10 bg-white py-2.5 pl-4 pr-10 text-sm font-semibold text-ink shadow-sm outline-none transition focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 hover:border-ink/20 cursor-pointer"
              >
                <option value="newest">Newest</option>
                <option value="oldest">Oldest</option>
                <option value="progress">Highest Progress</option>
              </select>
              <div className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2">
                <ChevronRight className="h-4 w-4 rotate-90 text-ink-soft" />
              </div>
            </div>

            <Link
              href="/upload"
              className="inline-flex items-center gap-2 rounded-full bg-indigo-600 px-6 py-2.5 text-sm font-bold text-white shadow-md transition hover:scale-105 hover:bg-indigo-700"
            >
              <Plus className="h-4 w-4" />
              New Course
            </Link>
          </div>
        </div>

        {deleteError && (
          <div className="mb-6 flex items-center gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700">
            <AlertTriangle className="h-4 w-4 shrink-0 text-rose-500" />
            <p className="flex-1 text-sm">{deleteError}</p>
            <button onClick={() => setDeleteError(null)} className="text-rose-400 hover:text-rose-600"><X className="h-4 w-4" /></button>
          </div>
        )}

        {isLoading ? (
          <LoadingSkeleton />
        ) : error ? (
          <ErrorState message={(error as Error).message} />
        ) : !data || data.length === 0 ? (
          <EmptyState />
        ) : (
          <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {sortedData.map((curriculum, index) => (
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

      <AnimatePresence>
        {pendingDelete && (
          <DeleteModal
            title={pendingDelete.title}
            onConfirm={handleDeleteConfirm}
            onCancel={() => { if (!deleting) { setPendingDelete(null); setDeleteError(null); } }}
            deleting={deleting}
          />
        )}
      </AnimatePresence>
    </AppLayout>
  );
}
