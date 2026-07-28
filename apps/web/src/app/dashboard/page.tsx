"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Video, RefreshCw, AlertTriangle, Trash2, X, ChevronRight, BookOpen, Clock, Activity, Flame, CheckCircle } from "lucide-react";
import LoadingSpinner from "@/components/LoadingSpinner";
import CurriculumCard from "@/components/CurriculumCard";
import AppLayout from "@/components/layout/AppLayout";

import { DashboardAreaChart, DashboardDonutChart, MiniCalendar } from "@/components/dashboard/Charts";
import { authFetcher, authFetch, getCurrentUser, type AuthUser } from "@/lib/auth";
import { staggerContainer } from "@/lib/motion";
import type { CurriculumSummary, StatsOverview } from "@/lib/types";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

/* â”€â”€ Polling â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const POLL_INTERVAL = 5_000;

const refreshInterval = (latest?: CurriculumSummary[]) => {
  if (!latest || latest.length === 0) return 0;
  const pending = latest.some(
    (c) => c.status !== "ready" && c.status !== "failed"
  );
  return pending ? POLL_INTERVAL : 0;
};

/* â”€â”€ Delete confirmation modal â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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

/* â”€â”€ Hero Banner â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
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
          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              href="/upload"
              className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-bold text-indigo-600 shadow-md transition hover:scale-105 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
            >
              Upload New Curriculum
              <ChevronRight className="h-4 w-4" />
            </Link>
            <Link
              href="/quiz"
              className="inline-flex items-center gap-2 rounded-full bg-indigo-500/20 border border-white/20 px-6 py-3 text-sm font-bold text-white shadow-md transition hover:scale-105 hover:bg-indigo-500/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/50 backdrop-blur-sm"
            >
              Take Random Quiz
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

/* â”€â”€ Statistics Row â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function StatsRow({ data, stats }: { data: CurriculumSummary[] | undefined, stats: StatsOverview | undefined }) {
  // Live metrics from the backend (Block D). Falls back to the curricula count
  // for the first card while the stats request is in flight so the row never
  // renders empty.

  const curricula = stats?.total_curricula ?? data?.length ?? 0;
  const exercises = stats?.completed_exercises ?? 0;
  const hours = stats?.hours_learned ?? 0;
  const correct = stats?.correct_exercises ?? 0;
  const accuracy = exercises > 0 ? Math.round((correct / exercises) * 100) : 0;

  return (
    <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
      
      <div className="flex items-center gap-4 rounded-3xl border border-ink/5 bg-white p-5 shadow-sm">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
          <Flame className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs font-medium text-ink-soft uppercase tracking-wider">Accuracy Rate</p>
          <p className="font-display text-xl font-bold text-ink">{accuracy}%</p>
        </div>
      </div>
    </div>
  );
}

/* â”€â”€ Empty & Error States â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function EmptyState() {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className="flex flex-col items-center justify-center gap-6 rounded-[2rem] border border-indigo-100 bg-gradient-to-b from-white to-indigo-50/50 py-16 px-8 text-center shadow-lg relative overflow-hidden"
    >
      <div className="absolute -top-12 -right-12 w-32 h-32 bg-indigo-500/10 blur-[40px] rounded-full pointer-events-none" />
      <div className="absolute -bottom-12 -left-12 w-32 h-32 bg-purple-500/10 blur-[40px] rounded-full pointer-events-none" />

      <motion.div
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
        className="flex h-20 w-20 items-center justify-center rounded-[2rem] bg-indigo-100 text-indigo-600 shadow-xl shadow-indigo-200/50 relative z-10"
      >
        <Video className="h-10 w-10" />
      </motion.div>
      <div className="max-w-sm space-y-3 relative z-10">
        <p className="font-display text-2xl font-bold text-ink tracking-tight">Your Curriculum Awaits</p>
        <p className="text-sm leading-relaxed text-ink-soft">
          You don't have any generated curricula yet. Paste a YouTube link or upload a video to create your first interactive learning experience!
        </p>
      </div>
      <Link
        href="/upload"
        className="mt-2 inline-flex items-center gap-2 rounded-full bg-indigo-600 px-6 py-3 text-sm font-bold text-white shadow-xl shadow-indigo-600/30 transition hover:scale-105 hover:bg-indigo-700 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 relative z-10"
      >
        <Plus className="h-5 w-5" />
        Create Curriculum
      </Link>
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

/* â”€â”€ Right Sidebar Stats Placeholder â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
function RightSidebarStats({ user, data, stats }: { user: AuthUser | null, data?: CurriculumSummary[], stats?: StatsOverview }) {
  // Goal: 5 hours of learning per week
  const goalHours = 5;
  const hoursLearned = stats?.watched_seconds ? stats.watched_seconds / 3600 : 0;
  const progressPercent = Math.min((hoursLearned / goalHours) * 100, 100);
  const strokeDashoffset = 289 - (289 * progressPercent) / 100;

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
        <div className="relative flex h-32 w-32 items-center justify-center rounded-full border-[6px] border-indigo-50">
          {/* Dynamic progress ring */}
          <svg className="absolute inset-0 h-full w-full -rotate-90 transform drop-shadow-md" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="46" fill="transparent" stroke="currentColor" strokeWidth="8" className="text-indigo-500 transition-all duration-1000 ease-out" strokeDasharray="289" strokeDashoffset={strokeDashoffset} strokeLinecap="round" />
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

/* â”€â”€ Page â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
export default function DashboardPage() {
  const [user, setUser] = useState<AuthUser | null>(null);

  const fetchUser = () => {
    getCurrentUser().then(setUser);
  };

  const [progressMessage, setProgressMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchUser();
    window.addEventListener("userUpdated", fetchUser);
    
    let es: EventSource | null = null;
    let timer: NodeJS.Timeout;

    const connectSSE = async () => {
      try {
        const res = await authFetch("/api/v1/events/token", { method: "POST" });
        if (!res.ok) return;
        const { token } = await res.json();
        
        es = new EventSource(`/api/v1/events/stream?token=${encodeURIComponent(token)}`);
        
        es.addEventListener("notification", (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "curriculum_progress") {
              setProgressMessage(data.message);
              clearTimeout(timer);
              if (data.message !== "Curriculum is ready!") {
                 timer = setTimeout(() => setProgressMessage(null), 15000);
              } else {
                 timer = setTimeout(() => {
                    setProgressMessage(null);
                    mutate();
                 }, 3000);
              }
            }
          } catch (e) {}
        });
      } catch (e) {}
    };
    
    connectSSE();

    return () => {
      window.removeEventListener("userUpdated", fetchUser);
      if (es) es.close();
      clearTimeout(timer);
    };
  }, []);

  const { data, error, isLoading, isValidating, mutate } =
    useSWR<CurriculumSummary[]>("/api/v1/curricula", authFetcher, {
      refreshInterval,
    });
    
  const { data: stats } = useSWR<StatsOverview>("/api/v1/stats/overview", authFetcher);

  // Undo Delete Flow
  const [undoToast, setUndoToast] = useState<{ id: number; title: string; timeoutId: NodeJS.Timeout } | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDeleteClick = (curriculum: CurriculumSummary) => {
    // Optimistic UI removal
    mutate((prev) => prev?.filter((c) => c.id !== curriculum.id), { revalidate: false });
    
    if (undoToast) clearTimeout(undoToast.timeoutId);
    
    const timeoutId = setTimeout(async () => {
      setUndoToast(null);
      try {
        const res = await authFetch(`/api/v1/curricula/${curriculum.id}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Delete failed");
      } catch (err) {
        mutate(); // Revert on failure
        setDeleteError("Failed to delete " + curriculum.title);
      }
    }, 5000);
    
    setUndoToast({ id: curriculum.id, title: curriculum.title, timeoutId });
  };

  const handleUndo = () => {
    if (!undoToast) return;
    clearTimeout(undoToast.timeoutId);
    setUndoToast(null);
    mutate(); // Revert optimistic removal
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl grid grid-cols-1 gap-8 xl:grid-cols-3">
        {/* Main Content Column */}
        <div className="flex flex-col gap-8 xl:col-span-2">
          
          <HeroBanner user={user} />

          <AnimatePresence>
            {progressMessage && (
              <motion.div
                initial={{ opacity: 0, y: -20, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -10, scale: 0.98 }}
                className="rounded-2xl border border-indigo-200 bg-indigo-50 p-4 shadow-sm flex items-center justify-between"
              >
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-indigo-600 shadow-sm">
                    {progressMessage === "Curriculum is ready!" ? (
                      <CheckCircle className="h-5 w-5 text-emerald-500" />
                    ) : (
                      <RefreshCw className="h-5 w-5 animate-spin" />
                    )}
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-indigo-900">AI Processing Curriculum</h3>
                    <p className="text-sm text-indigo-700/80 mt-0.5">{progressMessage}</p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          
          <StatsRow data={data} stats={stats} />
          
          <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
            <div className="rounded-[2.5rem] border border-ink/5 bg-white p-8 shadow-sm">
              <h2 className="mb-6 font-display text-xl font-bold text-ink">Learning Analytics</h2>
              <DashboardAreaChart data={data || []} />
            </div>
            
            <div className="rounded-[2.5rem] border border-ink/5 bg-white p-8 shadow-sm">
              <h2 className="mb-6 font-display text-xl font-bold text-ink">Topic Retention</h2>
              <DashboardDonutChart data={data || []} />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
            <div className="rounded-[2.5rem] border border-ink/5 bg-white p-8 shadow-sm">
              <h2 className="mb-6 font-display text-xl font-bold text-ink">Category Focus</h2>
              <div className="flex h-48 flex-col justify-end gap-3">
                {(() => {
                  let cats = stats?.categories || [];
                  if (cats.length === 0 && data && data.length > 0) {
                     // Fallback computation
                     const counts: Record<string, number> = {};
                     data.forEach(item => {
                        const t = item.title.toLowerCase();
                        let name = "General";
                        if (t.includes("react") || t.includes("python") || t.includes("code")) name = "Programming";
                        else if (t.includes("ai") || t.includes("data")) name = "Data & AI";
                        else if (t.includes("design") || t.includes("ui")) name = "Design";
                        counts[name] = (counts[name] || 0) + 1;
                     });
                     cats = Object.entries(counts).map(([category, count]) => ({ category, count, percent: 0 }));
                  }

                  if (cats.length === 0) {
                     return <div className="flex h-full items-center justify-center text-sm text-ink-soft">No category data yet</div>;
                  }

                  return cats.slice(0, 4).map((cat, i) => {
                    const max = Math.max(...cats.map(c => c.count));
                    const width = Math.max((cat.count / max) * 100, 5);
                    const colors = ["bg-indigo-500", "bg-rose-500", "bg-emerald-500", "bg-amber-500"];
                    return (
                      <div key={cat.category} className="flex items-center gap-4 text-sm">
                        <div className="w-24 shrink-0 truncate font-semibold text-ink-soft">{cat.category}</div>
                        <div className="flex-1">
                          <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: `${width}%` }}
                            transition={{ duration: 1, delay: i * 0.1 }}
                            className={`h-4 rounded-full ${colors[i % colors.length]}`} 
                          />
                        </div>
                        <div className="w-8 text-right font-bold text-ink">{cat.count}</div>
                      </div>
                    );
                  });
                })()}
              </div>
            </div>
            
            <div className="rounded-[2.5rem] border border-ink/5 bg-white p-8 shadow-sm">
              <MiniCalendar data={data || []} />
            </div>
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
              <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="overflow-hidden rounded-[2rem] border border-ink/5 bg-white shadow-sm">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="border-b border-ink/5 bg-ink/5 text-xs font-semibold uppercase tracking-wider text-ink-soft">
                      <tr>
                        <th className="px-6 py-4">Curriculum Title</th>
                        <th className="px-6 py-4">Status</th>
                        <th className="px-6 py-4">Created Date</th>
                        <th className="px-6 py-4 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-ink/5">
                      {data.map((curriculum, index) => {
                        const isReady = curriculum.status === "ready";
                        const isFailed = curriculum.status === "failed";
                        return (
                          <motion.tr 
                            key={curriculum.id}
                            custom={index}
                            variants={{ hidden: { opacity: 0, y: 10 }, visible: (i) => ({ opacity: 1, y: 0, transition: { delay: i * 0.05 } }) }}
                            className="group transition-colors hover:bg-ink/5"
                          >
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-3">
                                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600 group-hover:bg-indigo-100 group-hover:text-indigo-700 transition">
                                  <Video className="h-5 w-5" />
                                </div>
                                <span className="font-semibold text-ink line-clamp-1">{curriculum.title}</span>
                              </div>
                            </td>
                            <td className="px-6 py-4">
                              <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
                                isReady ? 'bg-emerald-50 text-emerald-600' :
                                isFailed ? 'bg-rose-50 text-rose-600' :
                                'bg-amber-50 text-amber-600'
                              }`}>
                                {isReady && <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />}
                                {isFailed && <span className="h-1.5 w-1.5 rounded-full bg-rose-500" />}
                                {!isReady && !isFailed && <RefreshCw className="h-3 w-3 animate-spin" />}
                                {curriculum.status}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-ink-soft">
                              {curriculum.created_at ? new Date(curriculum.created_at).toLocaleDateString() : 'N/A'}
                            </td>
                            <td className="px-6 py-4 text-right">
                              <div className="flex items-center justify-end gap-2">
                                <Link
                                  href={`/curriculum/${curriculum.id}`}
                                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                                    isReady
                                      ? "bg-indigo-600 text-white hover:bg-indigo-700"
                                      : "bg-ink/5 text-ink-soft hover:bg-ink/10"
                                  }`}
                                >
                                  {isReady ? "View" : "Details"}
                                </Link>
                                <button
                                  onClick={() => handleDeleteClick(curriculum)}
                                  className="rounded-lg p-1.5 text-ink-soft transition hover:bg-rose-50 hover:text-rose-600"
                                  title="Delete Curriculum"
                                >
                                  <Trash2 className="h-4 w-4" />
                                </button>
                              </div>
                            </td>
                          </motion.tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </motion.div>
            )}
          </div>
        </div>

        {/* Right Sidebar Column */}
        <div className="flex flex-col gap-8 xl:col-span-1 sticky top-28 self-start z-10">
          <RightSidebarStats user={user} data={data} stats={stats} />
        </div>
      </div>

      <AnimatePresence>
        {undoToast && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.9 }}
            className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 flex items-center gap-4 rounded-full bg-ink px-6 py-3 text-white shadow-2xl"
          >
            <span className="text-sm font-medium">Deleted &quot;{undoToast.title}&quot;</span>
            <button
              onClick={handleUndo}
              className="text-sm font-bold text-indigo-400 hover:text-indigo-300 transition"
            >
              Undo
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </AppLayout>
  );
}
