import React, { useRef, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { MoonScene } from './MoonScene';
import { colors, fonts } from '../styles/theme';
import { useResponsive } from '../hooks/useMediaQuery';

export const HeroSection: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const [isHovered, setIsHovered] = useState(false);
  const [buttonTarget, setButtonTarget] = useState<{ x: number; y: number } | null>(null);
  const { isMobile } = useResponsive();

  const handleStart = () => {
    if (user) {
      navigate('/chat');
    } else {
      navigate('/login?redirect=/chat');
    }
  };

  // Update target button position for the star road
  const updateTarget = () => {
    if (buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect();
      setButtonTarget({
        x: rect.left + rect.width / 2,
        y: rect.bottom,
      });
    }
  };

  useEffect(() => {
    updateTarget();
    window.addEventListener('resize', updateTarget);
    return () => window.removeEventListener('resize', updateTarget);
  }, []);

  return (
    <section
      id="home"
      style={{
        position: 'relative',
        width: '100%',
        height: '100vh',
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Dynamic Moon & Lake Canvas with the Star-Assembling Road */}
      <MoonScene isRoadActive={isHovered} buttonTarget={buttonTarget} />

      {/* Main Content Box */}
      <div
        style={{
          position: 'relative',
          zIndex: 2,
          textAlign: 'center',
          maxWidth: isMobile ? 400 : 860,
          padding: '0 24px',
          marginTop: -42,
          pointerEvents: 'auto',
        }}
      >
        {/* Title */}
        <h1
          style={{
            fontFamily: fonts.heading,
            fontSize: isMobile ? 36 : 72,
            fontWeight: 700,
            color: colors.moonlightSilver,
            marginBottom: 20,
            letterSpacing: '-0.02em',
            lineHeight: 1.1,
            textShadow: `0 0 60px ${colors.warmGold}30, 0 0 120px ${colors.warmGold}15, 0 2px 4px rgba(0,0,0,0.6)`,
            userSelect: 'none',
          }}
        >
          MangataAgent
        </h1>

        {/* Subtitle Couplet */}
        <div style={{ marginBottom: 40 }}>
          <p
            style={{
              fontFamily: fonts.heading,
              fontSize: isMobile ? 18 : 27,
              fontWeight: 400,
              fontStyle: 'italic',
              color: colors.warmGold,
              marginBottom: 8,
              lineHeight: 1.35,
              textShadow: `0 0 35px ${colors.warmGold}35, 0 0 70px ${colors.warmGold}15`,
            }}
          >
            Code flows like moonlight.
          </p>

          <p
            style={{
              fontFamily: fonts.heading,
              fontSize: isMobile ? 18 : 27,
              fontWeight: 400,
              fontStyle: 'italic',
              color: colors.warmGold,
              margin: 0,
              lineHeight: 1.35,
              textShadow: `0 0 35px ${colors.warmGold}35, 0 0 70px ${colors.warmGold}15`,
            }}
          >
            Agents light the way.
          </p>
        </div>

        {/* Interactive Button - English 'Start Your Creation' with matching Playfair Display italic font */}
        <div style={{ position: 'relative', display: 'inline-block' }}>
          {/* Ambient breathing starlight halo */}
          <div
            style={{
              position: 'absolute',
              inset: -14,
              borderRadius: 44,
              background: `radial-gradient(ellipse, ${colors.warmGold}70 0%, ${colors.pearlWhite}25 50%, transparent 80%)`,
              opacity: isHovered ? 1 : 0.25,
              filter: 'blur(14px)',
              transition: 'opacity 0.4s ease',
              pointerEvents: 'none',
            }}
          />

          <button
            ref={buttonRef}
            onMouseEnter={() => {
              updateTarget();
              setIsHovered(true);
            }}
            onMouseLeave={() => setIsHovered(false)}
            style={{
              position: 'relative',
              zIndex: 1,
              fontFamily: fonts.heading,
              fontStyle: 'italic',
              fontSize: isMobile ? 16 : 19,
              fontWeight: 600,
              color: colors.midnightDeep,
              letterSpacing: '0.04em',
              padding: isMobile ? '12px 32px' : '15px 46px',
              borderRadius: 32,
              cursor: 'pointer',
              background: isHovered
                ? `linear-gradient(135deg, #FFFFFF 0%, ${colors.pearlWhite} 100%)`
                : `linear-gradient(135deg, #FBF2E0 0%, ${colors.warmGold} 55%, #C59A5E 100%)`,
              border: '1px solid rgba(255, 255, 255, 0.5)',
              boxShadow: isHovered
                ? `0 6px 50px ${colors.warmGold}85, 0 0 100px ${colors.warmGold}50, inset 0 1px 2px #FFFFFF`
                : `0 4px 28px ${colors.warmGold}40, 0 0 50px ${colors.warmGold}15, inset 0 1px 1px rgba(255,255,255,0.6)`,
              transform: isHovered ? 'translateY(-3px) scale(1.05)' : 'translateY(0) scale(1)',
              transition: 'all 0.35s cubic-bezier(0.2, 0.8, 0.2, 1)',
            }}
            onClick={handleStart}
          >
            Start Your Creation
          </button>
        </div>
      </div>

      {/* Scroll indicator at the bottom */}
      <div
        style={{
          position: 'absolute',
          bottom: 28,
          left: '50%',
          zIndex: 2,
          textAlign: 'center',
          transform: 'translateX(-50%)',
          pointerEvents: 'none',
          opacity: isHovered ? 0.2 : 0.6,
          transition: 'opacity 0.4s ease',
        }}
      >
        <div
          style={{
            fontFamily: fonts.body,
            fontSize: 11,
            color: colors.coldSilverBlue,
            letterSpacing: '0.2em',
            marginBottom: 6,
            fontWeight: 300,
          }}
        >
          SCROLL
        </div>
        <svg width="18" height="10" viewBox="0 0 20 12">
          <path
            d="M2 2 L10 10 L18 2"
            stroke={colors.coldSilverBlue}
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
          />
        </svg>
      </div>
    </section>
  );
};
