import React from 'react';
import { Link } from 'react-router-dom';
import { colors, fonts } from '../../styles/theme';

export const NotFoundPage: React.FC = () => {
  return (
    <div
      style={{
        minHeight: '100vh',
        background: colors.midnightDeep,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '0 24px',
      }}
    >
      <h1
        style={{
          fontFamily: fonts.heading,
          fontSize: 96,
          color: colors.warmGold,
          marginBottom: 16,
          letterSpacing: '-0.02em',
        }}
      >
        404
      </h1>
      <p
        style={{
          fontFamily: fonts.heading,
          fontSize: 24,
          color: colors.moonlightSilver,
          marginBottom: 12,
        }}
      >
        Path Lost in the Mist
      </p>
      <p
        style={{
          fontFamily: fonts.body,
          fontSize: 16,
          color: colors.coldSilverBlue,
          marginBottom: 36,
          fontWeight: 300,
        }}
      >
        迷雾笼罩了水面，这条月光道路似乎并不存在。
      </p>
      <Link
        to="/"
        style={{
          background: `linear-gradient(135deg, ${colors.warmGold}, ${colors.pearlWhite})`,
          color: colors.midnightDeep,
          borderRadius: 24,
          padding: '12px 32px',
          fontWeight: 600,
          fontSize: 14,
          textDecoration: 'none',
        }}
      >
        返回月光起点 (Back Home)
      </Link>
    </div>
  );
};
