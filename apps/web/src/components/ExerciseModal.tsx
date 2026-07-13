"use client";

import React, { useEffect, useState, useRef } from "react";
import dynamic from "next/dynamic";
import { ExercisePayload } from "@/lib/types";

const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.default),
  { ssr: false }
);

interface ExerciseModalProps {
  isOpen: boolean;
  onClose: () => void;
  exercise: ExercisePayload;
  onSubmit?: (answer: string) => Promise<{ passed: boolean; message?: string }>;
  completedStatus?: "correct" | "incorrect" | null;
}

const AUTO_CLOSE_DELAY_MS = 1500;

export default function ExerciseModal({ isOpen, onClose, exercise, onSubmit, completedStatus }: ExerciseModalProps) {
  const [answer, setAnswer] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [result, setResult] = useState<{ passed: boolean; message?: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [execOutput, setExecOutput] = useState<string | null>(null);
  const autoCloseTimer = useRef<NodeJS.Timeout | null>(null);

  const alreadyAnswered = Boolean(completedStatus);
  // The learner may close the modal only once they've answered (submitted) OR
  // are re-opening an already-attempted checkpoint. Auto-paused checkpoints
  // cannot be dismissed without answering, forcing active recall.
  const canClose = submitted || alreadyAnswered;

  useEffect(() => {
    if (!isOpen) return;
    const starter = exercise.starter_code || exercise.starter;
    setAnswer(exercise.type === "coding" && starter ? starter : "");
    setSubmitted(alreadyAnswered);
    setResult(
      alreadyAnswered
        ? { passed: completedStatus === "correct", message: completedStatus === "correct" ? "Already answered correctly." : "Already attempted." }
        : null
    );
    setExecOutput(null);
    return () => {
      if (autoCloseTimer.current) {
        clearTimeout(autoCloseTimer.current);
        autoCloseTimer.current = null;
      }
    };
  }, [exercise, isOpen, completedStatus, alreadyAnswered]);

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

  const handleSubmit = async () => {
    if (!exercise) return;
    setLoading(true);
    setResult(null);
    setExecOutput(null);

    const isCoding = exercise.type === "coding";

    if (isCoding) {
      try {
        const response = await fetch("/api/v1/execute", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            code: answer,
            language: exercise.language || "python",
            stdin: "",
          }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          const message = data?.detail || data?.error || data?.message || `Server error: ${response.status}`;
          setResult({ passed: false, message });
        } else {
          const passed = Boolean(data?.passed);
          const output = data?.stdout ?? data?.stderr ?? "";
          setExecOutput(output ? String(output) : null);
          setResult({ passed, message: output ? String(output) : passed ? "Passed successfully" : "No output" });
        }
      } catch (error) {
        setResult({ passed: false, message: (error as Error).message || "Network or server error" });
      } finally {
        setSubmitted(true);
        setLoading(false);
      }
      return;
    }

    if (!onSubmit) {
      setLoading(false);
      return;
    }

    try {
      const res = await onSubmit(answer);
      setResult(res);
    } catch (error) {
      setResult({ passed: false, message: (error as Error).message || "Evaluation failed" });
    } finally {
      setSubmitted(true);
      setLoading(false);
    }
  };

  const renderQuestion = () => {
    if (!exercise) return null;
    const text = exercise.question || exercise.prompt;
    if (text) return <p className="text-white text-lg mb-4 whitespace-pre-wrap">{text}</p>;
    return null;
  };

  const renderAnswerArea = () => {
    if (exercise.options && exercise.options.length > 0) {
      const correctIdx =
        exercise.answer_idx ?? exercise.answer_index ?? -1;
      const correctOpt =
        correctIdx >= 0 && correctIdx < exercise.options.length
          ? exercise.options[correctIdx]
          : null;

      return (
        <div className="space-y-3">
          {exercise.options.map((opt, idx) => {
            const isCorrectOpt = opt === correctOpt;
            const isChosenOpt = answer === opt;
            // After submission, color-code each option.
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

    if (exercise.reference_answer) {
      return (
        <textarea
          className="w-full min-h-[180px] rounded-3xl border border-white/10 bg-slate-900/90 p-4 text-white outline-none placeholder:text-slate-500"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Type your answer here..."
          disabled={submitted}
        />
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
          options={{ minimap: { enabled: false }, fontSize: 14, wordWrap: "on", readOnly: submitted }}
        />
      </div>
    );
  };

  const showAutoCloseHint = submitted && result?.passed && !alreadyAnswered;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-2xl bg-gray-900 p-6 border border-white/10 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-white">Exercise</h2>
          {canClose && (
            <button onClick={onClose} className="text-gray-400 hover:text-white" aria-label="Close">✕</button>
          )}
        </div>

        {renderQuestion()}
        {renderAnswerArea()}

        {submitted && result && (
          <div className={`mt-4 p-3 rounded-lg ${result.passed ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'}`}>
            <div className="font-medium mb-2">
              {result.passed ? '✅ Correct!' : `❌ ${result.message || 'Incorrect, try again.'}`}
            </div>
            {execOutput !== null && (
              <pre className="bg-gray-800 text-sm p-3 rounded-md overflow-auto mt-2 text-white">{execOutput}</pre>
            )}
            {showAutoCloseHint && (
              <div className="text-xs text-green-300/80 mt-1">Closing automatically…</div>
            )}
          </div>
        )}

        <div className="flex justify-end gap-3 mt-4">
          {canClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-white transition"
            >
              Close
            </button>
          )}
          {!submitted && (
            <button
              onClick={handleSubmit}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition disabled:opacity-50"
              disabled={!answer || loading}
            >
              {loading ? 'Submitting...' : 'Submit'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
