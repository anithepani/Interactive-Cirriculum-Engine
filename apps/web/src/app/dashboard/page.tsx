"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Video, RefreshCw, AlertTriangle, Trash2, X, ChevronRight, BookOpen, Clock, Activity, Flame } from "lucide-react";
import LoadingSpinner from "@/components/LoadingSpinner";
import CurriculumCard from "@/components/CurriculumCard";
import AppLayout from "@/components/layout/AppLayout";
import { DashboardAreaChart, DashboardDonutChart, MiniCalendar } from "@/components/dashboard/Charts";
import { authFetcher, authFetch, getCurrentUser, type AuthUser } from "@/lib/auth";
import { staggerContainer } from "@/lib/motion";
import type { CurriculumSummary, StatsOverview } from "@/lib/types";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

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

/* ── Hero Banner ───────────────────────────────────────────────────────── */
function HeroBanner({ user }: { user: AuthUser | null }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="relative overflow-hidden rounded-[2rem] bg-gradient-to-br from-indigo-600 via-purple-600 to-fuchsia-600 p-8 text-white shadow-lg md:p-10"
    >
      <div className="relative z-10 flex flex-col items-start gap-4 md:flex-row md:items-center md:justify-between">
        <div className="max-w-xl">
          <h1 className="font-display text-3xl font-bold tracking-tight md:text-4xl">
            Welcome back, {user ? user.name.split(" ")[0] : "Learner"}!
          </h1>
          <p className="mt-3 text-sm text-white/80 md:text-base leading-relaxed">
            Sharpen your skills with professional interactive courses automatically generated from your favorite videos.
          </p>
          <div className="mt-8">
            <Link
              href="/upload"
              className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-bold text-indigo-600 shadow-md transition hover:scale-105 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
            >
              Upload New Curriculum
              <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
        
        {/* Decorative Graphic element */}
        <div className="hidden opacity-50 md:block absolute right-0 top-0 translate-x-1/4 -translate-y-1/4">
           <svg width="300" height="300" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
              <path fill="#ffffff" d="M44.7,-76.4C58.8,-69.2,71.8,-59.1,81.1,-46.3C90.4,-33.5,96,-18,94.4,-3C92.8,12,84,25.6,73.4,36.5C62.8,47.4,50.4,55.5,37.3,62.7C24.2,69.9,10.4,76.2,-4.3,83.7C-19.1,91.2,-34.7,99.9,-47.4,96.3C-60.1,92.7,-69.8,76.8,-76.4,60.8C-83,44.8,-86.5,28.8,-87.3,13.2C-88.1,-2.4,-86.2,-17.6,-80.7,-31.8C-75.2,-46,-66,-59.2,-53.4,-67.2C-40.8,-75.2,-24.8,-78,-9.2,-78.9C6.4,-79.8,22.8,-78.8,44.7,-76.4Z" transform="translate(100 100) scale(1.1)" />
            </svg>
        </div>
      </div>
    </motion.div>
  );
}

/* ── Statistics Row ────────────────────────────────────────────────────── */
function StatsRow({ data }: { data: CurriculumSummary[] | undefined }) {
  // Live metrics from the backend (Block D). Falls back to the curricula count
  // for the first card while the stats request is in flight so the row never
  // renders empty.
  const { data: stats } = useSWR<StatsOverview>("/api/v1/stats/overview", authFetcher);

  const curricula = stats?.total_curricula ?? data?.length ?? 0;
  const exercises = stats?.completed_exercises ?? 0;
  const hours = stats?.hours_learned ?? 0;

  return (
    <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
      <div className="flex items-center gap-4 rounded-3xl border border-ink/5 bg-white p-5 shadow-sm">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-indigo-600">
          <BookOpen className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs font-medium text-ink-soft uppercase tracking-wider">Curricula</p>
          <p className="font-display text-xl font-bold text-ink">{curricula}</p>
        </div>
      </div>
      
      <div className="flex items-center gap-4 rounded-3xl border border-ink/5 bg-white p-5 shadow-sm">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-pink-50 text-pink-600">
          <Activity className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs font-medium text-ink-soft uppercase tracking-wider">Exercises Done</p>
          <p className="font-display text-xl font-bold text-ink">{exercises}</p>
        </div>
      </div>
      
      <div className="flex items-center gap-4 rounded-3xl border border-ink/5 bg-white p-5 shadow-sm">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-blue-50 text-blue-600">
          <Clock className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs font-medium text-ink-soft uppercase tracking-wider">Hours Learned</p>
          <p className="font-display text-xl font-bold text-ink">{hours}</p>
        </div>
      </div>
    </div>
  );
}

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
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      {[...Array(2)].map((_, i) => (
        <div key={i} className="h-64 animate-pulse rounded-[2rem] border border-ink/10 bg-ink/5" style={{ animationDelay: `${i * 0.1}s` }} />
      ))}
    </div>
  );
}

/* ── Right Sidebar Stats Placeholder ───────────────────────────────────── */
function RightSidebarStats({ user, data }: { user: AuthUser | null, data?: CurriculumSummary[] }) {
  return (
    <div className="rounded-[2.5rem] border border-ink/5 bg-white p-8 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg font-bold text-ink">Statistic</h3>
        <button className="text-ink-soft hover:text-ink">
          <span className="sr-only">More options</span>
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
          </svg>
        </button>
      </div>

      <div className="mt-8 flex flex-col items-center">
        <div className="relative flex h-32 w-32 items-center justify-center rounded-full border-[6px] border-indigo-100">
          {/* Faux progress ring */}
          <svg className="absolute inset-0 h-full w-full -rotate-90 transform" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="46" fill="transparent" stroke="currentColor" strokeWidth="8" className="text-indigo-600" strokeDasharray="289" strokeDashoffset="180" strokeLinecap="round" />
          </svg>
          <Avatar className="h-20 w-20">
            <AvatarImage src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${user?.name || 'ICE'}`} />
            <AvatarFallback>{user?.name?.[0] || 'U'}</AvatarFallback>
          </Avatar>
        </div>
        <div className="mt-6 text-center">
          <h4 className="flex items-center justify-center gap-1 font-display text-xl font-bold text-ink">
            Good Morning {user?.name?.split(" ")[0] || "Learner"} <Flame className="h-5 w-5 text-orange-500 fill-orange-500" />
          </h4>
          <p className="mt-2 text-sm text-ink-soft">Continue your learning to achieve your target!</p>
        </div>
      </div>

      <div className="mt-10">
         <div className="mb-4 flex items-center justify-between">
           <h3 className="font-display text-lg font-bold text-ink">Recent Activity</h3>
         </div>
         <div className="space-y-4">
           {(!data || data.length === 0) ? (
             <p className="text-sm text-ink-soft text-center py-4">No recent activity</p>
           ) : (
             data.slice(0, 3).map((item) => (
               <div key={item.id} className="flex items-center justify-between rounded-2xl border border-ink/5 p-3 hover:bg-ink/5 transition-colors">
                 <div className="flex items-center gap-3 overflow-hidden">
                   <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                     <BookOpen className="h-5 w-5" />
                   </div>
                   <div className="min-w-0">
                     <p className="text-sm font-bold text-ink truncate">{item.title}</p>
                     <p className="text-xs text-ink-soft capitalize">{item.status}</p>
                   </div>
                 </div>
               </div>
             ))
           )}
         </div>
      </div>
    </div>
  );
}

/* ── Page ──────────────────────────────────────────────────────────────── */
export default function DashboardPage() {
  const [user, setUser] = useState<AuthUser | null>(null);

  const fetchUser = () => {
    getCurrentUser().then(setUser);
  };

  useEffect(() => {
    fetchUser();
    window.addEventListener("userUpdated", fetchUser);
    return () => window.removeEventListener("userUpdated", fetchUser);
  }, []);

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

  return (
    <AppLayout>
      <div className="grid grid-cols-1 gap-8 xl:grid-cols-3">
        {/* Main Content Column (Banner + Curricula) */}
        <div className="flex flex-col gap-8 xl:col-span-2">
          
          <HeroBanner user={user} />
          
          <StatsRow data={data} />

          {/* Project Analytics Chart */}
          <div className="rounded-[2.5rem] border border-ink/5 bg-white p-8 shadow-sm">
            <h2 className="mb-6 font-display text-xl font-bold text-ink">Learning Analytics</h2>
            <DashboardAreaChart data={data || []} />
          </div>

          {/* Continue Watching Section */}
          <div className="mt-4">
            <div className="mb-6 flex items-center justify-between">
              <h2 className="font-display text-2xl font-bold text-ink">Continue Watching</h2>
              <div className="flex items-center gap-2">
                <AnimatePresence>
                  {isValidating && !isLoading && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex items-center gap-1 text-xs text-ink-soft">
                      <RefreshCw className="h-3 w-3 animate-spin" />
                      Syncing
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>

            {deleteError && (
              <div className="mb-4 flex items-center gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700">
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
              <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="grid grid-cols-1 gap-6 md:grid-cols-2">
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
        </div>

        {/* Right Sidebar Column (Stats & Mentors) */}
        <div className="flex flex-col gap-8 xl:col-span-1">
          <RightSidebarStats user={user} data={data} />

          <div className="rounded-[2.5rem] border border-ink/5 bg-white p-8 shadow-sm">
            <h2 className="mb-6 font-display text-xl font-bold text-ink">Project Progress</h2>
            <DashboardDonutChart data={data || []} />
          </div>

          <div className="rounded-[2.5rem] border border-ink/5 bg-white p-8 shadow-sm">
            <MiniCalendar data={data || []} />
          </div>
        </div>
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
