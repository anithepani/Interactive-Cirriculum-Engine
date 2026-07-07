"use client";

import React, { useEffect, useState } from "react";
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
}

export default function ExerciseModal({ isOpen, onClose, exercise, onSubmit }: ExerciseModalProps) {
  const [answer, setAnswer] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [result, setResult] = useState<{ passed: boolean; message?: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [execOutput, setExecOutput] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setAnswer(exercise.type === "coding" && exercise.starter_code ? exercise.starter_code : "");
    setSubmitted(false);
    setResult(null);
    setExecOutput(null);
  }, [exercise, isOpen]);

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
      const result = await onSubmit(answer);
      setResult(result);
    } catch (error) {
      setResult({ passed: false, message: (error as Error).message || "Evaluation failed" });
    } finally {
      setSubmitted(true);
      setLoading(false);
    }
  };

  const renderQuestion = () => {
    if (!exercise) return null;
    if (exercise.question) return <p className="text-white text-lg mb-4">{exercise.question}</p>;
    return null;
  };

  const renderAnswerArea = () => {
    if (exercise.options && exercise.options.length > 0) {
      return (
        <div className="space-y-3">
          {exercise.options.map((opt, idx) => (
            <label
              key={idx}
              className="flex cursor-pointer items-center gap-3 rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-slate-200 transition hover:border-indigo-500/40"
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
            </label>
          ))}
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
          options={{ minimap: { enabled: false }, fontSize: 14, wordWrap: "on" }}
        />
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-2xl rounded-2xl bg-gray-900 p-6 border border-white/10 shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-white">Exercise</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
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
          </div>
        )}

        <div className="flex justify-end gap-3 mt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-white transition"
          >
            {submitted ? 'Close' : 'Skip'}
          </button>
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