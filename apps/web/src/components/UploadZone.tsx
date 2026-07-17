/**
 * UploadZone — light-theme version
 * ----------------------------------
 * Drag-and-drop file zone on the site's light canvas (bg-canvas = #f4f4f4).
 * Uses white bg, ink borders, and dark readable text — consistent with the
 * landing page's light card style (bg-white border border-ink/10).
 */

"use client";

import { useRef, useState } from "react";
import { Upload, File, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  selectedFile: File | null;
  onClear: () => void;
  disabled?: boolean;
}

export default function UploadZone({
  onFileSelect,
  selectedFile,
  onClear,
  disabled = false,
}: UploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  /* ── Drag handlers ─────────────────────────────────────────────────── */
  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragOver(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (disabled) return;
    const file = e.dataTransfer.files?.[0];
    if (file) onFileSelect(file);
  };

  /* ── Click-to-browse ───────────────────────────────────────────────── */
  const handleClick = () => {
    if (!disabled) inputRef.current?.click();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) onFileSelect(file);
    e.target.value = "";
  };

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        className="sr-only"
        onChange={handleInputChange}
        aria-label="Upload video file"
      />

      <motion.div
        onClick={handleClick}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        animate={{ scale: isDragOver ? 1.02 : 1 }}
        transition={{ type: "spring", stiffness: 260, damping: 22 }}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        onKeyDown={(e) => e.key === "Enter" && handleClick()}
        className={cn(
          "relative flex min-h-[200px] cursor-pointer flex-col items-center justify-center gap-4",
          "rounded-[2rem] border-2 border-dashed p-8 text-center transition-all duration-200",
          isDragOver
            ? "border-indigo-400 bg-indigo-50"
            : "border-ink/20 bg-ink/[0.03] hover:border-indigo-300 hover:bg-indigo-50/40",
          disabled && "cursor-not-allowed opacity-50"
        )}
      >
        <AnimatePresence mode="wait">
          {selectedFile ? (
            /* ── File selected ─────────────────────────────────────── */
            <motion.div
              key="file-selected"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex flex-col items-center gap-3"
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-100 text-indigo-600">
                <File className="h-7 w-7" />
              </div>
              <div>
                <p className="font-display font-semibold text-ink">
                  {selectedFile.name}
                </p>
                <p className="mt-1 text-sm text-ink-soft">
                  {(selectedFile.size / 1024 / 1024).toFixed(1)} MB
                </p>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onClear();
                }}
                className="inline-flex items-center gap-1.5 rounded-full border border-ink/15 px-3 py-1.5
                           text-xs font-medium text-ink-soft transition hover:border-rose-300 hover:text-rose-600"
              >
                <X className="h-3.5 w-3.5" />
                Remove
              </button>
            </motion.div>
          ) : (
            /* ── Idle / drag-over ──────────────────────────────────── */
            <motion.div
              key="idle"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex flex-col items-center gap-4"
            >
              {/* Pulsing icon */}
              <motion.div
                animate={
                  isDragOver
                    ? { scale: 1.15 }
                    : { scale: [1, 1.06, 1] }
                }
                transition={
                  isDragOver
                    ? { type: "spring", stiffness: 260, damping: 20 }
                    : { duration: 2.5, repeat: Infinity, ease: "easeInOut" }
                }
                className={cn(
                  "flex h-16 w-16 items-center justify-center rounded-2xl transition-colors duration-200",
                  isDragOver ? "bg-indigo-200 text-indigo-700" : "bg-ink/8 text-ink-soft"
                )}
              >
                <Upload className="h-8 w-8" />
              </motion.div>

              <div className="space-y-1">
                <p className="font-display text-lg font-bold text-ink">
                  {isDragOver ? "Drop to upload" : "Drop your video here"}
                </p>
                <p className="text-sm text-ink-soft">
                  or{" "}
                  <span className="font-medium text-indigo-600 underline-offset-2 hover:underline">
                    click to browse
                  </span>
                </p>
              </div>

              <p className="text-xs text-ink-soft/60">
                Supported: MP4, MOV, WebM, MKV · Max 2 GB
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
