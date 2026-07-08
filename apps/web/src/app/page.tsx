import Link from "next/link";

const featureList = [
  {
    title: "AI checkpoint generation",
    description: "Automatically identify key concepts and insert learning checkpoints into your video content.",
  },
  {
    title: "Interactive coding practice",
    description: "Run code directly inside the browser and get instant execution feedback.",
  },
  {
    title: "Progress tracking",
    description: "Monitor completion status, review weak concepts, and stay motivated with insight cards.",
  },
];

const exampleCurricula = [
  { title: "JavaScript Fundamentals", status: "Ready", progress: 78 },
  { title: "Python Data Science", status: "Queued", progress: 18 },
  { title: "React Component Patterns", status: "Ready", progress: 92 },
];

export default function HomePage() {
  return (
    <div className="space-y-16">
      <section className="relative overflow-hidden rounded-[32px] border border-white/10 bg-slate-950/90 px-6 py-16 shadow-2xl shadow-black/30 sm:px-10 lg:px-14">
        <div className="absolute inset-x-0 top-0 h-80 bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.18),_transparent_35%)]" />
        <div className="relative grid gap-12 lg:grid-cols-[0.9fr_0.9fr] lg:items-center">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold uppercase tracking-[0.32em] text-indigo-300">Interactive Curriculum Engine</p>
            <h1 className="mt-4 text-5xl font-semibold tracking-tight text-white sm:text-6xl">
              Transform videos into modern learning experiences with AI-driven checkpoints.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-300">
              Upload a tutorial or paste a link, then watch the system create immersive, interactive curricula with coding challenges, conceptual checks, and instructor-quality feedback.
            </p>
            <div className="mt-10 flex flex-col gap-4 sm:flex-row sm:items-center">
              <Link href="/upload" className="inline-flex items-center justify-center rounded-full bg-indigo-500 px-7 py-3 text-sm font-semibold text-white transition hover:bg-indigo-400">
                Get started
              </Link>
              <Link href="/dashboard" className="inline-flex items-center justify-center rounded-full border border-white/10 bg-white/5 px-7 py-3 text-sm font-semibold text-slate-100 transition hover:border-indigo-400">
                Explore dashboard
              </Link>
            </div>
          </div>

          <div className="rounded-[28px] bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 p-8 shadow-2xl shadow-black/40 ring-1 ring-white/5">
            <div className="mb-6 flex items-center justify-between rounded-3xl bg-white/5 px-4 py-4 text-sm text-slate-200">
              <span>Live Curriculum Preview</span>
              <span className="rounded-full bg-indigo-500/20 px-3 py-1 text-indigo-200">AI First</span>
            </div>
            <div className="space-y-4">
              {exampleCurricula.map((item) => (
                <div key={item.title} className="rounded-3xl border border-white/10 bg-slate-950/60 p-5">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <h3 className="text-lg font-semibold text-white">{item.title}</h3>
                      <p className="mt-1 text-sm text-slate-400">{item.status} curriculum</p>
                    </div>
                    <span className="rounded-full bg-slate-800/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-slate-200">{item.progress}%</span>
                  </div>
                  <div className="mt-4 h-2 overflow-hidden rounded-full bg-white/5">
                    <div className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-cyan-400 to-violet-400" style={{ width: `${item.progress}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        {featureList.map((feature) => (
          <div key={feature.title} className="rounded-[28px] border border-white/10 bg-white/5 p-8 shadow-lg shadow-black/10 transition hover:-translate-y-1 hover:border-indigo-500/30 hover:bg-slate-900/80">
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-indigo-300">Feature</p>
            <h2 className="mt-4 text-2xl font-semibold text-white">{feature.title}</h2>
            <p className="mt-3 text-slate-300">{feature.description}</p>
          </div>
        ))}
      </section>

      <section className="rounded-[32px] border border-white/10 bg-slate-950/80 p-8 shadow-2xl shadow-black/20">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.28em] text-indigo-300">Why ICE?</p>
            <h2 className="mt-3 text-3xl font-semibold text-white">Built for modern learners and creators.</h2>
          </div>
          <Link href="/dashboard" className="inline-flex items-center rounded-full bg-indigo-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-indigo-400">
            View dashboard
          </Link>
        </div>
        <div className="mt-8 grid gap-6 md:grid-cols-2">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <h3 className="text-xl font-semibold text-white">Fast onboarding</h3>
            <p className="mt-3 text-slate-300">From upload to learning checkpoints in seconds, the platform makes every tutorial interactive.</p>
          </div>
          <div className="rounded-3xl border border-white/10 bg-white/5 p-6">
            <h3 className="text-xl font-semibold text-white">Smart feedback</h3>
            <p className="mt-3 text-slate-300">Students receive instant results and refined guidance based on coding and conceptual responses.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
