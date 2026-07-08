"use client";

import { useEffect, useState } from "react";

export function useTypewriterCycle(
  strings: string[],
  typeSpeed = 30,
  holdMs = 1800,
  fadeMs = 300
) {
  const [displayText, setDisplayText] = useState("");
  const [opacity, setOpacity] = useState(1);
  const [stringIndex, setStringIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let typeTimer: ReturnType<typeof setTimeout>;
    let holdTimer: ReturnType<typeof setTimeout>;
    let fadeTimer: ReturnType<typeof setTimeout>;
    let nextTimer: ReturnType<typeof setTimeout>;

    const current = strings[stringIndex];

    const typeNext = (charIndex: number) => {
      if (cancelled) return;
      if (charIndex <= current.length) {
        setDisplayText(current.slice(0, charIndex));
        typeTimer = setTimeout(() => typeNext(charIndex + 1), typeSpeed);
      } else {
        holdTimer = setTimeout(() => {
          if (cancelled) return;
          setOpacity(0);
          fadeTimer = setTimeout(() => {
            if (cancelled) return;
            setStringIndex((prev) => (prev + 1) % strings.length);
            setDisplayText("");
            setOpacity(1);
          }, fadeMs);
        }, holdMs);
      }
    };

    typeNext(0);

    return () => {
      cancelled = true;
      clearTimeout(typeTimer);
      clearTimeout(holdTimer);
      clearTimeout(fadeTimer);
      clearTimeout(nextTimer);
    };
  }, [stringIndex, strings, typeSpeed, holdMs, fadeMs]);

  return { displayText, opacity };
}
