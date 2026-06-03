import { SectionReveal } from "../motion";
import { DataHubDiagram } from "../visuals/DataHubDiagram";

export function DataSourceOrbit() {
  return (
    <section id="sources" className="border-y border-white/10 bg-slate-950 px-6 py-20 md:py-24">
      <div className="mx-auto max-w-7xl">
        <SectionReveal className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-semibold uppercase tracking-widest text-teal-400">
            Unified data layer
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-5xl">
            Every system feeds one intelligent model.
          </h2>
          <p className="mt-4 text-lg leading-relaxed text-slate-400">
            CRM, ERP, billing, HRIS, spreadsheets, and warehouse data flow into SMPL — governed,
            reconciled, and ready for executive decisions.
          </p>
        </SectionReveal>

        <DataHubDiagram />
      </div>
    </section>
  );
}
