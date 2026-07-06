"use client";

import Link from "next/link";

export default function Navbar() {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-white/6 bg-black/30 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-6 py-4">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-white shadow-md">
            ICE
          </div>
          <div className="hidden items-baseline text-sm sm:flex">
            <span className="font-semibold">Interactive</span>
            <span className="ml-1 text-gray-400">Curriculum Engine</span>
          </div>
        </Link>

        <nav className="flex items-center gap-4">
          <Link
            href="/upload"
            className="rounded-lg px-3 py-2 text-sm font-medium text-white hover:bg-white/5"
          >
            Upload
          </Link>
          <Link
            href="/dashboard"
            className="rounded-lg px-3 py-2 text-sm font-medium text-white/80 hover:bg-white/5"
          >
            Dashboard
          </Link>
        </nav>
      </div>
    </header>
  );
}