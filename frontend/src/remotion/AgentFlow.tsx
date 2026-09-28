import React from 'react';
import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';
import { colors, fonts } from '../styles/theme';

interface AgentCardData {
  name: string;
  icon: string;
  description: string;
  x: number; // percentage position
}

const agents: AgentCardData[] = [
  { name: 'Simple', icon: '✨', description: 'Quick Responder', x: 10 },
  { name: 'Planner', icon: '🗺️', description: 'Technical Scout', x: 28 },
  { name: 'Host', icon: '✦', description: 'Orchestrator', x: 46 },
  { name: 'Builder', icon: '🛠️', description: 'Code Artisan', x: 64 },
  { name: 'Reviewer', icon: '🔍', description: 'Quality Guard', x: 82 },
];

export const AgentFlow: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  const convergenceY = height * 0.85;
  const convergenceX = width * 0.5;

  // Convergence point pulse
  const pulse = Math.sin((frame / fps) * Math.PI * 2) * 0.3 + 0.7;

  return (
    <div style={{
      width: '100%',
      height: '100%',
      background: colors.midnightDeep,
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Title */}
      {(() => {
        const titleOpacity = interpolate(frame, [0, 0.8 * fps], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
        const titleY = interpolate(frame, [0, 0.8 * fps], [30, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
        return (
          <div style={{
            position: 'absolute',
            top: '5%',
            width: '100%',
            textAlign: 'center',
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
          }}>
            <h2 style={{
              fontFamily: fonts.heading,
              fontSize: 36,
              color: colors.moonlightSilver,
              marginBottom: 8,
            }}>Multi-Agent Orchestration</h2>
            <p style={{
              fontFamily: fonts.body,
              fontSize: 16,
              color: colors.coldSilverBlue,
              fontWeight: 300,
            }}>Five specialized agents, one moonlit path</p>
          </div>
        );
      })()}

      {/* Agent Cards */}
      {agents.map((agent, index) => {
        const delay = index * 0.15 * fps;
        const cardScale = spring({
          frame: frame - delay,
          fps,
          config: { damping: 15, mass: 0.8, stiffness: 80 },
        });
        const cardOpacity = interpolate(
          frame - delay,
          [0, 0.5 * fps],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );

        const cardX = (agent.x / 100) * width;
        const cardY = height * 0.25 + (agent.name === 'Host' ? -20 : 0);

        // Light thread from card to convergence point
        const threadProgress = interpolate(
          frame - delay - 0.5 * fps,
          [0, 1.5 * fps],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );

        const threadEndY = cardY + 80 + (convergenceY - cardY - 80) * threadProgress;
        const threadEndX = cardX + (convergenceX - cardX) * threadProgress;

        return (
          <React.Fragment key={agent.name}>
            {/* Light thread SVG */}
            <svg style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              pointerEvents: 'none',
            }}>
              <defs>
                <linearGradient id={`thread-${index}`} x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" stopColor={colors.warmGold} stopOpacity={0.6} />
                  <stop offset="100%" stopColor={colors.moonlightSilver} stopOpacity={0.2} />
                </linearGradient>
              </defs>
              <line
                x1={cardX}
                y1={cardY + 80}
                x2={threadEndX}
                y2={threadEndY}
                stroke={`url(#thread-${index})`}
                strokeWidth={1.5}
                opacity={threadProgress * 0.7}
              />
            </svg>

            {/* Agent Card */}
            <div style={{
              position: 'absolute',
              left: cardX - 60,
              top: cardY - 20,
              width: 120,
              padding: '16px 12px',
              background: 'rgba(27, 42, 74, 0.4)',
              backdropFilter: 'blur(12px)',
              WebkitBackdropFilter: 'blur(12px)',
              border: `1px solid ${colors.warmGold}30`,
              borderRadius: 12,
              textAlign: 'center',
              transform: `scale(${cardScale})`,
              opacity: cardOpacity,
              boxShadow: `0 4px 24px rgba(0, 0, 0, 0.3), inset 0 1px 0 ${colors.moonlightSilver}10`,
            }}>
              <div style={{ fontSize: 28, marginBottom: 8 }}>{agent.icon}</div>
              <div style={{
                fontFamily: fonts.heading,
                fontSize: 14,
                color: colors.moonlightSilver,
                marginBottom: 4,
              }}>{agent.name}</div>
              <div style={{
                fontFamily: fonts.body,
                fontSize: 11,
                color: colors.coldSilverBlue,
                fontWeight: 300,
              }}>{agent.description}</div>
            </div>
          </React.Fragment>
        );
      })}

      {/* Convergence Point */}
      <div style={{
        position: 'absolute',
        left: convergenceX - 8,
        top: convergenceY - 8,
        width: 16,
        height: 16,
        borderRadius: '50%',
        background: `radial-gradient(circle, ${colors.warmGold} 0%, ${colors.moonlightSilver}60 50%, transparent 100%)`,
        boxShadow: `0 0 ${20 * pulse}px ${10 * pulse}px ${colors.warmGold}40`,
        opacity: interpolate(frame, [2 * fps, 3 * fps], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
      }} />

      {/* Label under convergence */}
      <div style={{
        position: 'absolute',
        left: convergenceX,
        top: convergenceY + 25,
        transform: 'translateX(-50%)',
        textAlign: 'center',
        opacity: interpolate(frame, [3 * fps, 3.5 * fps], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
      }}>
        <div style={{
          fontFamily: fonts.body,
          fontSize: 13,
          color: colors.warmGold,
          fontWeight: 400,
          letterSpacing: '0.1em',
        }}>DELIVERABLE</div>
      </div>
    </div>
  );
};
