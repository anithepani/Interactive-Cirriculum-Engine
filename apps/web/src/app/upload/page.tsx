/**
 * Upload Page — /upload (light-theme redesign)
 * ---------------------------------------------
 * Aligned with the site's LIGHT design system:
 *   - Background: bg-canvas (#f4f4f4)
 *   - Text: text-ink (#111111), text-ink-soft (#4b4b4b)
 *   - Container card: bg-white border border-ink/10 rounded-[2rem]
 *   - Accents: indigo-500 → purple-600 gradient
 *   - Typography: font-display (Space Grotesk) headings, Inter body
 *   - Framer Motion for panel transitions and progress bar
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle,
  AlertTriangle,
  X,
  Youtube,
  Sparkles,
  Loader2,
  Info,
  PlayCircle,
  TrendingUp,
} from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import UploadZone from "@/components/UploadZone";
import { authFetch } from "@/lib/auth";
import { cn } from "@/lib/utils";

/* ── Framer Motion variants ─────────────────────────────────────────────── */
const panelVariants = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.45, ease: "easeOut" as const } },
  exit: { opacity: 0, y: -16, transition: { duration: 0.25, ease: "easeIn" as const } },
};

/* ── Sub-components ─────────────────────────────────────────────────────── */

/** Red alert banner for errors — light theme (rose-50 bg) */
function ErrorToast({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.2 }}
      role="alert"
      className="flex items-start gap-3 rounded-2xl border border-rose-200
                 bg-rose-50 px-4 py-3 text-rose-700 shadow-sm"
    >
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-rose-500" />
      <p className="flex-1 text-sm">{message}</p>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss error"
        className="text-rose-400 transition hover:text-rose-600"
      >
        <X className="h-4 w-4" />
      </button>
    </motion.div>
  );
}

/** Friendly modal shown when the backend rejects a duplicate YouTube video (409). */
function DuplicateModal({
  message,
  curriculumId,
  onDismiss,
  onView,
}: {
  message: string;
  curriculumId: number | null;
  onDismiss: () => void;
  onView: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 px-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="duplicate-modal-title"
      onClick={onDismiss}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.94, y: 12 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.94, y: 12 }}
        transition={{ type: "spring", stiffness: 260, damping: 22 }}
        className="w-full max-w-md rounded-[2rem] border border-ink/10 bg-white p-7 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-3">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-amber-100 text-amber-600">
            <Info className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <p
              id="duplicate-modal-title"
              className="font-display text-lg font-bold text-ink"
            >
              Already in your workspace
            </p>
            <p className="mt-1.5 text-sm leading-relaxed text-ink-soft">
              {message}
            </p>
          </div>
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss"
            className="text-ink-soft/60 transition hover:text-ink"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-6 flex flex-col gap-2.5 sm:flex-row-reverse">
          {curriculumId !== null && (
            <button
              type="button"
              onClick={onView}
              className="flex items-center justify-center gap-2 rounded-full bg-gradient-to-r
                         from-indigo-500 to-purple-600 px-5 py-2.5 text-sm font-semibold text-white
                         shadow-md shadow-indigo-200 transition hover:shadow-indigo-300"
            >
              Open existing curriculum
            </button>
          )}
          <button
            type="button"
            onClick={onDismiss}
            className="rounded-full border border-ink/15 px-5 py-2.5 text-sm font-medium
                       text-ink-soft transition hover:border-ink/30 hover:text-ink"
          >
            Try another video
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
}

/** Animated indigo progress bar */
function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-ink/8">
      <motion.div
        className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500"
        initial={{ width: "0%" }}
        animate={{ width: `${value}%` }}
        transition={{ duration: 0.5, ease: "easeOut" as const }}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
      />
    </div>
  );
}

/** Info card — matches the landing page's light card style */
function InfoCard({ heading, bullets }: { heading: string; bullets: string[] }) {
  return (
    <div className="rounded-2xl border border-ink/10 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <Info className="h-4 w-4 shrink-0 text-indigo-500" />
        <p className="font-display text-sm font-semibold text-ink">{heading}</p>
      </div>
      <ul className="mt-3 space-y-1.5 text-sm text-ink-soft">
        {bullets.map((b) => (
          <li key={b} className="flex items-start gap-2">
            {/* Lime dot — matches the landing page pricing bullet style */}
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-lime" />
            {b}
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── Difficulty selector ────────────────────────────────────────────────── */
type Difficulty = "easy" | "medium" | "hard";

const DIFFICULTY_OPTIONS: { value: Difficulty; label: string; hint: string }[] = [
  { value: "easy", label: "Easy", hint: "Fewer, gentler checkpoints" },
  { value: "medium", label: "Medium", hint: "Balanced pacing" },
  { value: "hard", label: "Hard", hint: "Frequent, tougher checkpoints" },
];

/**
 * Segmented control for choosing the curriculum difficulty. Styled with the
 * existing design tokens (ink / indigo→purple gradient). The active pill uses
 * the same gradient as the primary submit button so it reads as "selected".
 */
function DifficultySelector({
  value,
  onChange,
  disabled,
}: {
  value: Difficulty;
  onChange: (d: Difficulty) => void;
  disabled?: boolean;
}) {
  return (
    <div className={cn(disabled && "pointer-events-none opacity-40")}>
      <span className="flex items-center gap-1.5 text-xs font-medium text-ink-soft">
        <Sparkles className="h-4 w-4 text-indigo-500" />
        Difficulty
      </span>
      <div
        role="radiogroup"
        aria-label="Curriculum difficulty"
        className="mt-2 grid grid-cols-3 gap-2 rounded-2xl border border-ink/10 bg-ink/[0.02] p-1.5"
      >
        {DIFFICULTY_OPTIONS.map((opt) => {
          const active = value === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              role="radio"
              aria-checked={active}
              disabled={disabled}
              onClick={() => onChange(opt.value)}
              title={opt.hint}
              className={cn(
                "rounded-xl px-3 py-2 text-sm font-semibold transition-all duration-200",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400",
                active
                  ? "bg-gradient-to-r from-indigo-500 to-purple-600 text-white shadow-md shadow-indigo-200"
                  : "text-ink-soft hover:bg-white hover:text-ink"
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

const TRENDING_VIDEOS = [
  { title: "React in 100 Seconds", author: "Fireship", duration: "1:45", url: "https://youtube.com/watch?v=Tn6-PIqc4UM", bg: "from-cyan-400 to-blue-500" },
  { title: "Python for Beginners", author: "Programming with Mosh", duration: "1:00:00", url: "https://youtube.com/watch?v=_uQrJ0TkZlc", bg: "from-yellow-400 to-orange-500" },
  { title: "Next.js App Router", author: "Vercel", duration: "45:00", url: "https://youtube.com/watch?v=ZBRKVBOSNKc", bg: "from-zinc-800 to-black" },
  { title: "What is Machine Learning?", author: "CodeBullet", duration: "12:30", url: "https://youtube.com/watch?v=f_uwKZIAeM0", bg: "from-fuchsia-500 to-purple-600" }
];
/* ── Page ─────────────────────────────────────────────────────────────────── */
/** Details of a detected duplicate curriculum (surfaced via a friendly modal). */
interface DuplicateInfo {
  message: string;
  curriculumId: number | null;
}

export default function UploadPage() {
  const [videoUrl, setVideoUrl] = useState("");
  const [draggedFile, setDraggedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [success, setSuccess] = useState(false);
  const [duplicate, setDuplicate] = useState<DuplicateInfo | null>(null);
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const router = useRouter();

  /* ── Form submit ──────────────────────────────────────────────────────── */
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setDuplicate(null);
    setSuccess(false);

    setLoading(true);
    setProgress(10);

    try {
      const tick = setInterval(() => {
        setProgress((p) => Math.min(p + 8, 85));
      }, 400);

      // Local file upload path: multipart/form-data → /curricula/upload. The
      // authFetch helper leaves FormData bodies alone (no forced JSON header)
      // so the browser sets the multipart boundary itself. YouTube URLs keep
      // using the JSON /curricula endpoint below.
      let res: Response;
      if (draggedFile && !videoUrl) {
        const form = new FormData();
        form.append("file", draggedFile);
        form.append("title", draggedFile.name);
        form.append("difficulty", difficulty);
        res = await authFetch("/api/v1/curricula/upload", {
          method: "POST",
          body: form,
        });
      } else {
        res = await authFetch("/api/v1/curricula", {
          method: "POST",
          body: JSON.stringify({
            video_url: videoUrl,
            title: draggedFile?.name ?? "Uploaded curriculum",
            difficulty,
          }),
        });
      }

      clearInterval(tick);

      if (!res.ok) {
        // Try to parse a structured FastAPI error ({ detail: {...} }). A 409
        // with code "duplicate_curriculum" gets a friendly modal instead of the
        // raw JSON error banner.
        let payload: unknown = null;
        try {
          payload = await res.json();
        } catch {
          payload = null;
        }
        const detail = (payload as { detail?: unknown })?.detail;

        if (
          res.status === 409 &&
          detail &&
          typeof detail === "object" &&
          (detail as { code?: string }).code === "duplicate_curriculum"
        ) {
          const d = detail as { message?: string; curriculum_id?: number };
          setProgress(0);
          setDuplicate({
            message:
              d.message ?? "This video is already in your workspace.",
            curriculumId: d.curriculum_id ?? null,
          });
          return;
        }

        // Fall back to a readable message for any other error shape.
        let message = `Server error ${res.status}`;
        if (typeof detail === "string") {
          message = detail;
        } else if (detail && typeof detail === "object") {
          message =
            (detail as { message?: string }).message ?? JSON.stringify(detail);
        } else if (payload && typeof payload === "string") {
          message = payload;
        }
        throw new Error(message);
      }

      const body = await res.json();
      setProgress(100);
      setSuccess(true);

      setTimeout(() => {
        router.push(`/curriculum/${body.curriculum_id}`);
      }, 1800);
    } catch (err) {
      setProgress(0);
      setError((err as Error).message || "Failed to upload. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const canSubmit = !loading && !success && (!!videoUrl || !!draggedFile);

  return (
    <AppLayout>
      <div className="mx-auto max-w-2xl px-6 py-10 md:py-16">
        {/* ── Page header ─────────────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" as const }}
        className="mb-8"
      >
        <p className="font-mono text-xs uppercase tracking-widest text-indigo-500">
          Create new
        </p>
        <h1 className="mt-2 font-display text-4xl font-black text-ink md:text-5xl">
          Upload Curriculum
        </h1>
        {/* Gradient underline */}
        <div className="mt-3 h-1 w-20 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500" />
        <p className="mt-4 text-sm leading-relaxed text-ink-soft">
          Paste a YouTube URL <em>or</em> drop a local video file to generate an
          interactive course with AI-powered checkpoints.
        </p>
      </motion.div>

      {/* ── Main white card container ───────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" as const }}
        className="rounded-[2rem] border border-ink/10 bg-white p-6 shadow-sm md:p-8"
      >
        {/* Error toast */}
        <AnimatePresence>
          {error && (
            <div className="mb-6">
              <ErrorToast message={error} onDismiss={() => setError(null)} />
            </div>
          )}
        </AnimatePresence>

        {/* ── Success panel ────────────────────────────────────────────── */}
        <AnimatePresence mode="wait">
          {success ? (
            <motion.div
              key="success"
              variants={panelVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="flex flex-col items-center gap-5 py-10 text-center"
            >
              <motion.div
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: "spring", stiffness: 200, damping: 16, delay: 0.1 }}
                className="flex h-20 w-20 items-center justify-center rounded-full bg-emerald-100"
              >
                <CheckCircle className="h-10 w-10 text-emerald-600" />
              </motion.div>

              <div>
                <p className="font-display text-xl font-bold text-ink">
                  Curriculum uploaded!
                </p>
                <p className="mt-2 text-sm text-ink-soft">
                  Redirecting to your curriculum…
                </p>
              </div>

              <div className="w-full max-w-xs">
                <ProgressBar value={100} />
              </div>
            </motion.div>
          ) : (
            /* ── Form ──────────────────────────────────────────────────── */
            <motion.form
              key="form"
              variants={panelVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              onSubmit={submit}
              className="space-y-6"
              noValidate
            >
              {/* Drag-and-drop zone */}
              <UploadZone
                onFileSelect={(file) => {
                  setDraggedFile(file);
                  setVideoUrl("");
                }}
                selectedFile={draggedFile}
                onClear={() => {
                  setDraggedFile(null);
                }}
                disabled={loading}
              />

              {/* Divider */}
              <div className="relative flex items-center gap-3">
                <div className="h-px flex-1 bg-ink/10" />
                <span className="text-xs font-medium text-ink-soft">or</span>
                <div className="h-px flex-1 bg-ink/10" />
              </div>

              {/* YouTube URL input */}
              <label
                className={cn(
                  "flex cursor-text flex-col gap-2 rounded-2xl border border-ink/10 bg-ink/[0.02] p-4",
                  "transition-colors duration-200 focus-within:border-indigo-400 focus-within:bg-indigo-50/40",
                  draggedFile && "pointer-events-none opacity-40"
                )}
              >
                <span className="flex items-center gap-1.5 text-xs font-medium text-ink-soft">
                  <Youtube className="h-4 w-4 text-red-500" />
                  YouTube URL
                </span>
                <input
                  id="youtube-url-input"
                  type="url"
                  value={videoUrl}
                  onChange={(e) => {
                    setVideoUrl(e.target.value);
                    if (e.target.value) {
                      setDraggedFile(null);
                    }
                  }}
                  placeholder="https://www.youtube.com/watch?v=…"
                  disabled={loading || !!draggedFile}
                  className="w-full bg-transparent font-mono text-sm text-ink outline-none
                             placeholder:text-ink-soft/40"
                  aria-label="YouTube video URL"
                />
              </label>

              {/* Difficulty selector (Phase 4) */}
              <DifficultySelector
                value={difficulty}
                onChange={setDifficulty}
                disabled={loading}
              />

              {/* Progress bar (while loading) */}
              <AnimatePresence>
                {loading && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="space-y-2 overflow-hidden"
                  >
                    <div className="flex items-center justify-between text-xs text-ink-soft">
                      <span>Processing…</span>
                      <span>{progress}%</span>
                    </div>
                    <ProgressBar value={progress} />
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Submit button */}
              <motion.button
                type="submit"
                id="generate-curriculum-btn"
                disabled={!canSubmit}
                whileHover={canSubmit ? { scale: 1.02 } : {}}
                whileTap={canSubmit ? { scale: 0.98 } : {}}
                className={cn(
                  "flex w-full items-center justify-center gap-2 rounded-full",
                  "px-6 py-3.5 text-sm font-semibold text-white",
                  "transition-all duration-200 focus-visible:outline-none",
                  "focus-visible:ring-2 focus-visible:ring-indigo-400",
                  canSubmit
                    ? "bg-gradient-to-r from-indigo-500 to-purple-600 shadow-md shadow-indigo-200 hover:shadow-indigo-300"
                    : "cursor-not-allowed bg-ink/20 text-ink-soft opacity-60"
                )}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating curriculum…
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Generate curriculum
                  </>
                )}
              </motion.button>
            </motion.form>
          )}
        </AnimatePresence>
      </motion.div>

      {/* ── Info cards ──────────────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.25, ease: "easeOut" as const }}
        className="mt-6 grid gap-4 sm:grid-cols-2"
      >
        <InfoCard
          heading="What happens next?"
          bullets={[
            "The AI extracts key segments from your video.",
            "Checkpoints (MCQ, coding, debug) are generated per concept.",
            "You can open the interactive player instantly.",
          ]}
        />
        <InfoCard
          heading="Tips for best results"
          bullets={[
            "Use a public YouTube tutorial (English recommended).",
            "Keep videos under 20 minutes for faster processing.",
            "Longer videos are supported but may take a few minutes.",
          ]}
        />
      </motion.div>

      {/* ── Trending Videos Carousel ────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.35, ease: "easeOut" as const }}
        className="mt-12 mb-8"
      >
        <div className="flex items-center gap-2 mb-6">
          <TrendingUp className="h-5 w-5 text-indigo-500" />
          <h2 className="font-display text-xl font-bold text-ink">Trending & Recommended</h2>
        </div>
        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide snap-x">
          {TRENDING_VIDEOS.map((video, idx) => (
            <button
              key={idx}
              onClick={() => {
                setVideoUrl(video.url);
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              className="group relative flex shrink-0 snap-start flex-col gap-3 rounded-[1.5rem] p-3 transition hover:bg-white hover:shadow-sm sm:w-[280px]"
            >
              <div className={`flex h-36 w-full items-center justify-center rounded-2xl bg-gradient-to-br ${video.bg} shadow-inner transition-transform group-hover:scale-[1.02]`}>
                <PlayCircle className="h-12 w-12 text-white/80 transition group-hover:scale-110 group-hover:text-white" />
                <div className="absolute bottom-5 right-5 rounded-md bg-black/60 px-2 py-1 text-xs font-medium text-white backdrop-blur-sm">
                  {video.duration}
                </div>
              </div>
              <div className="text-left px-1">
                <h3 className="line-clamp-1 font-display font-semibold text-ink transition group-hover:text-indigo-600">
                  {video.title}
                </h3>
                <p className="text-sm text-ink-soft">{video.author}</p>
              </div>
            </button>
          ))}
        </div>
      </motion.div>

      </div>

      {/* ── Duplicate-video modal (409 from the backend) ─────────────────── */}
      <AnimatePresence>
        {duplicate && (
          <DuplicateModal
            message={duplicate.message}
            curriculumId={duplicate.curriculumId}
            onDismiss={() => setDuplicate(null)}
            onView={() => {
              if (duplicate.curriculumId !== null) {
                router.push(`/curriculum/${duplicate.curriculumId}`);
              }
            }}
          />
        )}
      </AnimatePresence>
    </AppLayout>
  );
}
