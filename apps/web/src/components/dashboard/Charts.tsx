"use client";

import { motion } from "framer-motion";
import type { CurriculumSummary } from "@/lib/types";
import { useMemo, useState } from "react";

export function DashboardAreaChart({ data = [] }: { data: CurriculumSummary[] }) {
  // Group curricula by day of week
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  const dayNames = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
  // Index of the point the pointer is currently over (drives the tooltip).
  const [hovered, setHovered] = useState<number | null>(null);
  const stats = useMemo(() => {
    const counts = [0, 0, 0, 0, 0, 0, 0];
    data.forEach(item => {
      if (item.created_at) {
        const date = new Date(item.created_at);
        counts[date.getDay()]++;
      }
    });
    const max = Math.max(...counts, 1);
    return counts.map((count, i) => {
      // 0 = Sun, 6 = Sat
      const x = (i / 6) * 600;
      // SVG Y goes down, so 0 is top, 160 is bottom (padding top 20, padding bottom 20)
      const y = 160 - (count / max) * 120; 
      return { day: days[i], count, x, y };
    });
  }, [data]);

  const linePath = `M ${stats.map(s => `${s.x},${s.y}`).join(" L ")}`;
  const areaPath = `${linePath} L 600,180 L 0,180 Z`;

  return (
    <div className="relative h-48 w-full">
      {/* SVG Chart */}
      <svg viewBox="0 -10 600 200" className="h-full w-full overflow-visible">
        <defs>
          <linearGradient id="gradient-area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#4f46e5" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#4f46e5" stopOpacity="0" />
          </linearGradient>
          <clipPath id="wipe-clip">
            <motion.rect
              x="0" y="-50" width="600" height="300"
              initial={{ width: 0 }}
              animate={{ width: 600 }}
              transition={{ duration: 1.5, ease: "easeOut" }}
            />
          </clipPath>
        </defs>
        
        <g clipPath="url(#wipe-clip)">
          {/* Area fill */}
          <path
            d={areaPath}
            fill="url(#gradient-area)"
          />
          
          {/* Line */}
          <path
            d={linePath}
            fill="none"
            stroke="#4f46e5"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </g>
        
        {/* Data points */}
        {stats.map((stat, i) => (
          <motion.circle
            key={i}
            cx={stat.x}
            cy={stat.y}
            r={hovered === i ? 7 : 5}
            fill="#ffffff"
            stroke="#4f46e5"
            strokeWidth="3"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 1 + i * 0.1, type: "spring" }}
          />
        ))}

        {/* Invisible wide hit-targets so hovering anywhere in a day's column
            reveals its tooltip, not just the 5px dot. */}
        {stats.map((stat, i) => (
          <rect
            key={`hit-${i}`}
            x={stat.x - 42}
            y={-10}
            width={84}
            height={200}
            fill="transparent"
            style={{ cursor: "pointer" }}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered((cur) => (cur === i ? null : cur))}
          />
        ))}
      </svg>

      {/* Hover tooltip — absolutely positioned over the active data point. */}
      {hovered !== null && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-lg bg-ink px-3 py-1.5 text-center shadow-lg"
          style={{
            left: `${(stats[hovered].x / 600) * 100}%`,
            top: `${(stats[hovered].y / 200) * 100}%`,
          }}
        >
          <p className="whitespace-nowrap text-[11px] font-semibold text-white">
            {stats[hovered].count} {stats[hovered].count === 1 ? "curriculum" : "curricula"}
          </p>
          <p className="text-[10px] text-white/60">{dayNames[hovered]}</p>
        </motion.div>
      )}

      {/* X-axis labels and tooltips overlay */}
      <div className="absolute inset-0 flex justify-between">
        {stats.map((stat, i) => (
          <div key={stat.day} className="flex h-full flex-col items-center justify-between" style={{ width: '14.28%' }}>
            {/* Static per-day value (kept subtle; the hover tooltip is richer) */}
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1 + i * 0.1 }}
              className="mt-2 text-xs font-bold text-indigo-600"
            >
              {stat.count > 0 ? stat.count : ""}
            </motion.div>
            
            {/* X-axis label */}
            <span className={`mb-[-1.5rem] text-xs font-medium transition-colors ${hovered === i ? "text-indigo-600" : "text-ink-soft"}`}>{stat.day}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function DashboardDonutChart({ data = [] }: { data: CurriculumSummary[] }) {
  const [tip, setTip] = useState<string | null>(null);
  const stats = useMemo(() => {
    const total = data.length || 1; // avoid div by 0
    let completed = 0;
    let processing = 0;
    let failed = 0;
    
    data.forEach(item => {
      if (item.status === "ready") completed++;
      else if (item.status === "failed") failed++;
      else processing++;
    });
    
    return {
      completed,
      processing,
      failed,
      total,
      percent: Math.round((completed / total) * 100) || 0
    };
  }, [data]);

  // SVG calculations
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const completedDash = (stats.completed / stats.total) * circumference;
  const failedDash = (stats.failed / stats.total) * circumference;
  
  return (
    <div className="flex flex-col items-center">
      <div className="relative flex h-40 w-40 items-center justify-center">
        <svg className="h-full w-full -rotate-90 transform" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r={radius} fill="transparent" stroke="currentColor" strokeWidth="12" className="text-ink/5" />
          
          {stats.failed > 0 && (
            <motion.circle
              cx="50" cy="50" r={radius}
              fill="transparent"
              stroke="currentColor"
              strokeWidth="12"
              className="text-rose-500"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: circumference - failedDash }}
              transition={{ duration: 1.5, ease: "easeOut" }}
            />
          )}

          <motion.circle
            cx="50" cy="50" r={radius}
            fill="transparent"
            stroke="currentColor"
            strokeWidth="12"
            className="text-indigo-600"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: circumference - completedDash }}
            transition={{ duration: 1.5, ease: "easeOut" }}
            style={{ transformOrigin: '50px 50px', transform: `rotate(${(stats.failed / stats.total) * 360}deg)` }}
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center">
          {tip ? (
            <span className="max-w-[7rem] text-center text-xs font-semibold text-ink">{tip}</span>
          ) : (
            <>
              <span className="font-display text-3xl font-black text-ink">{stats.percent}%</span>
              <span className="text-xs text-ink-soft">Completed</span>
            </>
          )}
        </div>
      </div>
      
      {/* Legend doubles as a tooltip trigger — hover a segment label to see its
          absolute count in the donut center. */}
      <div className="mt-4 flex w-full justify-around text-xs font-medium text-ink-soft">
        <div
          className="flex cursor-default items-center gap-1.5"
          onMouseEnter={() => setTip(`${stats.completed} completed`)}
          onMouseLeave={() => setTip(null)}
        >
          <span className="h-2.5 w-2.5 rounded-full bg-indigo-600"></span> Completed
        </div>
        <div
          className="flex cursor-default items-center gap-1.5"
          onMouseEnter={() => setTip(`${stats.processing} processing`)}
          onMouseLeave={() => setTip(null)}
        >
          <span className="h-2.5 w-2.5 rounded-full bg-ink/20"></span> Processing
        </div>
        {stats.failed > 0 && (
          <div
            className="flex cursor-default items-center gap-1.5"
            onMouseEnter={() => setTip(`${stats.failed} failed`)}
            onMouseLeave={() => setTip(null)}
          >
            <span className="h-2.5 w-2.5 rounded-full bg-rose-500"></span> Failed
          </div>
        )}
      </div>
    </div>
  );
}

export function MiniCalendar({ data = [] }: { data: CurriculumSummary[] }) {
  // Simple current month calendar
  const today = new Date();
  const currentMonth = today.toLocaleString("default", { month: "long" });
  const currentYear = today.getFullYear();
  
  // Get active days from data
  const activeDays = useMemo(() => {
    const days = new Set<number>();
    data.forEach(item => {
      if (item.created_at) {
        const d = new Date(item.created_at);
        if (d.getMonth() === today.getMonth() && d.getFullYear() === today.getFullYear()) {
          days.add(d.getDate());
        }
      }
    });
    return days;
  }, [data, today]);

  // Just render 35 slots for a generic calendar view
  const daysInMonth = new Date(currentYear, today.getMonth() + 1, 0).getDate();
  const startDay = new Date(currentYear, today.getMonth(), 1).getDay();
  
  const cells = [];
  for (let i = 0; i < 35; i++) {
    const dateNum = i - startDay + 1;
    const isCurrentMonth = dateNum > 0 && dateNum <= daysInMonth;
    const isToday = isCurrentMonth && dateNum === today.getDate();
    const isActive = activeDays.has(dateNum);
    
    cells.push({
      id: i,
      num: isCurrentMonth ? dateNum : "",
      isToday,
      isActive
    });
  }

  return (
    <div className="w-full">
      <div className="mb-4 flex items-center justify-between">
        <h4 className="font-semibold text-ink">{currentMonth} {currentYear}</h4>
        <div className="flex gap-1">
          <button className="flex h-6 w-6 items-center justify-center rounded-full bg-ink/5 hover:bg-ink/10">{"<"}</button>
          <button className="flex h-6 w-6 items-center justify-center rounded-full bg-ink/5 hover:bg-ink/10">{">"}</button>
        </div>
      </div>
      
      <div className="grid grid-cols-7 gap-1 text-center text-xs">
        {["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].map(day => (
          <div key={day} className="font-medium text-ink-soft pb-2">{day}</div>
        ))}
        
        {cells.map(cell => (
          <div key={cell.id} className="flex h-8 items-center justify-center">
            {cell.num && (
              <span className={`flex h-7 w-7 items-center justify-center rounded-full ${
                cell.isToday ? "bg-indigo-600 text-white font-bold" : 
                cell.isActive ? "bg-indigo-100 text-indigo-700 font-semibold" : 
                "text-ink hover:bg-ink/5"
              }`}>
                {cell.num}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
