import React from 'react';
import { colors, fonts } from '../styles/theme';

export const CtaSection: React.FC = () => {
  return (
    <section style={{
      position:'relative',background:colors.midnightDeep,padding:'140px 24px',textAlign:'center',overflow:'hidden',
    }}>
      <style>{`
        @keyframes ctaOrbFloat {
          0%,100%{transform:translate(-50%,-50%) scale(1);opacity:0.06}
          50%{transform:translate(-50%,-50%) scale(1.4);opacity:0.12}
        }
        @keyframes ctaSparkle {
          0%,100%{opacity:0;transform:scale(0.5)}
          50%{opacity:0.6;transform:scale(1)}
        }
        .cta-btn-primary{transition:transform 0.3s ease,box-shadow 0.3s ease}
        .cta-btn-primary:hover{transform:translateY(-2px) scale(1.03)!important;box-shadow:0 6px 40px rgba(212,175,122,0.4),0 0 80px rgba(212,175,122,0.15)!important}
        .cta-btn-ghost{transition:transform 0.3s ease,border-color 0.3s ease,background 0.3s ease}
        .cta-btn-ghost:hover{transform:translateY(-2px)!important;border-color:rgba(212,175,122,0.6)!important;background:rgba(212,175,122,0.05)!important}
      `}</style>

      <div style={{
        position:'absolute',top:'50%',left:'50%',width:600,height:300,borderRadius:'50%',
        background:`radial-gradient(ellipse at center,${colors.warmGold}0A 0%,transparent 70%)`,
        animation:'ctaOrbFloat 10s ease-in-out infinite',pointerEvents:'none',
      }}/>
      <div style={{
        position:'absolute',top:'30%',left:'30%',width:200,height:200,borderRadius:'50%',
        background:`radial-gradient(circle,${colors.moonlightSilver}04 0%,transparent 70%)`,
        animation:'ctaOrbFloat 12s ease-in-out 2s infinite',pointerEvents:'none',
      }}/>

      {Array.from({length:12},(_,i)=>{
        const s=((i*7919)%997)/997, s2=((i*6271)%991)/991;
        return <div key={i} style={{
          position:'absolute',left:`${10+s*80}%`,top:`${10+s2*80}%`,
          width:2,height:2,borderRadius:'50%',
          backgroundColor:i%2===0?colors.warmGold:colors.moonlightSilver,
          animation:`ctaSparkle ${4+(i%3)*2}s ease-in-out infinite`,
          animationDelay:`${i*0.8}s`,
        }}/>;
      })}

      <div style={{position:'relative',zIndex:1}}>
        <h2 style={{
          fontFamily:fonts.heading,fontSize:40,fontWeight:600,color:colors.moonlightSilver,marginBottom:16,
          textShadow:`0 0 40px ${colors.warmGold}12`,
        }}>Let Moonlight Guide Your Code</h2>
        <p style={{fontFamily:fonts.body,fontSize:18,fontWeight:300,color:colors.coldSilverBlue,marginBottom:48}}>
          Start building with MangataAgent today.
        </p>
        <div style={{display:'flex',gap:20,justifyContent:'center'}}>
          <button className="cta-btn-primary" style={{
            fontFamily:fonts.body,fontSize:15,fontWeight:500,color:colors.midnightDeep,
            background:`linear-gradient(135deg,${colors.warmGold},${colors.pearlWhite})`,
            border:'none',borderRadius:28,padding:'14px 40px',cursor:'pointer',
            letterSpacing:'0.04em',boxShadow:`0 4px 30px ${colors.warmGold}30`,
          }}>Start Free</button>
          <button className="cta-btn-ghost" style={{
            fontFamily:fonts.body,fontSize:15,fontWeight:500,color:colors.warmGold,
            background:'transparent',border:`1px solid ${colors.warmGold}50`,
            borderRadius:28,padding:'14px 40px',cursor:'pointer',letterSpacing:'0.04em',
          }}>View Documentation</button>
        </div>
      </div>
    </section>
  );
};
