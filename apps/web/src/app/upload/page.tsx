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
} from "lucide-react";
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

/* ── Page ─────────────────────────────────────────────────────────────────── */
export default function UploadPage() {
  const [videoUrl, setVideoUrl] = useState("");
  const [draggedFile, setDraggedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [success, setSuccess] = useState(false);
  const router = useRouter();

  /* ── Form submit ──────────────────────────────────────────────────────── */
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setLoading(true);
    setProgress(10);

    try {
      const tick = setInterval(() => {
        setProgress((p) => Math.min(p + 8, 85));
      }, 400);

      const res = await authFetch("/api/v1/curricula", {
        method: "POST",
        body: JSON.stringify({
          video_url: videoUrl,
          title: draggedFile?.name ?? "Uploaded curriculum",
        }),
      });

      clearInterval(tick);

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Server error ${res.status}`);
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

  /* ── Render ─────────────────────────────────────────────────────────── */
  return (
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
                onClear={() => setDraggedFile(null)}
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
                    if (e.target.value) setDraggedFile(null);
                  }}
                  placeholder="https://www.youtube.com/watch?v=…"
                  disabled={loading || !!draggedFile}
                  className="w-full bg-transparent font-mono text-sm text-ink outline-none
                             placeholder:text-ink-soft/40"
                  aria-label="YouTube video URL"
                />
              </label>

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
    </div>
  );
}
