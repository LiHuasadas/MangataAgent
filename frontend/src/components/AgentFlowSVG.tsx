import React from 'react';
import { colors } from '../styles/theme';

interface AgentNode { name:string; icon:string; role:string; cx:number; cy:number; delay:number; }

const agents: AgentNode[] = [
  { name:'Simple',   icon:'\u26A1', role:'Quick Responder',  cx:12, cy:22, delay:0.0 },
  { name:'Planner',  icon:'\uD83D\uDDFA\uFE0F', role:'Technical Scout', cx:30, cy:18, delay:0.3 },
  { name:'Host',     icon:'\uD83C\uDF1F', role:'Orchestrator',    cx:50, cy:14, delay:0.6 },
  { name:'Builder',  icon:'\uD83D\uDEE0\uFE0F', role:'Code Artisan',    cx:70, cy:18, delay:0.9 },
  { name:'Reviewer', icon:'\uD83D\uDD0D', role:'Quality Guard',   cx:88, cy:22, delay:1.2 },
];

export const AgentFlowSVG: React.FC = () => {
  const cX = 50, cY = 82;
  return (
    <div style={{
      position:'relative',width:'100%',aspectRatio:'960/540',
      background:colors.midnightDeep,borderRadius:16,overflow:'hidden',
      border:`1px solid ${colors.warmGold}15`,boxShadow:'0 8px 48px rgba(0,0,0,0.4)',
    }}>
      <style>{`
        @keyframes agentAppear {
          0%{opacity:0;transform:scale(0.3) translateY(20px)}
          60%{opacity:1;transform:scale(1.05) translateY(-3px)}
          100%{opacity:1;transform:scale(1) translateY(0)}
        }
        @keyframes threadDraw {
          0%{stroke-dashoffset:300;opacity:0}
          20%{opacity:0.6}
          100%{stroke-dashoffset:0;opacity:0.6}
        }
        @keyframes convergePulse {
          0%,100%{r:6;opacity:0.7}
          50%{r:10;opacity:1}
        }
        @keyframes labelFade {
          0%{opacity:0;transform:translateY(8px)}
          100%{opacity:1;transform:translateY(0)}
        }
        @keyframes cardGlow {
          0%,100%{box-shadow:0 4px 20px rgba(0,0,0,0.3),inset 0 1px 0 rgba(201,214,227,0.05)}
          50%{box-shadow:0 4px 28px rgba(212,175,122,0.15),inset 0 1px 0 rgba(201,214,227,0.1)}
        }
        @keyframes particleDrift {
          0%,100%{transform:translateY(0) scale(1);opacity:0.4}
          50%{transform:translateY(-12px) scale(1.3);opacity:0.8}
        }
        .agent-card {
          animation:agentAppear 0.8s cubic-bezier(0.34,1.56,0.64,1) forwards,cardGlow 4s ease-in-out infinite;
          opacity:0;
        }
        .thread-line { stroke-dasharray:300; animation:threadDraw 1.5s ease-out forwards; }
      `}</style>

      {Array.from({length:20},(_,i)=>{
        const s1=((i*7919)%997)/997, s2=((i*6271)%991)/991;
        return <div key={i} style={{
          position:'absolute',left:`${s1*100}%`,top:`${s2*100}%`,
          width:2,height:2,borderRadius:'50%',
          backgroundColor:i%2===0?colors.warmGold:colors.moonlightSilver,
          animation:`particleDrift ${3+(i%4)}s ease-in-out infinite`,
          animationDelay:`${i*0.5}s`,opacity:0.3,
        }}/>;
      })}

      <svg style={{position:'absolute',inset:0,width:'100%',height:'100%'}}>
        <defs>
          {agents.map((_,i)=>(
            <linearGradient key={i} id={`tg-${i}`} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={colors.warmGold} stopOpacity={0.7}/>
              <stop offset="100%" stopColor={colors.moonlightSilver} stopOpacity={0.15}/>
            </linearGradient>
          ))}
          <radialGradient id="cg">
            <stop offset="0%" stopColor={colors.warmGold} stopOpacity={0.9}/>
            <stop offset="50%" stopColor={colors.pearlWhite} stopOpacity={0.4}/>
            <stop offset="100%" stopColor={colors.warmGold} stopOpacity={0}/>
          </radialGradient>
        </defs>
        {agents.map((a,i)=>(
          <line key={i} className="thread-line"
            x1={`${a.cx}%`} y1={`${a.cy+12}%`} x2={`${cX}%`} y2={`${cY}%`}
            stroke={`url(#tg-${i})`} strokeWidth={1.5}
            style={{animationDelay:`${a.delay+1}s`}}/>
        ))}
        <circle cx={`${cX}%`} cy={`${cY}%`} r={6} fill="url(#cg)"
          style={{animation:'convergePulse 3s ease-in-out infinite 2.5s'}}/>
        <circle cx={`${cX}%`} cy={`${cY}%`} r={18}
          fill="none" stroke={colors.warmGold} strokeWidth={0.5} opacity={0.2}
          style={{animation:'convergePulse 4s ease-in-out infinite 2.8s'}}/>
      </svg>

      <div style={{position:'absolute',top:'3%',width:'100%',textAlign:'center',animation:'labelFade 0.8s ease-out forwards'}}>
        <h3 style={{fontFamily:"'Playfair Display',serif",fontSize:22,color:colors.moonlightSilver,margin:0,fontWeight:600}}>Multi-Agent Orchestration</h3>
        <p style={{fontFamily:"'Inter',sans-serif",fontSize:12,color:colors.coldSilverBlue,fontWeight:300,marginTop:4,letterSpacing:'0.06em'}}>Five specialized agents, one moonlit path</p>
      </div>

      {agents.map((a)=>(
        <div key={a.name} className="agent-card" style={{
          animationDelay:`${a.delay}s, ${a.delay+0.8}s`,
          position:'absolute',left:`${a.cx}%`,top:`${a.cy}%`,transform:'translate(-50%,0)',
          width:110,padding:'14px 10px',
          background:'rgba(27,42,74,0.45)',backdropFilter:'blur(12px)',WebkitBackdropFilter:'blur(12px)',
          border:'1px solid rgba(212,175,122,0.18)',borderRadius:10,textAlign:'center',
        }}>
          <div style={{fontSize:24,marginBottom:6}}>{a.icon}</div>
          <div style={{fontFamily:"'Playfair Display',serif",fontSize:13,color:colors.moonlightSilver,marginBottom:3,fontWeight:600}}>{a.name}</div>
          <div style={{fontFamily:"'Inter',sans-serif",fontSize:10,color:colors.coldSilverBlue,fontWeight:300}}>{a.role}</div>
        </div>
      ))}

      <div style={{
        position:'absolute',left:`${cX}%`,top:`${cY+5}%`,transform:'translateX(-50%)',textAlign:'center',
        animation:'labelFade 0.6s ease-out 3s forwards',opacity:0,
      }}>
        <div style={{fontFamily:"'Inter',sans-serif",fontSize:11,color:colors.warmGold,fontWeight:500,letterSpacing:'0.15em'}}>DELIVERABLE</div>
      </div>
    </div>
  );
};
