"use client";

import { useState } from "react";
import { Film, BookOpen, Sparkles, Video, Bot } from "lucide-react";
import LoadingSpinner from "@/components/LoadingSpinner";

import ConceptGraph from "./ConceptGraph";
import TutorChat from "./TutorChat";

interface MediaTabsProps {
  curriculumId: number;
  recapStatus: "none" | "processing" | "ready" | "failed";
  recapUrl: string | null;
  studyGuideHtml: string | null;
  onTriggerRecap: () => void;
  
  signalStatus: "none" | "queued" | "processing" | "ready" | "failed";
  signalUrl: string | null;
  onTriggerSignal: () => void;
  
  getCurrentTime: () => number;
}

type TabKey = "signal" | "recap" | "study" | "graph" | "tutor";

export default function MediaTabs({
  curriculumId,
  recapStatus,
  recapUrl,
  studyGuideHtml,
  onTriggerRecap,
  signalStatus,
  signalUrl,
  onTriggerSignal,
  getCurrentTime,
}: MediaTabsProps) {
  const [active, setActive] = useState<TabKey>("signal");

  const tabs: { key: TabKey; label: string; icon: any }[] = [
    { key: "signal", label: "Cinematic Summary", icon: Video },
    { key: "recap", label: "Recap Video", icon: Film },
    { key: "study", label: "Study Guide", icon: BookOpen },
    { key: "graph", label: "Skill Tree", icon: Sparkles },
    { key: "tutor", label: "AI Tutor", icon: Bot },
  ];

  const renderContent = () => {
    if (active === "tutor") {
      return (
        <div className="pt-2">
          <TutorChat curriculumId={curriculumId} getCurrentTime={getCurrentTime} />
        </div>
      );
    }
    if (active === "graph") {
      return (
        <div className="pt-2">
          <ConceptGraph curriculumId={curriculumId} />
        </div>
      );
    }
    if (active === "signal") {
      if (signalStatus === "none") {
        return (
          <div className="py-12 text-center">
            <h2 className="font-display text-xl font-bold text-ink">Want a Cinematic Summary?</h2>
            <p className="mx-auto mt-2 max-w-lg text-ink-soft">
              Generate a high-quality &quot;Signal-to-Noise&quot; video featuring professional voiceover and dynamic moving visuals.
            </p>
            <button
              onClick={onTriggerSignal}
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 font-semibold text-white transition hover:bg-indigo-700"
            >
              <Sparkles className="h-4 w-4" /> Generate Cinematic Video
            </button>
          </div>
        );
      }
      if (signalStatus === "processing" || signalStatus === "queued") {
        return (
          <div className="py-12 text-center">
            <h2 className="font-display text-xl font-bold text-ink">Generating Cinematic Video...</h2>
            <p className="mx-auto mb-6 mt-2 max-w-lg text-ink-soft">
              We are analyzing the transcript, generating voiceovers, and fetching HD B-roll. This takes about 2-3 minutes.
            </p>
            <LoadingSpinner size={32} />
          </div>
        );
      }
      if (signalStatus === "failed") {
        return (
          <div className="py-12 text-center text-rose-700">
            <h2 className="font-display text-xl font-bold">Failed to generate video</h2>
            <p className="mt-2">There was an issue creating the cinematic recap. Please try again.</p>
            <button
              onClick={onTriggerSignal}
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-rose-600 px-6 py-3 font-semibold text-white transition hover:bg-rose-700"
            >
              Try Again
            </button>
          </div>
        );
      }
      if (signalUrl) {
        return (
          <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black">
            <video
              src={signalUrl}
              controls
              className="h-full w-full object-contain"
              controlsList="nodownload"
            />
          </div>
        );
      }
    }

    if (active === "recap") {
      if (recapStatus === "none") {
        return (
          <div className="py-12 text-center">
            <h2 className="font-display text-xl font-bold text-ink">Want a quick summary?</h2>
            <p className="mx-auto mt-2 max-w-lg text-ink-soft">
              Generate a short video supercut covering the most important concepts from this curriculum.
            </p>
            <button
              onClick={onTriggerRecap}
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 font-semibold text-white transition hover:bg-indigo-700"
            >
              <Sparkles className="h-4 w-4" /> Generate Recap Video
            </button>
          </div>
        );
      }
      if (recapStatus === "processing") {
        return (
          <div className="py-12 text-center">
            <h2 className="font-display text-xl font-bold text-ink">Generating Recap...</h2>
            <p className="mx-auto mb-6 mt-2 max-w-lg text-ink-soft">
              We are extracting the key moments and rendering your supercut. This takes about 1-2 minutes.
            </p>
            <LoadingSpinner size={32} />
          </div>
        );
      }
      if (recapStatus === "failed") {
        return (
          <div className="py-12 text-center text-rose-700">
            <h2 className="font-display text-xl font-bold">Failed to generate recap</h2>
            <p className="mt-2">There was an issue creating the recap. Please try again.</p>
            <button
              onClick={onTriggerRecap}
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-rose-600 px-6 py-3 font-semibold text-white transition hover:bg-rose-700"
            >
              Try Again
            </button>
          </div>
        );
      }
      if (recapUrl) {
        return (
          <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-black">
            <video
              src={recapUrl}
              controls
              className="h-full w-full object-contain"
              controlsList="nodownload"
            />
          </div>
        );
      }
    }

    if (active === "study") {
      if (recapStatus === "none" || recapStatus === "failed") {
        return (
          <div className="py-12 text-center">
            <h2 className="font-display text-xl font-bold text-ink">Study Guide</h2>
            <p className="mx-auto mt-2 max-w-lg text-ink-soft">
              Generate a recap video to also unlock a comprehensive written study guide.
            </p>
            <button
              onClick={() => setActive("recap")}
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-3 font-semibold text-white transition hover:bg-indigo-700"
            >
              Go to Recap
            </button>
          </div>
        );
      }
      if (recapStatus === "processing") {
        return (
          <div className="py-12 text-center">
            <h2 className="font-display text-xl font-bold text-ink">Generating Study Guide...</h2>
            <p className="mx-auto mb-6 mt-2 max-w-lg text-ink-soft">
              Writing comprehensive notes and conceptual summaries...
            </p>
            <LoadingSpinner size={32} />
          </div>
        );
      }
      if (studyGuideHtml) {
        return (
          <div
            className="study-guide-content prose prose-sm max-w-none text-ink bg-white p-6 rounded-xl border border-ink/5"
            dangerouslySetInnerHTML={{ __html: studyGuideHtml }}
          />
        );
      }
    }

    return null;
  };

  return (
    <div className="mt-8 rounded-[2rem] border border-ink/10 bg-white p-6 shadow-sm">
      <div className="mb-6 flex gap-2 border-b border-ink/10 overflow-x-auto pb-1">
        {tabs.map((tab) => {
          const isActive = active === tab.key;
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => setActive(tab.key)}
              className={`relative flex items-center gap-2 rounded-t-xl px-5 py-3 text-sm font-semibold transition whitespace-nowrap
                ${isActive ? "text-indigo-600 bg-indigo-50/50" : "text-ink-soft hover:text-ink hover:bg-ink/5"}`}
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

      <div className="animate-[recapFade_0.25s_ease] min-h-[300px] flex flex-col justify-center">
        {renderContent()}
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
