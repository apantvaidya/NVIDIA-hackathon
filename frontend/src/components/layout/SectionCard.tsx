import type { ReactNode } from "react";

export function SectionCard({ title, subtitle, children, className = "" }: { title?: string; subtitle?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border border-line bg-panel/95 p-4 shadow-xl shadow-black/20 ${className}`}>
      {(title || subtitle) && (
        <header className="mb-4">
          {title && <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-100">{title}</h2>}
          {subtitle && <p className="mt-1 text-xs text-slate-400">{subtitle}</p>}
        </header>
      )}
      {children}
    </section>
  );
}
