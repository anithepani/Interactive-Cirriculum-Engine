"use client";

import { useSearchParams, useRouter } from "next/navigation";
import { ArrowLeft, ExternalLink, ShieldAlert } from "lucide-react";
import { Suspense, useEffect, useState } from "react";

import AppLayout from "@/components/layout/AppLayout";

function ReaderContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const url = searchParams.get("url");
  const [hostname, setHostname] = useState<string>("Unknown Source");

  useEffect(() => {
    if (url) {
      try {
        const parsedUrl = new URL(url);
        setHostname(parsedUrl.hostname);
      } catch (e) {
        setHostname("Invalid URL");
      }
    }
  }, [url]);

  if (!url) {
    return (
      <AppLayout>
        <div className="flex h-full flex-col items-center justify-center bg-canvas pt-24">
          <div className="flex flex-col items-center rounded-3xl bg-white p-12 text-center shadow-sm border border-ink/5">
            <ShieldAlert className="mb-4 h-12 w-12 text-rose-500" />
            <h1 className="mb-2 font-display text-2xl font-bold text-ink">No URL Provided</h1>
            <p className="mb-8 text-ink-soft">We couldn&apos;t find a valid link to read.</p>
            <button
              onClick={() => router.back()}
              className="flex items-center gap-2 rounded-full bg-indigo-600 px-6 py-3 font-semibold text-white transition hover:bg-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              <ArrowLeft className="h-5 w-5" />
              Go Back
            </button>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="-m-8 flex h-[calc(100vh-68px)] flex-col bg-canvas overflow-hidden">
        {/* Top Header */}
        <header className="flex h-[60px] shrink-0 items-center justify-between border-b border-ink/10 bg-white px-6">
          <div className="flex items-center gap-6">
            <button
              onClick={() => router.back()}
              className="flex items-center gap-2 text-sm font-semibold text-ink-soft transition hover:text-ink focus-visible:outline-none"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-ink/5 transition hover:bg-ink/10">
                <ArrowLeft className="h-4 w-4" />
              </div>
              Back to Discover
            </button>
            <div className="hidden h-6 w-px bg-ink/10 sm:block" />
            <div className="flex items-center gap-2">
              <span className="rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700">
                Reader Mode
              </span>
              <span className="hidden text-sm font-medium text-ink sm:block truncate max-w-md">
                {hostname}
              </span>
            </div>
          </div>

          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 rounded-full border border-ink/10 bg-white px-4 py-2 text-sm font-medium text-ink transition hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 shadow-sm"
          >
            <ExternalLink className="h-4 w-4 text-ink-soft" />
            <span className="hidden sm:inline">Open Original</span>
          </a>
        </header>

        {/* Iframe Body - Force bg-white to prevent transparency bleed-through */}
        <div className="flex-1 bg-white relative">
          <iframe
            src={url}
            className="absolute inset-0 h-full w-full border-none bg-white"
            sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
            title="Reader View"
          />
        </div>
      </div>
    </AppLayout>
  );
}

export default function ReaderPage() {
  return (
    <Suspense fallback={<div className="h-screen bg-canvas flex items-center justify-center">Loading...</div>}>
      <ReaderContent />
    </Suspense>
  );
}
