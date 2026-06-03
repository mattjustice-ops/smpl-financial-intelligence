import { LandingFooter } from "./LandingFooter";
import { LandingHeader } from "./LandingHeader";
import { AiCopilotSection } from "./sections/AiCopilotSection";
import { BeforeAfterSection } from "./sections/BeforeAfterSection";
import { DataSourceOrbit } from "./sections/DataSourceOrbit";
import { FinalCtaSection } from "./sections/FinalCtaSection";
import { HeroSection } from "./sections/HeroSection";
import { MissionSection } from "./sections/MissionSection";
import { OperatingModelSection } from "./sections/OperatingModelSection";
import { ProductModulesSection } from "./sections/ProductModulesSection";
import { TaskSelectorSection } from "./sections/TaskSelectorSection";
import { TrustSection } from "./sections/TrustSection";

/** Server page shell — only interactive slices are client components. */
export function SmplAiLandingPage() {
  return (
    <div className="min-h-screen">
      <LandingHeader />
      <main>
        <HeroSection />
        <DataSourceOrbit />
        <OperatingModelSection />
        <TaskSelectorSection />
        <ProductModulesSection />
        <BeforeAfterSection />
        <AiCopilotSection />
        <TrustSection />
        <MissionSection />
        <FinalCtaSection />
      </main>
      <LandingFooter />
    </div>
  );
}
