"use client";

type MiniSparklineProps = {
  points: number[];
  color?: string;
  className?: string;
};

export function MiniSparkline({
  points,
  color = "#2dd4bf",
  className = "",
}: MiniSparklineProps) {
  const w = 64;
  const h = 28;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const step = w / (points.length - 1);

  const d = points
    .map((p, i) => {
      const x = i * step;
      const y = h - ((p - min) / range) * (h - 4) - 2;
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      className={`h-7 w-16 shrink-0 opacity-80 ${className}`}
      aria-hidden
    >
      <path d={d} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
