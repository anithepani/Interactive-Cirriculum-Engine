import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto max-w-3xl px-6 py-20">
      <h1 className="text-4xl font-bold tracking-tight text-brand">
        Interactive Curriculum Engine
      </h1>
      <p className="mt-4 text-lg text-gray-300">
        Turn passive tutorial videos into active practice. Submit a video and the
        system generates checkpoints, MCQs, coding challenges, debugging tasks,
        and conceptual questions that test <em>transfer of understanding</em>,
        not recall.
      </p>
      <div className="mt-8 flex gap-4">
        <Link
          href="/learn"
          className="rounded-md bg-brand px-5 py-2.5 font-medium text-white hover:bg-brand-dark"
        >
          Start learning
        </Link>
        <Link
          href="/dashboard"
          className="rounded-md border border-gray-700 px-5 py-2.5 font-medium text-gray-200 hover:bg-gray-900"
        >
          Dashboard
        </Link>
      </div>
      <p className="mt-12 text-sm text-gray-500">
        Status: Phase 0 (R&amp;D Spike &amp; Foundations). v0.1.0
      </p>
    </main>
  );
}
