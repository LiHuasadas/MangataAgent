import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { colors, fonts } from '../styles/theme';
import { Sparkles } from 'lucide-react';

export const Navbar: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <nav
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        padding: '0 48px',
        height: 64,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: scrolled ? 'rgba(11, 16, 38, 0.92)' : 'transparent',
        backdropFilter: scrolled ? 'blur(20px)' : 'none',
        WebkitBackdropFilter: scrolled ? 'blur(20px)' : 'none',
        borderBottom: scrolled ? `1px solid ${colors.warmGold}15` : 'none',
        transition: 'background 0.3s ease, border-bottom 0.3s ease',
      }}
    >
      {/* Brand Logo on the left */}
      <Link
        to="/"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          textDecoration: 'none',
        }}
      >
        <Sparkles size={20} color={colors.warmGold} />
        <span
          style={{
            fontFamily: fonts.heading,
            fontSize: 22,
            color: colors.warmGold,
            fontWeight: 600,
            letterSpacing: '-0.01em',
          }}
        >
          MangataAgent
        </span>
      </Link>

      {/* Top right is clean with no buttons */}
      <div />
    </nav>
  );
};
