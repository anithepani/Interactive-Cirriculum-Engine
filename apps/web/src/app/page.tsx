import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto min-h-screen max-w-5xl px-6 py-20 text-white">
      <div className="rounded-3xl border border-white/10 bg-slate-950 p-10 shadow-2xl shadow-black/40">
        <p className="text-sm uppercase tracking-[0.32em] text-blue-400">Interactive Curriculum Engine</p>
        <h1 className="mt-4 text-5xl font-semibold leading-tight text-white sm:text-6xl">
          Turn tutorial videos into interactive learning journeys.
        </h1>
        <p className="mt-6 max-w-3xl text-lg leading-8 text-gray-300">
          Submit a YouTube URL, generate an adaptive curriculum, then practice with concept checkpoints, coding exercises, and mock evaluation directly in the browser.
        </p>

        <div className="mt-10 grid gap-4 sm:grid-cols-2">
          <Link
            href="/upload"
            className="rounded-3xl bg-blue-500 px-6 py-4 text-center text-lg font-semibold text-white transition hover:bg-blue-400"
          >
            Upload video
          </Link>
          <Link
            href="/dashboard"
            className="rounded-3xl border border-white/10 bg-white/5 px-6 py-4 text-center text-lg font-semibold text-white transition hover:border-blue-400"
          >
            View dashboard
          </Link>
        </div>
      </div>
    </main>
  );
}
