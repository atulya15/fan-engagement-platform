"use client";

import { motion } from "framer-motion";
import { AnimatedCounter } from "./AnimatedCounter";
import type { Hero as HeroData } from "@/lib/snapshot";

export function Hero({ hero }: { hero: HeroData }) {
  return (
    <section className="relative mx-auto flex w-full max-w-5xl flex-col items-start px-6 pt-32 pb-20 sm:pt-44 sm:pb-28">
      <motion.p
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="num text-xs font-medium uppercase tracking-[0.2em] text-accent"
      >
        Product Analytics Platform
      </motion.p>

      <motion.h1
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
        className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight text-foreground sm:text-6xl"
      >
        Fan Engagement Platform
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
        className="mt-5 max-w-xl text-lg leading-relaxed text-muted"
      >
        A simulated LiveLike-style sports & media gamification product —
        polls, trivia, predictions, leaderboards — instrumented end-to-end
        with retention analysis, A/B experimentation, and a hybrid
        recommendation engine.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
        className="mt-14 grid w-full grid-cols-2 gap-6 border-t border-hairline pt-10 sm:grid-cols-4"
      >
        <Stat
          value={hero.total_users}
          label="Simulated users"
        />
        <Stat
          value={hero.total_events}
          label="Widget events"
        />
        <Stat
          value={hero.simulation_months}
          label="Months simulated"
          suffix=""
        />
        <Stat
          value={hero.avg_stickiness_30d * 100}
          label="DAU/MAU stickiness"
          decimals={1}
          suffix="%"
        />
      </motion.div>
    </section>
  );
}

function Stat({
  value,
  label,
  decimals = 0,
  suffix = "",
}: {
  value: number;
  label: string;
  decimals?: number;
  suffix?: string;
}) {
  return (
    <div>
      <div className="text-3xl font-semibold text-foreground sm:text-4xl">
        <AnimatedCounter
          value={value}
          format={(v) =>
            `${v.toLocaleString("en-US", {
              minimumFractionDigits: decimals,
              maximumFractionDigits: decimals,
            })}${suffix}`
          }
        />
      </div>
      <div className="mt-1 text-sm text-muted">{label}</div>
    </div>
  );
}
