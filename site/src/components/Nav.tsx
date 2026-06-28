"use client";

const LINKS = [
  { href: "#retention", label: "Retention" },
  { href: "#funnels", label: "Funnels" },
  { href: "#growth", label: "Growth" },
  { href: "#experiment", label: "Experiments" },
  { href: "#recommendations", label: "Recommendations" },
];

const DASHBOARD_URL =
  process.env.NEXT_PUBLIC_DASHBOARD_URL ?? "https://github.com/atulya15/-fan-engagement-platform";
const REPO_URL = "https://github.com/atulya15/-fan-engagement-platform";

export function Nav() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-hairline bg-base/70 backdrop-blur-md">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <span className="text-sm font-semibold text-foreground">
          Fan Engagement Platform
        </span>
        <nav className="hidden items-center gap-6 text-sm text-muted sm:flex">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="cursor-pointer transition-colors hover:text-foreground"
            >
              {l.label}
            </a>
          ))}
        </nav>
        <div className="flex items-center gap-3 text-sm">
          <a
            href={DASHBOARD_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden cursor-pointer text-muted transition-colors hover:text-foreground sm:inline"
          >
            Full dashboard
          </a>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="cursor-pointer rounded-lg border border-hairline px-3 py-1.5 text-foreground transition-colors hover:bg-surface-hover"
          >
            GitHub
          </a>
        </div>
      </div>
    </header>
  );
}
