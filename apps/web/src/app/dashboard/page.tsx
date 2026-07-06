"use client";

import Link from "next/link";
import useSWR from "swr";
import { CurriculumSummary } from "@/lib/types";

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function DashboardPage() {
  const { data, error, isLoading } = useSWR<CurriculumSummary[]>("/api/v1/curricula", fetcher, {
    refreshInterval: 10000,
  });

  if (error) return (
    <div className="text-red-400 p-6">Failed to load curricula. Please try again later.</div>
  );

  if (isLoading) return (
    <div className="text-gray-400 p-6">⏳ Loading curricula...</div>
  );

  // Ensure data is an array; if not, treat as empty
  const curricula = Array.isArray(data) ? data : [];

  return (
    <main className="mx-auto max-w-6xl p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-white">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-400">Overview of generated curricula and progress.</p>
        </div>
        <Link
          href="/upload"
          className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-4 py-2 rounded-full transition"
        >
          ➕ Upload
        </Link>
      </div>

      <section className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {curricula.length === 0 ? (
          <div className="col-span-full bg-white/5 backdrop-blur-sm rounded-2xl p-6 text-center text-gray-400 border border-white/10">
            No curricula yet. Upload a video to get started.
          </div>
        ) : (
          curricula.map((c) => (
            <Link
              key={c.id}
              href={`/curriculum/${c.id}`}
              className="bg-white/5 backdrop-blur-sm rounded-2xl p-6 border border-white/10 hover:scale-[1.02] transition-all duration-200 hover:border-indigo-500/50"
            >
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="text-lg font-semibold text-white">{c.title}</h3>
                  <p className="mt-1 text-sm text-gray-400">
                    {c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}
                  </p>
                </div>
                <span
                  className={`text-sm px-2 py-1 rounded-full ${
                    c.status === "ready"
                      ? "bg-green-500/20 text-green-400"
                      : c.status === "queued"
                      ? "bg-yellow-500/20 text-yellow-400"
                      : "bg-gray-500/20 text-gray-400"
                  }`}
                >
                  {c.status}
                </span>
              </div>
            </Link>
          ))
        )}
      </section>
    </main>
  );
}