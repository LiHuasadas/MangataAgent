import React from 'react';
import { useCurrentFrame, useVideoConfig, interpolate } from 'remotion';
import { colors } from '../styles/theme';

export const MoonlightPath: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // Generate sparkle positions deterministically from index
  const sparkles = Array.from({ length: 20 }, (_, i) => {
    const seed = (i * 137.508) % 1; // golden angle distribution
    const x = seed * width;
    const baseY = height * 0.5 + (((i * 73) % 100) - 50);
    const speed = 0.3 + (i % 5) * 0.15;
    const delay = (i * 0.3) * fps;
    const size = 1.5 + (i % 3);

    const progress = interpolate(
      frame - delay,
      [0, 3 * fps],
      [0, 1],
      { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
    );

    const y = baseY - progress * 120;
    const opacity = interpolate(
      progress,
      [0, 0.2, 0.8, 1],
      [0, 0.8, 0.6, 0],
      { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
    );

    return { x, y, opacity, size };
  });

  // Main light band oscillation
  const bandPulse = Math.sin((frame / fps) * Math.PI * 0.5) * 0.15 + 0.85;
  const bandWidth = interpolate(
    frame,
    [0, 2 * fps],
    [0, width * 0.7],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );

  // Secondary ripple layers
  const ripple1 = Math.sin((frame / fps) * Math.PI * 0.8) * 10;
  const ripple2 = Math.sin((frame / fps) * Math.PI * 1.2 + 1) * 6;

  return (
    <div style={{
      width: '100%',
      height: '100%',
      background: `linear-gradient(180deg, ${colors.midnightDeep} 0%, ${colors.midnightMid} 50%, ${colors.midnightDeep} 100%)`,
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Main light band */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: `translate(-50%, -50%) translateY(${ripple1}px)`,
        width: bandWidth,
        height: 4,
        background: `radial-gradient(ellipse at center, ${colors.warmGold}${Math.round(bandPulse * 255).toString(16).padStart(2, '0')} 0%, ${colors.moonlightSilver}40 40%, transparent 70%)`,
        borderRadius: '50%',
        boxShadow: `0 0 60px 30px ${colors.warmGold}30, 0 0 120px 60px ${colors.moonlightSilver}15`,
      }} />

      {/* Secondary glow layer */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: `translate(-50%, -50%) translateY(${ripple2}px)`,
        width: bandWidth * 0.8,
        height: 2,
        background: `radial-gradient(ellipse at center, ${colors.pearlWhite}60 0%, transparent 60%)`,
        borderRadius: '50%',
      }} />

      {/* Wide ambient glow */}
      <div style={{
        position: 'absolute',
        top: '45%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: bandWidth * 1.2,
        height: 200,
        background: `radial-gradient(ellipse at center, ${colors.warmGold}08 0%, transparent 70%)`,
        borderRadius: '50%',
      }} />

      {/* Sparkles */}
      {sparkles.map((s, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: s.x,
            top: s.y,
            width: s.size,
            height: s.size,
            borderRadius: '50%',
            backgroundColor: i % 3 === 0 ? colors.warmGold : colors.moonlightSilver,
            opacity: s.opacity,
          }}
        />
      ))}
    </div>
  );
};
