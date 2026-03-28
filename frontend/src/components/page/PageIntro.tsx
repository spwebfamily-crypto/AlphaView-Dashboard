import type { ReactNode } from "react";

type IntroStat = {
  label: string;
  value: ReactNode;
  note: string;
  tone?: "neutral" | "positive" | "negative" | "accent" | "warning";
};

type PageIntroProps = {
  eyebrow: string;
  title: string;
  description: string;
  stats: IntroStat[];
};

export function PageIntro({ eyebrow, title, description, stats }: PageIntroProps) {
  return (
    <section className="page-intro panel">
      <div className="page-intro-copy">
        <span className="eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>

      <div className="page-intro-stats">
        {stats.map((stat) => (
          <article className={`page-intro-stat tone-${stat.tone ?? "neutral"}`} key={stat.label}>
            <span className="metric-label">{stat.label}</span>
            <strong>{stat.value}</strong>
            <small>{stat.note}</small>
          </article>
        ))}
      </div>
    </section>
  );
}
