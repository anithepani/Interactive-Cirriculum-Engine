"use client";

import Link from "next/link";
import useSWR from "swr";
import LoadingSpinner from "@/components/LoadingSpinner";
import { authFetcher } from "@/lib/auth";
import type { CurriculumSummary } from "@/lib/types";

const POLL_INTERVAL = 5000;

// Stop polling once every row has reached a terminal state.
const refreshInterval = (latest?: CurriculumSummary[]) => {
  if (!latest || latest.length === 0) return 0;
  const pending = latest.some(
    (c) => c.status !== "ready" && c.status !== "failed"
  );
  return pending ? POLL_INTERVAL : 0;
};

const STATUS_BADGE: Record<string, string> = {
  ready: "bg-emerald-500/20 text-emerald-300",
  processing: "bg-amber-500/20 text-amber-300",
  queued: "bg-sky-500/20 text-sky-300",
  failed: "bg-rose-500/20 text-rose-300",
};

export default function DashboardPage() {
  const { data, error, isLoading } = useSWR<CurriculumSummary[]>(
    "/api/v1/curricula",
    authFetcher,
    { refreshInterval }
  );

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-white">Your curricula</h1>
          <p className="mt-2 text-sm text-slate-300">
            Curricula you have generated from video tutorials.
          </p>
        </div>
        <Link
          href="/upload"
          className="inline-flex items-center rounded-full bg-indigo-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400"
        >
          + New curriculum
        </Link>
      </div>

      <div className="mt-8">
        {isLoading ? (
          <div className="glass p-6">
            <LoadingSpinner />
          </div>
        ) : error ? (
          <div className="glass p-6 text-rose-300">
            Failed to load curricula: {(error as Error).message}
          </div>
        ) : !data || data.length === 0 ? (
          <div className="glass p-10 text-center">
            <p className="text-lg font-medium text-white">No curricula yet</p>
            <p className="mt-2 text-sm text-slate-300">
              Submit a YouTube URL to generate your first interactive curriculum.
            </p>
            <Link
              href="/upload"
              className="mt-5 inline-flex items-center rounded-full bg-indigo-500 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-400"
            >
              Get started
            </Link>
          </div>
        ) : (
          <ul className="space-y-3">
            {data.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/curriculum/${c.id}`}
                  className="glass flex items-center justify-between rounded-2xl p-5 transition hover:border-indigo-400/40 hover:bg-white/5"
                >
                  <div className="min-w-0">
                    <p className="truncate text-lg font-semibold text-white">
                      {c.title}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      {c.created_at
                        ? `Created ${new Date(c.created_at).toLocaleString()}`
                        : ""}
                      {c.ready_at
                        ? ` · Ready ${new Date(c.ready_at).toLocaleString()}`
                        : ""}
                    </p>
                  </div>
                  <span
                    className={`ml-4 shrink-0 rounded-full px-3 py-1 text-xs font-medium capitalize ${
                      STATUS_BADGE[c.status] ?? "bg-white/10 text-slate-300"
                    }`}
                  >
                    {c.status}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
