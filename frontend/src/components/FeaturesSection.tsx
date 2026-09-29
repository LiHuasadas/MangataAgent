import React from 'react';
import { AgentFlowSVG } from './AgentFlowSVG';
import { colors, fonts } from '../styles/theme';
import { useResponsive } from '../hooks/useMediaQuery';

const features = [
  { icon:'\u26A1', title:'\u667A\u80FD\u5206\u5DE5', titleEn:'Intelligent Division', description:'Five specialized agents work in concert, each bringing unique expertise to your codebase.' },
  { icon:'\uD83C\uDF19', title:'\u6708\u5149\u8DEF\u5F84', titleEn:'Moonlit Path', description:'From plan to code to review, a clear illuminated path guides every step of development.' },
  { icon:'\uD83D\uDEE1\uFE0F', title:'\u5B89\u5168\u62A4\u680F', titleEn:'Safety Rails', description:'Built-in Jev guardrails ensure safe command execution and intelligent memory management.' },
];

export const FeaturesSection: React.FC = () => {
  const { isMobile } = useResponsive();
  return (
    <section id="features" style={{
      background:`linear-gradient(180deg,${colors.midnightDeep} 0%,${colors.midnightMid}40 50%,${colors.midnightDeep} 100%)`,
      padding: isMobile ? '60px 16px' : '100px 24px',
    }}>
      <div style={{maxWidth:960,margin:'0 auto 80px'}}><AgentFlowSVG/></div>

      <div style={{maxWidth:1100,margin:'0 auto',display:'grid',gridTemplateColumns: isMobile ? '1fr' : 'repeat(3,1fr)',gap:32}}>
        {features.map(f=>(
          <div key={f.titleEn} style={{
            background:'rgba(27,42,74,0.3)',backdropFilter:'blur(8px)',WebkitBackdropFilter:'blur(8px)',
            borderRadius:12,padding:'32px 28px',border:`1px solid ${colors.warmGold}10`,
            borderLeft:`3px solid ${colors.warmGold}50`,
            transition:'transform 0.35s ease, border-color 0.35s ease, box-shadow 0.35s ease',
            cursor:'default',
          }}
            onMouseEnter={e=>{const el=e.currentTarget;el.style.transform='translateY(-4px)';el.style.borderColor=`${colors.warmGold}40`;el.style.boxShadow='0 8px 40px rgba(212,175,122,0.08)'}}
            onMouseLeave={e=>{const el=e.currentTarget;el.style.transform='translateY(0)';el.style.borderColor=`${colors.warmGold}10`;el.style.boxShadow='none'}}
          >
            <div style={{fontSize:32,marginBottom:16}}>{f.icon}</div>
            <h3 style={{fontFamily:fonts.heading,fontSize:22,color:colors.moonlightSilver,marginBottom:4}}>{f.title}</h3>
            <p style={{fontFamily:fonts.body,fontSize:13,color:colors.warmGold,fontWeight:400,marginBottom:12,letterSpacing:'0.05em'}}>{f.titleEn}</p>
            <p style={{fontFamily:fonts.body,fontSize:15,color:colors.coldSilverBlue,fontWeight:300,lineHeight:1.7}}>{f.description}</p>
          </div>
        ))}
      </div>
    </section>
  );
};
