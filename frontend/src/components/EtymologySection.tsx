import React from 'react';
import { colors, fonts } from '../styles/theme';
import { useResponsive } from '../hooks/useMediaQuery';

export const EtymologySection: React.FC = () => {
  const { isMobile } = useResponsive();
  return (
    <section id="about" style={{
      position:'relative',background:colors.midnightDeep,padding: isMobile ? '60px 16px' : '120px 24px',
      display:'flex',justifyContent:'center',overflow:'hidden',
    }}>
      <style>{`
        @keyframes etymFadeUp {
          0%{opacity:0;transform:translateY(30px)}
          100%{opacity:1;transform:translateY(0)}
        }
        @keyframes dividerGrow {
          0%{width:0;opacity:0}
          100%{width:120px;opacity:1}
        }
        @keyframes wordSlideLeft {
          0%{opacity:0;transform:translateX(-40px)}
          100%{opacity:1;transform:translateX(0)}
        }
        @keyframes wordSlideRight {
          0%{opacity:0;transform:translateX(40px)}
          100%{opacity:1;transform:translateX(0)}
        }
        @keyframes plusRotate {
          0%{opacity:0;transform:rotate(-90deg) scale(0.5)}
          100%{opacity:0.6;transform:rotate(0) scale(1)}
        }
        @keyframes ambientOrb {
          0%,100%{transform:translate(-50%,-50%) scale(1);opacity:0.04}
          50%{transform:translate(-50%,-50%) scale(1.3);opacity:0.08}
        }
      `}</style>

      <div style={{
        position:'absolute',top:'50%',left:'50%',width:500,height:300,borderRadius:'50%',
        background:`radial-gradient(ellipse,${colors.warmGold}08 0%,transparent 70%)`,
        animation:'ambientOrb 8s ease-in-out infinite',transform:'translate(-50%,-50%)',pointerEvents:'none',
      }}/>

      <div style={{maxWidth:700,textAlign:'center',position:'relative',zIndex:1}}>
        <h2 style={{
          fontFamily:fonts.heading,fontSize: isMobile ? 32 : 48,fontWeight:600,fontStyle:'italic',color:colors.warmGold,
          marginBottom:8,animation:'etymFadeUp 0.8s ease-out forwards',
          textShadow:`0 0 40px ${colors.warmGold}15`,
        }}>M&aring;ngata</h2>

        <p style={{
          fontFamily:fonts.body,fontSize:16,color:colors.coldSilverBlue,marginBottom:40,
          fontWeight:300,letterSpacing:'0.05em',
          animation:'etymFadeUp 0.8s ease-out 0.2s forwards',opacity:0,
        }}>/&#x02C8;m&#x0254;&#x014B;&#x0251;&#x02D0;ta/ &#x2014; Swedish</p>

        <div style={{
          height:1,
          background:`linear-gradient(90deg,transparent,${colors.warmGold}60,transparent)`,
          margin:'0 auto 48px',animation:'dividerGrow 1s ease-out 0.4s forwards',width:0,opacity:0,
        }}/>

        <div style={{display:'flex',alignItems:'center',justifyContent:'center',gap: isMobile ? 24 : 48,marginBottom:48}}>
          <div style={{animation:'wordSlideLeft 0.7s ease-out 0.6s forwards',opacity:0}}>
            <div style={{fontFamily:fonts.heading,fontSize: isMobile ? 22 : 32,color:colors.moonlightSilver,marginBottom:8,textShadow:`0 0 20px ${colors.moonlightSilver}10`}}>M&aring;ne</div>
            <div style={{fontFamily:fonts.body,fontSize:14,color:colors.coldSilverBlue,fontWeight:300,letterSpacing:'0.15em'}}>MOON</div>
          </div>
          <div style={{fontFamily:fonts.heading,fontSize:32,color:colors.warmGold,animation:'plusRotate 0.5s ease-out 0.8s forwards',opacity:0}}>+</div>
          <div style={{animation:'wordSlideRight 0.7s ease-out 0.6s forwards',opacity:0}}>
            <div style={{fontFamily:fonts.heading,fontSize: isMobile ? 22 : 32,color:colors.moonlightSilver,marginBottom:8,textShadow:`0 0 20px ${colors.moonlightSilver}10`}}>Gata</div>
            <div style={{fontFamily:fonts.body,fontSize:14,color:colors.coldSilverBlue,fontWeight:300,letterSpacing:'0.15em'}}>PATH</div>
          </div>
        </div>

        <div style={{marginBottom:32,animation:'etymFadeUp 0.6s ease-out 1s forwards',opacity:0}}>
          <svg width="40" height="40" viewBox="0 0 40 40" style={{opacity:0.25}}>
            <circle cx="20" cy="20" r="15" fill="none" stroke={colors.warmGold} strokeWidth="0.5"/>
            <circle cx="20" cy="20" r="8" fill="none" stroke={colors.warmGold} strokeWidth="0.3" opacity="0.5"/>
            <circle cx="20" cy="20" r="2" fill={colors.warmGold} opacity="0.6"/>
          </svg>
        </div>

        <p style={{
          fontFamily:fonts.heading,fontSize:18,fontStyle:'italic',color:colors.moonlightSilver,lineHeight:1.8,
          marginBottom:24,opacity:0,animation:'etymFadeUp 0.8s ease-out 1.1s forwards',
        }}>
          The shimmering road of moonlight that stretches across calm water,<br/>a path that seems to lead to the moon itself.
        </p>

        <p style={{
          fontFamily:fonts.body,fontSize:15,fontStyle:'italic',color:colors.coldSilverBlue,lineHeight:1.8,
          fontWeight:300,opacity:0,animation:'etymFadeUp 0.8s ease-out 1.3s forwards',
        }}>
          &#x6708;&#x5149;&#x6D12;&#x5728;&#x6C34;&#x9762;&#x4E0A;&#xFF0C;&#x968F;&#x6CE2;&#x5149;&#x8D77;&#x4F0F;&#xFF0C;&#x5F62;&#x6210;&#x4E00;&#x6761;&#x4EFF;&#x4F5B;&#x901A;&#x5F80;&#x6708;&#x4EAE;&#x7684;&#x9053;&#x8DEF;&#x3002;
        </p>
      </div>
    </section>
  );
};
