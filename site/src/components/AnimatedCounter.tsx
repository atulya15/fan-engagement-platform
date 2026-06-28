"use client";

import { useEffect, useRef, useState } from "react";
import { useInView, animate } from "framer-motion";

export function AnimatedCounter({
  value,
  format = (v: number) => Math.round(v).toLocaleString("en-US"),
  durationMs = 1400,
  className = "",
}: {
  value: number;
  format?: (v: number) => string;
  durationMs?: number;
  className?: string;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true, margin: "-10% 0px" });
  const [display, setDisplay] = useState("0");

  useEffect(() => {
    if (!inView) return;
    const controls = animate(0, value, {
      duration: durationMs / 1000,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => setDisplay(format(v)),
    });
    return () => controls.stop();
  }, [inView, value, durationMs, format]);

  return (
    <span ref={ref} className={`num ${className}`}>
      {display}
    </span>
  );
}
