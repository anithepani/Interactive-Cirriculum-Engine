"use client";

import React, { useState } from "react";
import dynamic from "next/dynamic";
import { ExercisePayload } from "@/lib/types";

const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.default),
  { ssr: false }
);

interface ExerciseModalProps {
  isOpen: boolean;
  onClose: () => void;
  exercise: ExercisePayload;   // <-- now expecting the payload directly
  onSubmit?: (answer: string) => Promise<{ passed: boolean }>;
}

export default function ExerciseModal({ isOpen, onClose, exercise, onSubmit }: ExerciseModalProps) {
  const [answer, setAnswer] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [result, setResult] = useState<{ passed: boolean; message?: string } | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (!onSubmit) return;
    try {
      const res = await onSubmit(answer);
      setResult(res);
      setSubmitted(true);
    } catch (e) {
      setResult({ passed: false, message: (e as Error).message });
    }
  };

  const renderQuestion = () => {
    if (!exercise) return null;
    if (exercise.question) return <p className="text-white text-lg mb-4">{exercise.question}</p>;
    return null;
  };

  const renderAnswerArea = () => {
    // MCQ
    if (exercise.options && exercise.options.length > 0) {
      return (
        <div className="space-y-2">
          {exercise.options.map((opt, idx) => (
            <label key={idx} className="flex items-center gap-3 text-gray-200">
              <input
                type="radio"
                name="mcq"
                value={opt}
                onChange={() => setAnswer(opt)}
                disabled={submitted}
                className="accent-indigo-500"
              />
              {opt}
            </label>
          ))}
        </div>
      );
    }
    // Conceptual – text area
    if (exercise.reference_answer) {
      return (
        <textarea
          className="w-full h-32 bg-gray-800 border border-white/10 rounded-lg p-3 text-white"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Type your answer here..."
          disabled={submitted}
        />
      );
    }
    // Coding – Monaco editor
    return (
      <div className="h-64 border border-white/10 rounded-lg overflow-hidden">
        <MonacoEditor
          height="100%"
          defaultLanguage="python"
          theme="vs-dark"
          value={answer}
          onChange={(value) => setAnswer(value || "")}
          options={{ minimap: { enabled: false }, fontSize: 14 }}
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
            {result.passed ? '✅ Correct!' : `❌ ${result.message || 'Incorrect, try again.'}`}
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
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white transition"
              disabled={!answer}
            >
              Submit
            </button>
          )}
        </div>
      </div>
    </div>
  );
}