import React from "react";

export default function SectionHeader({ title, subtitle }: { title: string; subtitle: string; }) {
  return (
    <div className="mb-8 max-w-3xl">
      <p className="text-sm font-semibold uppercase tracking-[0.28em] text-indigo-300">Interactive Curriculum Engine</p>
      <h2 className="mt-3 text-4xl font-semibold text-white sm:text-5xl">{title}</h2>
      <p className="mt-4 text-base leading-8 text-slate-300">{subtitle}</p>
    </div>
  );
}
