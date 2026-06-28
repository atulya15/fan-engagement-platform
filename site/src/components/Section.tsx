import { ReactNode } from "react";

export function Section({
  id,
  eyebrow,
  title,
  insight,
  children,
}: {
  id: string;
  eyebrow: string;
  title: string;
  insight?: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="mx-auto w-full max-w-5xl px-6 py-24 sm:py-32">
      <div className="mb-12">
        <p className="num text-xs font-medium uppercase tracking-[0.2em] text-accent">
          {eyebrow}
        </p>
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
          {title}
        </h2>
        {insight && (
          <p className="mt-4 max-w-2xl text-base leading-relaxed text-muted">
            {insight}
          </p>
        )}
      </div>
      {children}
    </section>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-2xl border border-hairline bg-surface p-6 backdrop-blur-sm ${className}`}
    >
      {children}
    </div>
  );
}
