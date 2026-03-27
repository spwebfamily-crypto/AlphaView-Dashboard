type ModeBadgeProps = {
  mode: string;
};

export function ModeBadge({ mode }: ModeBadgeProps) {
  const normalizedMode = mode.toUpperCase();
  const label = normalizedMode === "PAPER" ? "SIMULATION" : normalizedMode;
  return <span className={`mode-badge mode-${normalizedMode.toLowerCase()}`}>{label}</span>;
}
