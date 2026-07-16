"use client";

import { motion } from "framer-motion";
import type { CurriculumSummary } from "@/lib/types";
import { useMemo } from "react";

export function DashboardAreaChart({ data = [] }: { data: CurriculumSummary[] }) {
  // Group curricula by day of week
  const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
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
            r="5"
            fill="#ffffff"
            stroke="#4f46e5"
            strokeWidth="3"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 1 + i * 0.1, type: "spring" }}
          />
        ))}
      </svg>
      
      {/* X-axis labels and tooltips overlay */}
      <div className="absolute inset-0 flex justify-between">
        {stats.map((stat, i) => (
          <div key={stat.day} className="flex h-full flex-col items-center justify-between" style={{ width: '14.28%' }}>
            {/* Tooltip value */}
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 1 + i * 0.1 }}
              className="mt-2 text-xs font-bold text-indigo-600"
            >
              {stat.count > 0 ? stat.count : ""}
            </motion.div>
            
            {/* X-axis label */}
            <span className="mb-[-1.5rem] text-xs font-medium text-ink-soft">{stat.day}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function DashboardDonutChart({ data = [] }: { data: CurriculumSummary[] }) {
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
  
  return (
    <div className="flex flex-col items-center">
      <div className="relative flex h-40 w-40 items-center justify-center">
        <svg className="h-full w-full -rotate-90 transform" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r={radius} fill="transparent" stroke="currentColor" strokeWidth="12" className="text-ink/5" />
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
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center">
          <span className="font-display text-3xl font-black text-ink">{stats.percent}%</span>
          <span className="text-xs text-ink-soft">Completed</span>
        </div>
      </div>
      
      <div className="mt-4 flex w-full justify-around text-xs font-medium text-ink-soft">
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-indigo-600"></span> Completed
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-ink/20"></span> Processing
        </div>
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
