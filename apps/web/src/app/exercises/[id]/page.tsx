"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { ArrowLeft, CheckCircle2, Circle, AlertTriangle, Code, HelpCircle } from "lucide-react";
import Link from "next/link";
import AppLayout from "@/components/layout/AppLayout";
import LoadingSpinner from "@/components/LoadingSpinner";
import { authFetcher } from "@/lib/auth";

export default function ExerciseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const { data, error, isLoading } = useSWR(`/api/v1/curricula/${id}`, authFetcher);

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
              <p className="mt-1 text-sm text-rose-600">{(error as Error)?.message || "Curriculum not found"}</p>
            </div>
          </div>
        </div>
      </AppLayout>
    );
  }

  // Extract all valid exercises from checkpoints
  const exercises = data.checkpoints
    ?.filter((cp: any) => cp.exercise)
    .map((cp: any) => ({
      ...cp.exercise,
      type: cp.exercise_type,
      ts: cp.ts,
      checkpointId: cp.id,
    })) || [];

  return (
    <AppLayout>
      <div className="mx-auto max-w-5xl">
        <div className="mb-8 flex items-center gap-4">
          <button
            onClick={() => router.back()}
            className="flex h-10 w-10 items-center justify-center rounded-full border border-ink/10 bg-white text-ink-soft transition hover:bg-ink/5 hover:text-ink"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-indigo-500">
              Exercises
            </p>
            <h1 className="font-display text-2xl font-bold text-ink">
              {data.title}
            </h1>
          </div>
        </div>

        {exercises.length === 0 ? (
          <div className="rounded-[2rem] border border-ink/10 bg-white py-16 text-center shadow-sm">
            <p className="text-ink-soft">No exercises have been generated for this curriculum yet.</p>
          </div>
        ) : (
          <div className="grid gap-6">
            {exercises.map((ex: any, idx: number) => (
              <div key={ex.id || idx} className="rounded-[2rem] border border-ink/10 bg-white p-8 shadow-sm">
                <div className="mb-6 flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
                    {ex.type === "mcq" ? <HelpCircle className="h-5 w-5" /> : <Code className="h-5 w-5" />}
                  </div>
                  <div>
                    <h3 className="font-display font-bold text-ink capitalize">{ex.type} Challenge</h3>
                    <p className="text-xs text-ink-soft">From video timestamp: {Math.floor(ex.ts)}s</p>
                  </div>
                </div>

                <div className="prose prose-sm max-w-none text-ink">
                  <p className="text-base font-medium">{ex.prompt}</p>
                </div>

                {ex.type === "mcq" && ex.options && (
                  <div className="mt-6 space-y-3">
                    {ex.options.map((opt: string, oIdx: number) => (
                      <div key={oIdx} className="flex items-center gap-3 rounded-xl border border-ink/10 p-4 transition hover:bg-indigo-50/50">
                        <Circle className="h-5 w-5 text-ink/20" />
                        <span className="text-sm">{opt}</span>
                      </div>
                    ))}
                  </div>
                )}

                {(ex.type === "coding" || ex.type === "debug") && ex.context && (
                  <div className="mt-6 rounded-xl bg-ink/5 p-4 font-mono text-sm text-ink/80">
                    <pre className="whitespace-pre-wrap">{ex.context}</pre>
                  </div>
                )}
                
                <div className="mt-8 flex justify-end">
                   <button className="rounded-full bg-indigo-50 px-6 py-2.5 text-sm font-semibold text-indigo-600 transition hover:bg-indigo-100">
                     Review Answer
                   </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
