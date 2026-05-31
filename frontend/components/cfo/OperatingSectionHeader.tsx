export function OperatingSectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div style={{ marginBottom: 4 }}>
      <h2 className="os-slide-title">{title}</h2>
      {subtitle && <p className="os-slide-sub">{subtitle}</p>}
    </div>
  );
}
