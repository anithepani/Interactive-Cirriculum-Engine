"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function UploadPage() {
  const [videoUrl, setVideoUrl] = useState("");
  const [draggedFile, setDraggedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);
    try {
      const res = await fetch("/api/v1/curricula", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_url: videoUrl, title: "Uploaded curriculum" }),
      });
      if (!res.ok) throw new Error(await res.text());
      const body = await res.json();
      setSuccess("Curriculum created successfully!");
      router.push(`/curriculum/${body.curriculum_id}`);
    } catch (err) {
      setError((err as Error).message || "Failed to upload");
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    if (event.dataTransfer.files?.length) {
      setDraggedFile(event.dataTransfer.files[0]);
      setVideoUrl(event.dataTransfer.files[0].name);
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  return (
    <div className="mx-auto max-w-4xl">
      <div className="rounded-[32px] border border-white/10 bg-slate-950/90 p-8 shadow-2xl shadow-black/20">
        <h1 className="text-3xl font-semibold text-white">Upload a curriculum</h1>
        <p className="mt-3 text-slate-300">Paste a YouTube URL or drop a local file to create a new interactive course.</p>

        <form onSubmit={submit} className="mt-8 space-y-6">
          <div className="grid gap-4 sm:grid-cols-[1fr_auto]">
            <label className="block rounded-3xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
              <span className="block text-slate-400">YouTube URL</span>
              <input
                type="url"
                value={videoUrl}
                onChange={(e) => setVideoUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
                className="mt-3 w-full bg-transparent text-white outline-none placeholder:text-slate-500"
              />
            </label>
            <button
              type="submit"
              disabled={loading || (!videoUrl && !draggedFile)}
              className="inline-flex items-center justify-center rounded-full bg-indigo-500 px-6 py-3 text-sm font-semibold text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? <LoadingSpinner size={18} /> : "Generate curriculum"}
            </button>
          </div>

          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            className="rounded-3xl border border-dashed border-white/15 bg-slate-900/80 p-10 text-center text-slate-300 transition hover:border-indigo-400/60 hover:bg-slate-900"
          >
            <p className="text-lg font-semibold text-white">Drag and drop a video file</p>
            <p className="mt-2 text-sm text-slate-400">Or use the URL field above to import from YouTube.</p>
            {draggedFile ? <p className="mt-3 text-slate-200">Selected file: {draggedFile.name}</p> : null}
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl bg-slate-900/80 p-5 text-sm text-slate-300">
              <p className="font-semibold text-white">What happens next?</p>
              <ul className="mt-3 space-y-2 text-slate-400">
                <li>• The backend generates checkpoints from key video segments.</li>
                <li>• You can view progress and open the curriculum player instantly.</li>
              </ul>
            </div>
            <div className="rounded-3xl bg-slate-900/80 p-5 text-sm text-slate-300">
              <p className="font-semibold text-white">Tips for best results</p>
              <ul className="mt-3 space-y-2 text-slate-400">
                <li>• Use a public YouTube tutorial or local video file.</li>
                <li>• Keep the content under 20 minutes for faster processing.</li>
              </ul>
            </div>
          </div>
        </form>

        {error ? <p className="mt-4 text-sm text-rose-400">{error}</p> : null}
        {success ? <p className="mt-4 text-sm text-emerald-400">{success}</p> : null}
      </div>
    </div>
  );
}
