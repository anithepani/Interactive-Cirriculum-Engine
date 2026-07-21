"use client";

import { useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  MinusCircle,
  AlertTriangle,
  Code,
  HelpCircle,
  FileText,
} from "lucide-react";
import AppLayout from "@/components/layout/AppLayout";
import LoadingSpinner from "@/components/LoadingSpinner";
import { authFetcher } from "@/lib/auth";
import type { CurriculumDetail, Checkpoint } from "@/lib/types";

/* ── Types ─────────────────────────────────────────────────────────────── */
type AttemptStatus = "correct" | "incorrect" | "unattempted";

interface ReviewRow {
  checkpointId: number | string;
  index: number;
  type: string;
  ts: number;
  question: string;
  status: AttemptStatus;
  learnerAnswer: string | null;
  correctAnswer: string | null;
  options?: string[];
  correctOption?: string | null;
  // Shown under the answer matrix when there's no reference code (e.g. legacy
  // debug rows) — falls back to the bug explanation instead of a bare
  // "No reference answer available." (Issue 4)
  fallbackNote?: string | null;
}

/* ── Helpers ───────────────────────────────────────────────────────────── */
const TYPE_LABEL: Record<string, string> = {
  mcq: "Multiple Choice",
  coding: "Coding",
  debug: "Debugging",
  conceptual: "Conceptual",
};

// Derive the human-readable "correct answer" for a checkpoint from whatever
// field the generator populated (varies by exercise type).
function deriveCorrect(cp: Checkpoint): { text: string | null; option: string | null } {
  const ex = cp.exercise;
  if (!ex) return { text: null, option: null };
  const type = cp.exercise_type;

  if (type === "mcq" && Array.isArray(ex.options)) {
    const idx = ex.answer_idx ?? ex.answer_index ?? -1;
    const opt = idx >= 0 && idx < ex.options.length ? ex.options[idx] : null;
    return { text: opt, option: opt };
  }
  if (type === "coding") {
    return { text: ex.reference_solution || ex.solution || null, option: null };
  }
  if (type === "debug") {
    // Issue 4: prefer the corrected code (fixed_code / reference_solution).
    // Legacy debug rows have neither — the caller falls back to bug_explanation.
    return {
      text: ex.fixed_code || ex.reference_solution || ex.solution || null,
      option: null,
    };
  }
  // conceptual
  return { text: ex.reference_answer || null, option: null };
}

function toReviewRow(cp: Checkpoint, index: number): ReviewRow {
  const { text: correctAnswer, option: correctOption } = deriveCorrect(cp);
  const status: AttemptStatus =
    cp.status === "correct" ? "correct" : cp.status === "incorrect" ? "incorrect" : "unattempted";
  // Issue 4: for debug exercises with no stored corrected code (legacy rows),
  // surface the bug explanation as the reference instead of "No reference
  // answer available."
  const fallbackNote =
    cp.exercise_type === "debug" && !correctAnswer && cp.exercise?.bug_explanation
      ? cp.exercise.bug_explanation
      : null;
  return {
    checkpointId: cp.id,
    index,
    type: cp.exercise_type,
    ts: cp.ts,
    question: cp.exercise?.question || cp.exercise?.prompt || "Untitled exercise",
    status,
    learnerAnswer: cp.submitted_answer ?? null,
    correctAnswer,
    options: cp.exercise?.options,
    correctOption,
    fallbackNote,
  };
}

const isCode = (type: string) => type === "coding" || type === "debug";

/* ── Status pill ───────────────────────────────────────────────────────── */
function StatusPill({ status }: { status: AttemptStatus }) {
  if (status === "correct") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
        <CheckCircle2 className="h-3.5 w-3.5" /> Correct
      </span>
    );
  }
  if (status === "incorrect") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-50 px-3 py-1 text-xs font-semibold text-rose-700">
        <XCircle className="h-3.5 w-3.5" /> Incorrect
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-ink/5 px-3 py-1 text-xs font-semibold text-ink-soft">
      <MinusCircle className="h-3.5 w-3.5" /> Not attempted
    </span>
  );
}

function typeIcon(type: string) {
  if (type === "mcq") return <HelpCircle className="h-5 w-5" />;
  if (type === "conceptual") return <FileText className="h-5 w-5" />;
  return <Code className="h-5 w-5" />;
}

/* ── Answer cell (side-by-side matrix) ─────────────────────────────────── */
function AnswerCell({
  label,
  value,
  tone,
  mono,
  fallbackNote,
}: {
  label: string;
  value: string | null;
  tone: "learner" | "correct";
  mono: boolean;
  fallbackNote?: string | null;
}) {
  const empty = value == null || value.trim() === "";
  const toneClasses =
    tone === "correct" ? "border-emerald-200 bg-emerald-50/60" : "border-ink/10 bg-ink/[0.03]";
  const labelColor = tone === "correct" ? "text-emerald-700" : "text-ink-soft";
  return (
    <div className={`flex-1 rounded-2xl border p-4 ${toneClasses}`}>
      <div className={`mb-2 text-xs font-semibold uppercase tracking-wide ${labelColor}`}>
        {label}
      </div>
      {empty && fallbackNote ? (
        /* Issue 4: legacy debug rows without corrected code — show the bug
           explanation as the reference instead of "No reference answer". */
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-700">
            Bug explanation
          </p>
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">
            {fallbackNote}
          </p>
        </div>
      ) : empty ? (
        <p className="text-sm italic text-ink-soft">
          {tone === "learner" ? "No answer submitted." : "No reference answer available."}
        </p>
      ) : mono ? (
        <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-ink/90 p-3 font-mono text-xs leading-relaxed text-slate-100">
          {value}
        </pre>
      ) : (
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">{value}</p>
      )}
    </div>
  );
}

/* ── Summary matrix header ─────────────────────────────────────────────── */
function SummaryBar({
  summary,
}: {
  summary: { total: number; correct: number; incorrect: number; attempted: number; accuracy: number };
}) {
  const cells = [
    { label: "Exercises", value: summary.total, color: "text-ink" },
    { label: "Attempted", value: summary.attempted, color: "text-indigo-600" },
    { label: "Correct", value: summary.correct, color: "text-emerald-600" },
    { label: "Incorrect", value: summary.incorrect, color: "text-rose-600" },
    { label: "Accuracy", value: `${summary.accuracy}%`, color: "text-ink" },
  ];
  return (
    <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-5">
      {cells.map((c) => (
        <div
          key={c.label}
          className="rounded-2xl border border-ink/5 bg-white p-4 text-center shadow-sm"
        >
          <p className={`font-display text-2xl font-black ${c.color}`}>{c.value}</p>
          <p className="mt-1 text-xs font-medium uppercase tracking-wider text-ink-soft">
            {c.label}
          </p>
        </div>
      ))}
    </div>
  );
}

/* ── Page ──────────────────────────────────────────────────────────────── */
export default function ExerciseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const { data, error, isLoading } = useSWR<CurriculumDetail>(
    `/api/v1/curricula/${id}`,
    authFetcher
  );

  const rows = useMemo<ReviewRow[]>(() => {
    if (!data?.checkpoints) return [];
    return data.checkpoints
      .filter((cp) => cp.exercise)
      .sort((a, b) => a.ts - b.ts)
      .map((cp, i) => toReviewRow(cp, i));
  }, [data]);

  const summary = useMemo(() => {
    const total = rows.length;
    const correct = rows.filter((r) => r.status === "correct").length;
    const incorrect = rows.filter((r) => r.status === "incorrect").length;
    const attempted = correct + incorrect;
    const accuracy = attempted ? Math.round((correct / attempted) * 100) : 0;
    return { total, correct, incorrect, attempted, accuracy };
  }, [rows]);

  if (isLoading) {
    return (
      <AppLayout>
        <div className="flex h-[60vh] items-center justify-center">
          <LoadingSpinner size={32} />
        </div>
      </AppLayout>
    );
  }

  if (error || !data) {
    return (
      <AppLayout>
        <div className="mx-auto max-w-4xl pt-8">
          <div className="flex items-start gap-4 rounded-[2rem] border border-rose-200 bg-rose-50 px-6 py-5 text-rose-700">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-500" />
            <div>
              <p className="font-semibold text-rose-700">Failed to load exercises</p>
              <p className="mt-1 text-sm text-rose-600">
                {(error as Error)?.message || "Curriculum not found"}
              </p>
            </div>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-ink/10 bg-white text-ink-soft transition hover:bg-ink/5 hover:text-ink"
            aria-label="Go back"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-500">
              Exercise Review
            </p>
            <h1 className="font-display text-2xl font-bold text-ink">{data.title}</h1>
          </div>
        </div>

        {rows.length === 0 ? (
          <div className="rounded-[2rem] border border-ink/10 bg-white py-16 text-center shadow-sm">
            <p className="text-ink-soft">
              No exercises have been generated for this curriculum yet.
            </p>
          </div>
        ) : (
          <>
            <SummaryBar summary={summary} />

            <div className="grid gap-6">
              {rows.map((row) => (
                <div
                  key={row.checkpointId}
                  className="rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm"
                >
                  {/* Header row */}
                  <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                        {typeIcon(row.type)}
                      </div>
                      <div>
                        <h3 className="font-display font-bold text-ink">
                          {row.index + 1}. {TYPE_LABEL[row.type] || row.type} Exercise
                        </h3>
                        <p className="text-xs text-ink-soft">
                          From video timestamp: {Math.floor(row.ts)}s
                        </p>
                      </div>
                    </div>
                    <StatusPill status={row.status} />
                  </div>

                  {/* Prompt */}
                  <p className="mb-6 whitespace-pre-wrap text-base font-medium text-ink">
                    {row.question}
                  </p>

                  {/* MCQ: show all options with correct/chosen markers */}
                  {row.type === "mcq" && row.options ? (
                    <div className="space-y-3">
                      {row.options.map((opt, oIdx) => {
                        const isCorrect = opt === row.correctOption;
                        const isChosen = opt === row.learnerAnswer;
                        let cls = "border-ink/10 bg-white";
                        if (isCorrect) cls = "border-emerald-300 bg-emerald-50";
                        else if (isChosen) cls = "border-rose-300 bg-rose-50";
                        return (
                          <div
                            key={oIdx}
                            className={`flex items-center gap-3 rounded-xl border p-4 text-sm ${cls}`}
                          >
                            {isCorrect ? (
                              <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" />
                            ) : isChosen ? (
                              <XCircle className="h-5 w-5 shrink-0 text-rose-500" />
                            ) : (
                              <MinusCircle className="h-5 w-5 shrink-0 text-ink/20" />
                            )}
                            <span className="text-ink">{opt}</span>
                            {isCorrect && (
                              <span className="ml-auto text-xs font-semibold text-emerald-700">
                                Correct answer
                              </span>
                            )}
                            {isChosen && !isCorrect && (
                              <span className="ml-auto text-xs font-semibold text-rose-600">
                                Your answer
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    /* Coding / debug / conceptual: side-by-side answer matrix */
                    <div className="space-y-4">
                      <div className="flex flex-col gap-4 md:flex-row">
                        <AnswerCell
                          label="Your answer"
                          value={row.learnerAnswer}
                          tone="learner"
                          mono={isCode(row.type)}
                        />
                        <AnswerCell
                          label="Correct answer"
                          value={row.correctAnswer}
                          tone="correct"
                          mono={isCode(row.type)}
                          fallbackNote={row.fallbackNote}
                        />
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
