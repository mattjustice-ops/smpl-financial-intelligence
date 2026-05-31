export function CommentaryPanel({
  label = "Executive takeaway",
  text,
  variant = "default",
}: {
  label?: string;
  text: string;
  variant?: "default" | "risk";
}) {
  if (!text.trim()) return null;
  return (
    <div className={`os-commentary${variant === "risk" ? " risk" : ""}`}>
      <div className="os-commentary-label">{label}</div>
      <div className="os-commentary-text">{text}</div>
    </div>
  );
}
