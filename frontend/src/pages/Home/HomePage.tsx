import React from 'react';
import { HeroSection } from '../../components/HeroSection';
import { EtymologySection } from '../../components/EtymologySection';
import { FeaturesSection } from '../../components/FeaturesSection';
import { CtaSection } from '../../components/CtaSection';

export const HomePage: React.FC = () => {
  return (
    <div>
      <HeroSection />
      <EtymologySection />
      <FeaturesSection />
      <CtaSection />
    </div>
  );
};
