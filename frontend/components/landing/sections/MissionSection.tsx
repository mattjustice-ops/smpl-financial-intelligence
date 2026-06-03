import { SectionReveal } from "../motion";

export function MissionSection() {
  return (
    <section id="mission" className="relative overflow-hidden bg-white px-6 py-28 text-slate-950">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_100%,rgba(45,212,191,0.12),transparent)]" />
      <div className="relative mx-auto max-w-4xl text-center">
        <SectionReveal>
          <p className="text-sm font-semibold uppercase tracking-widest text-teal-600">Our mission</p>
          <blockquote className="mt-6 text-3xl font-semibold leading-tight tracking-tight md:text-4xl lg:text-5xl">
            We believe finance teams should spend less time assembling reports and more time shaping
            the future of the business.
          </blockquote>
          <p className="mx-auto mt-8 max-w-2xl text-lg leading-relaxed text-slate-600">
            SMPL gives SaaS operators the financial intelligence layer they need to make better
            decisions, faster — with the rigor of a world-class CFO team behind every metric.
          </p>
        </SectionReveal>
      </div>
    </section>
  );
}
