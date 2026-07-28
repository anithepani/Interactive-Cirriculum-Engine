import React from "react";

interface CodeBlockProps {
  code: string;
  language?: string;
}

export default function CodeBlock({ code, language = "python" }: CodeBlockProps) {
  return (
    <div className="relative font-mono text-sm">
      <div className="flex items-center justify-between px-4 py-2 bg-[#0d1117] border-b border-white/10">
        <span className="text-xs text-zinc-400 font-bold uppercase tracking-wider">{language}</span>
      </div>
      <div className="p-4 bg-[#0d1117] text-[#c9d1d9] overflow-x-auto">
        <pre className="whitespace-pre-wrap leading-relaxed">{code}</pre>
      </div>
    </div>
  );
}
