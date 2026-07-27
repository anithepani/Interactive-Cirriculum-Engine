import Hero from "@/components/sections/Hero";
import InstructorSpotlight from "@/components/sections/InstructorSpotlight";
import LogoMarquee from "@/components/sections/LogoMarquee";
import ValuePropositionFan from "@/components/sections/ValuePropositionFan";
import VisionSplitGrid from "@/components/sections/VisionSplitGrid";
import LearnerMatrix from "@/components/sections/LearnerMatrix";
import FeatureMosaic from "@/components/sections/FeatureMosaic";
import MarketplaceCarousel from "@/components/sections/MarketplaceCarousel";
import ComponentGridMatrix from "@/components/sections/ComponentGridMatrix";
import PricingNodes from "@/components/sections/PricingNodes";
import NeonMarqueeBelt from "@/components/sections/NeonMarqueeBelt";
import DualCTABlocks from "@/components/sections/DualCTABlocks";

export default function HomePage() {
  return (
    <>
      <Hero />
      <InstructorSpotlight />
      <LogoMarquee />
      <ValuePropositionFan />
      <VisionSplitGrid />
      <LearnerMatrix />
      <FeatureMosaic />
      <MarketplaceCarousel />
      <PricingNodes />
      <ComponentGridMatrix />
      <NeonMarqueeBelt />
      <DualCTABlocks />
    </>
  );
}
