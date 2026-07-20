"use client";

import { useState } from "react";
import { Film, BookOpen, Sparkles } from "lucide-react";
import LoadingSpinner from "@/components/LoadingSpinner";

interface RecapTabsProps {
  recapStatus: "none" | "processing" | "ready" | "failed";
  recapUrl: string | null;
  studyGuideHtml: string | null;
  onTrigger: () => void;
}

type TabKey = "recap" | "study";

/**
 * Recap Video + Study Guide surface (Feature 1).
 *
 * Before generation the tab bar is hidden entirely — only a "Generate" call to
 * action (or a processing/failed state) is shown. Once the recap payload
 * transitions to `ready`, a minimal tabbed container appears: one view rendered
 * at a time, switched via a lightweight underline-accent tab bar with a fade
 * transition, matching the ICE theme.
 */
export default function RecapTabs({
  recapStatus,
  recapUrl,
  studyGuideHtml,
  onTrigger,
}: RecapTabsProps) {
  const hasStudy = Boolean(studyGuideHtml);
  const [active, setActive] = useState<TabKey>("recap");

  // ---- Pre-ready states: no tab bar, just the CTA / status card ----
  if (recapStatus === "none") {
    return (
      <div className="mt-4 rounded-[2rem] border border-ink/10 bg-white p-8 text-center shadow-sm">
        <h2 className="font-display text-xl font-bold text-ink">Want a quick summary?</h2>
        <p className="mx-auto mt-2 max-w-lg text-ink-soft">
          Generate a short video supercut plus a written study guide covering the
          most important concepts from this curriculum.
        </p>
        <button
          onClick={onTrigger}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 font-semibold text-white transition hover:bg-indigo-700"
        >
          <Sparkles className="h-4 w-4" /> Generate Recap &amp; Summary
        </button>
      </div>
    );
  }

  if (recapStatus === "processing") {
    return (
      <div className="mt-4 rounded-[2rem] border border-ink/10 bg-white p-8 text-center shadow-sm">
        <h2 className="font-display text-xl font-bold text-ink">Generating Recap &amp; Summary…</h2>
        <p className="mx-auto mb-6 mt-2 max-w-lg text-ink-soft">
          We are extracting the key moments and rendering your supercut. This
          takes about 1–2 minutes.
        </p>
        <LoadingSpinner size={32} />
      </div>
    );
  }

  if (recapStatus === "failed") {
    return (
      <div className="mt-4 rounded-[2rem] border border-rose-200 bg-rose-50 p-8 text-center text-rose-700">
        <h2 className="font-display text-xl font-bold">Failed to generate recap</h2>
        <p className="mt-2">There was an issue creating the recap. Please try again.</p>
        <button
          onClick={onTrigger}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-rose-600 px-6 py-3 font-semibold text-white transition hover:bg-rose-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  // ---- ready: tabbed container ----
  const tabs: { key: TabKey; label: string; icon: typeof Film; enabled: boolean }[] = [
    { key: "recap", label: "Recap Video", icon: Film, enabled: Boolean(recapUrl) },
    { key: "study", label: "Study Guide / Summary", icon: BookOpen, enabled: hasStudy },
  ];

  return (
    <div className="mt-4 rounded-[2rem] border border-ink/10 bg-white p-6 shadow-sm">
      {/* Tab bar — minimal underline accent */}
      <div className="mb-6 flex gap-2 border-b border-ink/10">
        {tabs.map((tab) => {
          const isActive = active === tab.key;
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              disabled={!tab.enabled}
              onClick={() => setActive(tab.key)}
              className={`relative flex items-center gap-2 rounded-t-xl px-4 py-2.5 text-sm font-semibold transition
                ${isActive ? "text-indigo-600" : "text-ink-soft hover:text-ink"}
                ${!tab.enabled ? "cursor-not-allowed opacity-40" : ""}`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
              <span
                className={`absolute inset-x-2 -bottom-px h-0.5 rounded-full transition-all duration-300
                  ${isActive ? "bg-indigo-600 opacity-100" : "opacity-0"}`}
              />
            </button>
          );
        })}
      </div>

      {/* Panels — only the active one is mounted, with a fade-in. */}
      <div key={active} className="animate-[recapFade_0.25s_ease]">
        {active === "recap" &&
          (recapUrl ? (
            <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black">
              <video
                src={recapUrl}
                controls
                className="h-full w-full object-contain"
                controlsList="nodownload"
              />
            </div>
          ) : (
            <p className="py-8 text-center text-ink-soft">Recap video is not available.</p>
          ))}
        {active === "study" &&
          (hasStudy ? (
            <div
              className="study-guide-content prose prose-sm max-w-none text-ink"
              dangerouslySetInnerHTML={{ __html: studyGuideHtml as string }}
            />
          ) : (
            <p className="py-8 text-center text-ink-soft">Study guide is not available.</p>
          ))}
      </div>

      <style jsx>{`
        @keyframes recapFade {
          from {
            opacity: 0;
            transform: translateY(4px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </div>
  );
}
