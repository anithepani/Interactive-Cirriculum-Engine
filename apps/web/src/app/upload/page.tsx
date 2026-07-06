"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function UploadPage() {
  const [videoUrl, setVideoUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/v1/curricula", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_url: videoUrl, title: "Uploaded curriculum" }),
      });
      if (!res.ok) throw new Error(await res.text());
      const body = await res.json();
      router.push(`/curriculum/${body.curriculum_id}`);
    } catch (err) {
      setError((err as Error).message || "Failed to upload");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-3xl">
      <div className="glass rounded-3xl p-8">
        <h1 className="text-3xl font-semibold">Upload a YouTube video</h1>
        <p className="mt-2 text-gray-300">Paste a YouTube URL and start generating an interactive curriculum.</p>

        <form className="mt-6 flex gap-3" onSubmit={submit}>
          <input
            className="flex-1 rounded-full bg-black/60 px-4 py-3 text-white outline-none placeholder:text-gray-400"
            placeholder="https://www.youtube.com/watch?v=..."
            value={videoUrl}
            onChange={(e) => setVideoUrl(e.target.value)}
          />
          <button type="submit" className="btn-primary rounded-full px-6 py-3 text-white font-semibold">
            {loading ? <LoadingSpinner size={18} /> : "Generate"}
          </button>
        </form>

        {error ? <div className="mt-4 text-sm text-red-400">{error}</div> : null}
      </div>
    </main>
  );
}
