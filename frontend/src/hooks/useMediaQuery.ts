import { useState, useEffect } from 'react';
import { breakpoints } from '../styles/theme';

/**
 * Responsive breakpoint hook — returns current screen size classification.
 * Usage:
 *   const { isMobile, isTablet, isDesktop } = useResponsive();
 */
export function useResponsive() {
  const getState = () => {
    const w = window.innerWidth;
    return {
      isMobile: w < breakpoints.tablet,       // < 768
      isTablet: w >= breakpoints.tablet && w < breakpoints.desktop,  // 768–1023
      isDesktop: w >= breakpoints.desktop,     // >= 1024
      width: w,
    };
  };

  const [state, setState] = useState(getState);

  useEffect(() => {
    const handle = () => setState(getState());
    window.addEventListener('resize', handle);
    return () => window.removeEventListener('resize', handle);
  }, []);

  return state;
}
