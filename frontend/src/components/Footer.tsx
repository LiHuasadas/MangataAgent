import React from 'react';
import { colors, fonts } from '../styles/theme';

export const Footer: React.FC = () => {
  return (
    <footer style={{
      background:colors.midnightDeep,borderTop:`1px solid ${colors.warmGold}15`,padding:'48px 48px 32px',
    }}>
      <div style={{maxWidth:1100,margin:'0 auto',display:'flex',justifyContent:'space-between',alignItems:'flex-start'}}>
        <div>
          <div style={{fontFamily:fonts.heading,fontSize:18,color:colors.warmGold,marginBottom:8}}>MangataAgent</div>
          <div style={{fontFamily:fonts.body,fontSize:12,color:colors.coldSilverBlue,fontWeight:300}}>&copy; 2024 MangataAgent</div>
        </div>
        <div style={{display:'flex',gap:32}}>
          {['GitHub','Documentation','API Reference'].map(link=>(
            <a key={link} href="#" style={{fontFamily:fonts.body,fontSize:13,color:colors.coldSilverBlue,fontWeight:300,textDecoration:'none',transition:'color 0.3s ease'}}
              onMouseEnter={e=>(e.target as HTMLElement).style.color=colors.warmGold}
              onMouseLeave={e=>(e.target as HTMLElement).style.color=colors.coldSilverBlue}
            >{link}</a>
          ))}
        </div>
        <div style={{fontFamily:fonts.body,fontSize:12,color:colors.coldSilverBlue,fontWeight:300,fontStyle:'italic'}}>
          Built with &#x2728; by moonlight
        </div>
      </div>
    </footer>
  );
};
