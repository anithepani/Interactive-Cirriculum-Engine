export default function Footer() {
  return (
    <footer className="border-t border-white/10 bg-slate-950/80 px-4 py-8 text-slate-400 sm:px-6">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 text-sm sm:flex-row sm:items-center sm:justify-between">
        <p>Interactive Curriculum Engine © {new Date().getFullYear()}</p>
        <div className="flex flex-wrap items-center gap-4 text-slate-400">
          <a href="/" className="transition hover:text-white">Home</a>
          <a href="/dashboard" className="transition hover:text-white">Dashboard</a>
          <a href="/upload" className="transition hover:text-white">Upload</a>
        </div>
      </div>
    </footer>
  );
}
