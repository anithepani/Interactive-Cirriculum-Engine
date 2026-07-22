"use client";

import React, { useEffect, useState, useRef } from "react";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
import { ExercisePayload } from "@/lib/types";

function CelebrationBurst({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-50 flex items-center justify-center">
      {Array.from({ length: 30 }).map((_, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 1, scale: 0, x: 0, y: 0 }}
          animate={{
            opacity: 0,
            scale: [0, 1.5, 0],
            x: (Math.random() - 0.5) * 400,
            y: (Math.random() - 0.5) * 400,
          }}
          transition={{ duration: 1.5, ease: "easeOut", delay: Math.random() * 0.2 }}
          className={`absolute w-3 h-3 rounded-full ${['bg-indigo-500', 'bg-fuchsia-500', 'bg-emerald-500', 'bg-amber-500'][i % 4]}`}
        />
      ))}
    </div>
  );
}

const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.default),
  { ssr: false }
);

const DiffEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.DiffEditor),
  { ssr: false }
);

export interface RunResult {
  passed?: boolean;
  message?: string;
  stdout?: string;
  stderr?: string;
}

export interface SubmitResult {
  passed: boolean;
  message?: string;
  stdout?: string;
  stderr?: string;
}

interface ExerciseModalProps {
  isOpen: boolean;
  onClose: () => void;
  exercise: ExercisePayload;
  onSubmit?: (answer: string) => Promise<SubmitResult>;
  /** Trial run against /execute (no hidden tests, no skill-model update). */
  onRun?: (answer: string) => Promise<RunResult>;
  completedStatus?: "correct" | "incorrect" | null;
  /** The learner's previously submitted answer (session-scoped), for review. */
  submittedAnswer?: string | null;
}

const AUTO_CLOSE_DELAY_MS = 1500;

interface OutputState {
  stdout: string;
  stderr: string;
  note?: string;
  /** Exit status of the run: true = exit 0, false = runtime error, undefined = n/a. */
  ok?: boolean;
}

export default function ExerciseModal({
  isOpen,
  onClose,
  exercise,
  onSubmit,
  onRun,
  completedStatus,
  submittedAnswer,
}: ExerciseModalProps) {
  const [answer, setAnswer] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [result, setResult] = useState<{ passed: boolean; message?: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [output, setOutput] = useState<OutputState | null>(null);
  const autoCloseTimer = useRef<NodeJS.Timeout | null>(null);
  // Identity of the exercise the editor was last seeded for. Seeding runs ONCE
  // per open (per exercise identity). This prevents a mid-submit reseed: on
  // Submit the parent flips `submittedAnswer` (and re-fetches via mutate),
  // which previously re-fired the seed effect and clobbered the learner's code
  // back to the starter/buggy template — the "resets to default" race (Fix 3).
  const seededKeyRef = useRef<string | null>(null);

  const exType = exercise.type || "";
  const isCodeType = exType === "coding" || exType === "debug";
  const isMcq = Boolean(exercise.options && exercise.options.length > 0);
  const isConceptual = !isCodeType && !isMcq && Boolean(exercise.reference_answer);

  const alreadyAnswered = Boolean(completedStatus);
  // Review mode: re-opening a checkpoint the learner already submitted. The
  // editor is locked, pre-filled with their prior answer, and Run/Submit are
  // hidden — only Close is available.
  const reviewMode = alreadyAnswered;
  // The learner may close the modal only once they've answered (submitted) OR
  // are re-opening an already-attempted checkpoint. Auto-paused checkpoints
  // cannot be dismissed without answering, forcing active recall.
  const canClose = submitted || alreadyAnswered;
  // Editor is read-only after submitting or when reviewing a past attempt.
  const editorReadOnly = submitted || reviewMode;

  // Seed the editor EXACTLY ONCE per open (per exercise identity). Critically,
  // this must NOT re-run when `submittedAnswer` flips on Submit (the parent
  // stores the answer in a session map, which would otherwise re-fire this
  // effect and clobber the learner's code back to the starter/buggy template —
  // the "Submit resets to default" race). We therefore key on a stable
  // identity (type + prompt) and guard with a ref, and deliberately exclude
  // `submittedAnswer` from the reseed trigger.
  const openKey = isOpen ? `${exType}::${exercise.prompt ?? exercise.question ?? ""}` : null;
  useEffect(() => {
    if (!isOpen || openKey == null) return;
    if (seededKeyRef.current === openKey) return; // already seeded this open
    seededKeyRef.current = openKey;

    // Seed order:
    //  - review mode  -> the learner's previously submitted answer
    //  - coding       -> starter code
    //  - debug        -> the buggy snippet they must fix
    //  - otherwise    -> empty
    let seed = "";
    if (reviewMode && submittedAnswer != null) {
      seed = submittedAnswer;
    } else if (exType === "coding") {
      seed = exercise.starter_code || exercise.starter || "";
    } else if (exType === "debug") {
      seed = exercise.buggy_code || "";
    }
    setAnswer(seed);

    setSubmitted(alreadyAnswered);
    setResult(
      alreadyAnswered
        ? {
            passed: completedStatus === "correct",
            message:
              completedStatus === "correct"
                ? "Already answered correctly."
                : "Already attempted — review the correct answer below.",
          }
        : null
    );
    setOutput(null);
    setRunning(false);
    setLoading(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openKey]);

  // Reset the seed guard when the modal closes so the next open re-seeds.
  useEffect(() => {
    if (!isOpen) {
      seededKeyRef.current = null;
    }
    return () => {
      if (autoCloseTimer.current) {
        clearTimeout(autoCloseTimer.current);
        autoCloseTimer.current = null;
      }
    };
  }, [isOpen]);

  // Auto-close 1-2s after a CORRECT submission so the learner sees the
  // confirmation but isn't forced to click. Wrong answers never auto-close.
  useEffect(() => {
    if (submitted && result?.passed && !alreadyAnswered) {
      autoCloseTimer.current = setTimeout(() => {
        onClose();
      }, AUTO_CLOSE_DELAY_MS);
      return () => {
        if (autoCloseTimer.current) {
          clearTimeout(autoCloseTimer.current);
          autoCloseTimer.current = null;
        }
      };
    }
    return undefined;
  }, [submitted, result, alreadyAnswered, onClose]);

  if (!isOpen) return null;

  const applyOutput = (r: RunResult | SubmitResult, fallbackNote?: string, ok?: boolean) => {
    const stdout = r.stdout ? String(r.stdout) : "";
    const stderr = r.stderr ? String(r.stderr) : "";
    if (stdout || stderr) {
      setOutput({ stdout, stderr, note: fallbackNote, ok });
    } else if (fallbackNote) {
      setOutput({ stdout: "", stderr: "", note: fallbackNote, ok });
    } else {
      setOutput(null);
    }
  };

  // "Run": trial execution via /execute. No hidden tests, no skill-model
  // update, does not mark the checkpoint or lock the editor. For coding, the
  // exercise's VISIBLE tests are appended so their assertions execute and
  // stream real stdout/stderr feedback (hidden tests stay hidden until Submit).
  // Always renders stdout/stderr (incl. tracebacks) verbatim; only when BOTH
  // are empty do we show a clear, exit-code-aware note.
  const buildRunSnippet = (code: string): string => {
    const visible =
      exType === "coding" ? (exercise.tests_visible || []).filter((t) => t && t.trim()) : [];
    if (visible.length === 0) return code;
    return `${code.replace(/\s+$/, "")}\n\n# --- visible tests ---\n${visible.join("\n")}\n`;
  };

  const handleRun = async () => {
    if (!onRun || !answer) return;
    setRunning(true);
    setOutput(null);
    try {
      const r = await onRun(buildRunSnippet(answer));
      const hasOutput = Boolean(r.stdout || r.stderr);
      const note = hasOutput
        ? undefined
        : r.passed
        ? "Code executed successfully (no output)."
        : "Code exited with an error but produced no output.";
      applyOutput(r, note, Boolean(r.passed));
    } catch (error) {
      setOutput({
        stdout: "",
        stderr: (error as Error).message || "Run failed.",
        note: undefined,
        ok: false,
      });
    } finally {
      setRunning(false);
    }
  };

  // "Submit": final evaluation via /evaluate (hidden tests + skill model).
  const handleSubmit = async () => {
    if (!exercise || !onSubmit) return;
    setLoading(true);
    setResult(null);
    setOutput(null);

    try {
      const res = await onSubmit(answer);
      setResult({ passed: res.passed, message: res.message });
      applyOutput(res);
    } catch (error) {
      setResult({ passed: false, message: (error as Error).message || "Evaluation failed" });
    } finally {
      setSubmitted(true);
      setLoading(false);
    }
  };

  // "Incorrect review" is active both when re-opening a previously-failed
  // checkpoint (reviewMode) AND immediately after a fresh failing submit — so
  // the explanation drawer / diff appears right away (Fix 4) instead of only on
  // re-open. The learner's code is the frozen `answer` (or the persisted prior
  // answer when re-opening).
  const incorrectReview =
    (reviewMode && completedStatus === "incorrect") ||
    Boolean(submitted && result && !result.passed);
  const learnerCode = submittedAnswer != null ? submittedAnswer : answer;

  const renderQuestion = () => {
    if (!exercise) return null;
    const text = exercise.question || exercise.prompt;
    if (text) return <p className="text-white text-lg mb-4 whitespace-pre-wrap">{text}</p>;
    return null;
  };

  // The supporting code snippet extracted from the lesson (M3 OCR -> exercise
  // `context`). Shown read-only ONLY when present AND genuinely relevant.
  // Issue 3 (defence-in-depth): the backend now scopes context to the segment,
  // hardens OCR, and gates relevance — but legacy rows may still carry garbage
  // OCR (IDE chrome / terminal output / cross-segment code) or duplicate the
  // editor's own code. This guard hides the snippet unless it (a) is the right
  // exercise kind, (b) looks like real code, (c) is free of OCR corruption,
  // (d) doesn't duplicate the editor seed, and — for coding/mcq/conceptual —
  // (e) the prompt actually references a code block.
  const isLikelyIdeMetadata = (code: string): boolean => {
    const markers = [
      "main.py", "builtins", "structure", "run:", "process finished",
      "exit code", "__pycache__", "site-packages", "external libraries",
      "explorer", "navigate", "refactor", "in[", "out[", "library number",
      "winequality", "traceback",
    ];
    const lines = code.split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length === 0) return true;
    const low = code.toLowerCase();
    const hits = markers.filter((m) => low.includes(m)).length;
    // Two or more distinct IDE markers => almost certainly an editor screenshot.
    return hits >= 2;
  };

  // OCR corruption: real source never contains CJK or full-width punctuation.
  const hasOcrCorruption = (code: string): boolean =>
    /[\u3000-\u9fff\uac00-\ud7a3（）“”‘’＝，；：《》【】、。]/.test(code);

  // At least one genuine code signal must be present.
  const looksLikeCode = (code: string): boolean =>
    /\b(def|class|import|function|const|let|return|print|console)\b|[=;{}()]/.test(
      code
    );

  // Does the prompt explicitly point the learner at a provided snippet?
  const promptReferencesCode = (): boolean => {
    const p = (exercise.prompt || exercise.question || "").toLowerCase();
    if (!p) return false;
    return (
      /```/.test(exercise.prompt || "") ||
      /(following|below|above|shown)\s+code|code\s+(below|above|shown)|this\s+function|the\s+function\s+(below|above)|snippet|given\s+code|this\s+code|consider\s+the/.test(
        p
      )
    );
  };

  const contextIsRelevant = (code: string): boolean => {
    const trimmed = code.trim();
    if (trimmed.length < 20) return false;
    if (hasOcrCorruption(trimmed)) return false;
    if (isLikelyIdeMetadata(trimmed)) return false;
    if (!looksLikeCode(trimmed)) return false;
    // Don't repeat the code already shown in the editor (debug buggy / coding starter).
    const editorSeed = (exercise.buggy_code || exercise.starter_code || exercise.starter || "").trim();
    if (editorSeed && trimmed.slice(0, 40) === editorSeed.slice(0, 40)) return false;
    // debug: the learner analyses provided code, so a snippet is inherently
    // relevant. coding/mcq/conceptual: only when the prompt references code
    // (a from-scratch `greet` coding task must NOT show a snippet).
    if (exType === "debug") return true;
    return promptReferencesCode();
  };

  const renderContext = () => {
    const code = exercise.context;
    if (!code || !code.trim() || !contextIsRelevant(code)) return null;
    return (
      <div className="mb-4">
        <div className="text-xs font-semibold uppercase tracking-wide mb-1 text-slate-400">Code snippet</div>
        <pre className="max-h-56 overflow-auto rounded-lg bg-black/80 border border-white/10 p-3 font-mono text-xs text-slate-200 whitespace-pre-wrap">{code}</pre>
      </div>
    );
  };

  const renderAnswerArea = () => {
    if (isMcq) {
      const correctIdx = exercise.answer_idx ?? exercise.answer_index ?? -1;
      const correctOpt =
        correctIdx >= 0 && correctIdx < (exercise.options as string[]).length
          ? (exercise.options as string[])[correctIdx]
          : null;

      return (
        <div className="space-y-3">
          {(exercise.options as string[]).map((opt, idx) => {
            const isCorrectOpt = opt === correctOpt;
            const isChosenOpt = answer === opt;
            let stateClasses = "border-white/10 bg-slate-900/80 hover:border-indigo-500/40";
            if (submitted) {
              if (isCorrectOpt) {
                stateClasses = "border-green-500 bg-green-500/15 text-green-200";
              } else if (isChosenOpt) {
                stateClasses = "border-red-500 bg-red-500/15 text-red-200";
              } else {
                stateClasses = "border-white/10 bg-slate-900/80 opacity-60";
              }
            }
            return (
              <label
                key={idx}
                className={`flex cursor-pointer items-center gap-3 rounded-2xl border px-4 py-3 text-slate-200 transition ${stateClasses} ${submitted ? "cursor-default" : ""}`}
              >
                <input
                  type="radio"
                  name="mcq"
                  value={opt}
                  checked={answer === opt}
                  onChange={() => setAnswer(opt)}
                  disabled={submitted}
                  className="h-4 w-4 accent-indigo-500"
                />
                <span>{opt}</span>
                {submitted && isCorrectOpt && (
                  <span className="ml-auto text-green-300 text-sm font-semibold">Correct</span>
                )}
                {submitted && isChosenOpt && !isCorrectOpt && (
                  <span className="ml-auto text-red-300 text-sm font-semibold">Your answer</span>
                )}
              </label>
            );
          })}
        </div>
      );
    }

    if (isConceptual) {
      return (
        <textarea
          className="w-full min-h-[180px] rounded-3xl border border-white/10 bg-slate-900/90 p-4 text-white outline-none placeholder:text-slate-500 disabled:opacity-70"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Type your answer here..."
          disabled={editorReadOnly}
        />
      );
    }

    // Code editor (coding + debug).
    // Incorrect (fresh fail or re-open review) + a reference/corrected solution
    // available -> show a side-by-side diff (learner's answer vs the correct
    // solution) with Monaco's native red/green line highlighting. Issue 4:
    // debug now carries fixed_code (mirrored into reference_solution), so the
    // diff works for debug too; legacy debug rows without it fall through to the
    // plain read-only editor + bug_explanation hint below.
    const referenceCode = exercise.reference_solution || exercise.fixed_code || "";
    const showDiff =
      incorrectReview &&
      (exType === "coding" || exType === "debug") &&
      Boolean(referenceCode) &&
      Boolean(learnerCode);

    if (showDiff) {
      return (
        <div>
          <div className="mb-1 flex items-center justify-between text-xs font-semibold uppercase tracking-wide">
            <span className="text-red-300">Your submission</span>
            <span className="text-green-300">Reference solution</span>
          </div>
          <div className="h-[320px] rounded-3xl border border-white/10 bg-slate-900/90 overflow-hidden">
            <DiffEditor
              height="100%"
              language={exercise.language || "python"}
              theme="vs-dark"
              original={learnerCode || ""}
              modified={referenceCode}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                wordWrap: "on",
                readOnly: true,
                renderSideBySide: true,
                renderOverviewRuler: false,
              }}
            />
          </div>
        </div>
      );
    }

    return (
      <div className="h-[320px] rounded-3xl border border-white/10 bg-slate-900/90 overflow-hidden">
        <MonacoEditor
          height="100%"
          defaultLanguage={exercise.language || "python"}
          theme="vs-dark"
          value={answer}
          onChange={(value) => setAnswer(value || "")}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            wordWrap: "on",
            readOnly: editorReadOnly,
          }}
        />
      </div>
    );
  };

  // Hint / explanation surfaced when the learner got it wrong — on a fresh
  // failed submission OR when re-opening an incorrectly-answered checkpoint.
  const renderReviewHint = () => {
    if (!incorrectReview) return null;
    const hint =
      exType === "debug"
        ? exercise.bug_explanation
        : isConceptual
        ? exercise.reference_answer
        : undefined;
    if (!hint) return null;
    const label = exType === "debug" ? "Bug explanation" : "Reference answer";
    return (
      <div className="mt-4 p-3 rounded-lg bg-amber-500/15 text-amber-200 border border-amber-500/30">
        <div className="text-xs font-semibold uppercase tracking-wide mb-1 text-amber-300">{label}</div>
        <div className="text-sm whitespace-pre-wrap">{hint}</div>
      </div>
    );
  };

  const renderOutputWindow = () => {
    if (!output) return null;
    // Exit-status line: only meaningful when we know the exit code (Run).
    const statusLabel =
      output.ok === undefined
        ? null
        : output.ok
        ? "Exit 0 · success"
        : "Runtime error";
    return (
      <div className="mt-4">
        <div className="flex items-center justify-between mb-1">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Output</div>
          {statusLabel && (
            <div
              className={`text-xs font-semibold uppercase tracking-wide ${
                output.ok ? "text-green-400" : "text-red-400"
              }`}
            >
              {statusLabel}
            </div>
          )}
        </div>
        <div className="max-h-48 overflow-auto rounded-lg bg-black/80 border border-white/10 p-3 font-mono text-xs">
          {output.stdout && (
            <pre className="whitespace-pre-wrap text-slate-200">{output.stdout}</pre>
          )}
          {output.stderr && (
            <pre className="whitespace-pre-wrap text-red-400">{output.stderr}</pre>
          )}
          {!output.stdout && !output.stderr && output.note && (
            <pre className="whitespace-pre-wrap text-slate-400">{output.note}</pre>
          )}
        </div>
      </div>
    );
  };

  const showAutoCloseHint = submitted && result?.passed && !alreadyAnswered;
  // Run/Submit are hidden entirely in review mode.
  const showActions = !reviewMode && !submitted;
  const showRun = showActions && isCodeType && Boolean(onRun);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-2xl bg-gray-900 p-6 border border-white/10 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-white">
            {reviewMode ? "Exercise Review" : "Exercise"}
          </h2>
          {canClose && (
            <button onClick={onClose} className="text-gray-400 hover:text-white" aria-label="Close">✕</button>
          )}
        </div>

        {renderQuestion()}
        {renderContext()}
        {renderAnswerArea()}
        {renderOutputWindow()}

        {submitted && result && (
          <div className={`mt-4 p-3 rounded-lg ${result.passed ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'}`}>
            <div className="font-medium">
              {result.passed ? '✅ Correct!' : `❌ ${result.message || 'Incorrect, try again.'}`}
            </div>
            {showAutoCloseHint && (
              <div className="text-xs text-green-300/80 mt-1">Closing automatically…</div>
            )}
          </div>
        )}

        {renderReviewHint()}

        <div className="flex justify-end gap-3 mt-4">
          {canClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-white transition"
            >
              Close
            </button>
          )}
          {showRun && (
            <button
              onClick={handleRun}
              className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-white transition disabled:opacity-50"
              disabled={!answer || running || loading}
            >
              {running ? 'Running...' : 'Run'}
            </button>
          )}
          {showActions && (
            <button
              onClick={handleSubmit}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition disabled:opacity-50"
              disabled={!answer || loading || running}
            >
              {loading ? 'Submitting...' : 'Submit'}
            </button>
          )}
        </div>
      </div>
      <CelebrationBurst active={submitted && result?.passed === true && !alreadyAnswered} />
    </div>
  );
}
