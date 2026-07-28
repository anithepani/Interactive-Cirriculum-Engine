"use client";

import { useState } from "react";
import useSWR from "swr";
import { motion, AnimatePresence } from "framer-motion";
import AppLayout from "@/components/layout/AppLayout";
import LoadingSpinner from "@/components/LoadingSpinner";
import { authFetcher } from "@/lib/auth";
import { BrainCircuit, Check, X, ArrowRight, Trophy } from "lucide-react";
import Link from "next/link";
import { ExercisePayload } from "@/lib/types";

interface QuizQuestion {
  id: number;
  concept_label: string;
  type: string;
  payload: ExercisePayload;
}

export default function QuizPage() {
  const { data: questions, error, isLoading } = useSWR<QuizQuestion[]>("/api/v1/review/quiz", authFetcher);
  
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [score, setScore] = useState(0);

  const currentQuestion = questions?.[currentIndex];

  const handleSubmit = () => {
    if (!selectedOption || !currentQuestion) return;
    setIsSubmitted(true);
    if (selectedOption === currentQuestion.payload.reference_answer) {
      setScore(prev => prev + 1);
    }
  };

  const handleNext = () => {
    setSelectedOption(null);
    setIsSubmitted(false);
    setCurrentIndex(prev => prev + 1);
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-4xl py-8 px-6">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="font-display text-3xl font-bold text-ink flex items-center gap-2">
              <BrainCircuit className="w-8 h-8 text-indigo-600" />
              Random Concept Quiz
            </h1>
            <p className="mt-2 text-ink-soft">
              Test your knowledge across random concepts.
            </p>
          </div>
        </div>

        {isLoading ? (
          <div className="flex h-[400px] items-center justify-center">
            <LoadingSpinner size={40} />
          </div>
        ) : error ? (
          <div className="rounded-[2rem] border border-rose-200 bg-rose-50 p-6 text-rose-700 text-center font-medium">
            Failed to load quiz.
          </div>
        ) : !questions || questions.length === 0 ? (
           <div className="flex flex-col items-center justify-center h-[400px] border border-ink/10 bg-white dark:bg-zinc-900 rounded-[2rem] shadow-sm p-12 text-center">
             <h2 className="text-2xl font-display font-bold text-ink mb-2">No Quizzes Available</h2>
             <p className="text-ink-soft max-w-md mx-auto mb-8">
               You don't have any multiple choice exercises in your curricula yet.
             </p>
             <Link href="/dashboard" className="px-6 py-3 bg-ink text-white font-semibold rounded-xl hover:bg-ink-soft transition-colors">
               Return to Dashboard
             </Link>
           </div>
        ) : currentIndex >= questions.length ? (
          <div className="flex flex-col items-center justify-center h-[400px] border border-ink/10 bg-white dark:bg-zinc-900 rounded-[2rem] shadow-sm p-12 text-center relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 to-purple-600/10" />
            <div className="w-24 h-24 bg-indigo-100 rounded-full flex items-center justify-center mb-6 relative z-10 shadow-lg shadow-indigo-200/50">
              <Trophy className="w-12 h-12 text-indigo-600" />
            </div>
            <h2 className="text-3xl font-display font-bold text-ink mb-3 relative z-10">Quiz Complete!</h2>
            <p className="text-xl text-ink-soft mb-8 relative z-10">
              You scored <span className="font-bold text-indigo-600">{score}</span> out of {questions.length}
            </p>
            <Link href="/dashboard" className="relative z-10 px-8 py-3 bg-indigo-600 text-white font-semibold rounded-full hover:bg-indigo-700 transition-colors shadow-md hover:shadow-xl active:scale-95">
              Back to Dashboard
            </Link>
          </div>
        ) : currentQuestion ? (
          <div className="max-w-2xl mx-auto flex flex-col">
            <div className="w-full mb-6 flex items-center justify-between text-sm font-medium text-ink-soft">
              <span>Question {currentIndex + 1} of {questions.length}</span>
              <span className="px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full font-bold">
                {currentQuestion.concept_label}
              </span>
            </div>

            <div className="w-full rounded-[2rem] border border-ink/10 bg-white dark:bg-zinc-900 shadow-xl flex flex-col p-8 sm:p-10">
              <h3 className="text-2xl font-display font-bold text-ink mb-8 leading-snug">
                {currentQuestion.payload.question}
              </h3>
              
              <div className="flex flex-col gap-4 mb-8">
                {currentQuestion.payload.options?.map((opt, i) => {
                  const isSelected = selectedOption === opt;
                  const isCorrect = isSubmitted && opt === currentQuestion.payload.reference_answer;
                  const isWrong = isSubmitted && isSelected && opt !== currentQuestion.payload.reference_answer;
                  
                  let borderClass = "border-ink/10";
                  let bgClass = "hover:border-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20";
                  
                  if (isSelected && !isSubmitted) {
                    borderClass = "border-indigo-500 ring-2 ring-indigo-500/20";
                    bgClass = "bg-indigo-50 dark:bg-indigo-900/20";
                  } else if (isCorrect) {
                    borderClass = "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20";
                    bgClass = "";
                  } else if (isWrong) {
                    borderClass = "border-rose-500 bg-rose-50 dark:bg-rose-900/20";
                    bgClass = "";
                  }

                  return (
                    <button
                      key={i}
                      onClick={() => !isSubmitted && setSelectedOption(opt)}
                      disabled={isSubmitted}
                      className={`relative text-left p-5 rounded-2xl border-2 transition-all font-medium text-ink ${borderClass} ${bgClass}`}
                    >
                      {opt}
                      {isCorrect && (
                        <Check className="absolute right-5 top-1/2 -translate-y-1/2 w-6 h-6 text-emerald-500" />
                      )}
                      {isWrong && (
                        <X className="absolute right-5 top-1/2 -translate-y-1/2 w-6 h-6 text-rose-500" />
                      )}
                    </button>
                  );
                })}
              </div>

              <div className="flex justify-end pt-6 border-t border-ink/10">
                {!isSubmitted ? (
                  <button
                    onClick={handleSubmit}
                    disabled={!selectedOption}
                    className="px-8 py-3 bg-indigo-600 text-white font-bold rounded-full disabled:opacity-50 hover:bg-indigo-700 transition shadow-md active:scale-95 flex items-center gap-2"
                  >
                    Check Answer
                  </button>
                ) : (
                  <button
                    onClick={handleNext}
                    className="px-8 py-3 bg-ink text-white font-bold rounded-full hover:bg-ink-soft transition shadow-md active:scale-95 flex items-center gap-2"
                  >
                    Next Question <ArrowRight className="w-5 h-5" />
                  </button>
                )}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </AppLayout>
  );
}
