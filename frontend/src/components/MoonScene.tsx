import React, { useEffect, useRef } from 'react';
import { colors } from '../styles/theme';

interface MoonSceneProps {
  isRoadActive?: boolean;
  buttonTarget?: { x: number; y: number } | null;
}

interface StarParticle {
  id: number;
  // Ambient wandering properties
  originX: number;
  originY: number;
  driftRadiusX: number;
  driftRadiusY: number;
  driftSpeedX: number;
  driftSpeedY: number;
  driftPhase: number;

  // Road properties
  roadProgress: number;   // 0 (lake bottom) -> 1 (button)
  roadLateralNorm: number; // -1 to 1 offset factor
  roadSpeed: number;      // upward streaming speed

  // Smooth independent physics transition (0 = ambient, 1 = road)
  currentEase: number;
  gatherRate: number;     // speed of convergence
  disperseRate: number;   // speed of dispersal

  // Rendering
  size: number;
  spriteIndex: number;
  twinkleSpeed: number;
  twinklePhase: number;
  isSparkle: boolean;
}

export const MoonScene: React.FC<MoonSceneProps> = ({
  isRoadActive = false,
  buttonTarget = null,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameRef = useRef<number>(0);

  const stateRef = useRef({
    active: false,
    roadBlend: 0,
    targetX: 0,
    targetY: 0,
  });

  useEffect(() => {
    stateRef.current.active = isRoadActive;
  }, [isRoadActive]);

  useEffect(() => {
    if (buttonTarget) {
      stateRef.current.targetX = buttonTarget.x;
      stateRef.current.targetY = buttonTarget.y;
    }
  }, [buttonTarget]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);

    // ─────────────────────────────────────────────────────────────
    // 1. High-Performance Pre-rendered Star Glow Sprites
    // Eliminates all 480+ `ctx.shadowBlur` operations per frame!
    // ─────────────────────────────────────────────────────────────
    const spritePalette = [
      { core: '#FFFFFF', halo: 'rgba(255, 255, 255, 0.45)' },
      { core: '#FFF5DC', halo: 'rgba(242, 217, 166, 0.50)' },
      { core: colors.warmGold, halo: 'rgba(212, 175, 122, 0.55)' },
      { core: colors.pearlWhite, halo: 'rgba(242, 217, 166, 0.50)' },
      { core: '#FFE08C', halo: 'rgba(255, 215, 110, 0.55)' },
      { core: colors.moonlightSilver, halo: 'rgba(201, 214, 227, 0.40)' },
      { core: '#B8DCFF', halo: 'rgba(160, 210, 255, 0.45)' },
    ];

    const SPRITE_SIZE = 40;
    const HALF_SPRITE = SPRITE_SIZE / 2;
    const starSprites: HTMLCanvasElement[] = spritePalette.map(palette => {
      const sCanvas = document.createElement('canvas');
      sCanvas.width = SPRITE_SIZE;
      sCanvas.height = SPRITE_SIZE;
      const sCtx = sCanvas.getContext('2d');
      if (sCtx) {
        const rad = sCtx.createRadialGradient(
          HALF_SPRITE, HALF_SPRITE, 1,
          HALF_SPRITE, HALF_SPRITE, HALF_SPRITE - 2
        );
        rad.addColorStop(0, '#FFFFFF');
        rad.addColorStop(0.2, palette.core);
        rad.addColorStop(0.5, palette.halo);
        rad.addColorStop(1, 'rgba(0, 0, 0, 0)');

        sCtx.fillStyle = rad;
        sCtx.beginPath();
        sCtx.arc(HALF_SPRITE, HALF_SPRITE, HALF_SPRITE - 2, 0, Math.PI * 2);
        sCtx.fill();
      }
      return sCanvas;
    });

    // ─────────────────────────────────────────────────────────────
    // 2. Initialize 450 Stars with Smooth Spring Physics
    // ─────────────────────────────────────────────────────────────
    const STAR_COUNT = 450;
    const stars: StarParticle[] = [];

    // Horizon position (sea starts at 50% height)
    const horizonY = height * 0.50;
    const skyMaxY = horizonY - 18; // strictly above sea horizon

    for (let i = 0; i < STAR_COUNT; i++) {
      const rx = Math.random() * width;
      // All stars strictly in the night sky (0 to skyMaxY), none in the sea!
      const ryRatio = 0.02 + Math.random() * 0.95;
      const ry = ryRatio * skyMaxY;

      // Central clustering for a dense road spine
      const rawCluster = Math.pow(Math.random(), 1.6);
      const sign = Math.random() < 0.5 ? -1 : 1;

      stars.push({
        id: i,
        originX: rx,
        originY: ry,
        driftRadiusX: 12 + Math.random() * 26,
        driftRadiusY: 6 + Math.random() * 14,
        driftSpeedX: 0.15 + Math.random() * 0.35,
        driftSpeedY: 0.12 + Math.random() * 0.3,
        driftPhase: Math.random() * Math.PI * 2,

        roadProgress: Math.random(),
        roadLateralNorm: rawCluster * sign,
        roadSpeed: 0.005 + Math.random() * 0.009,

        currentEase: 0,
        // Individualized fluid gather and disperse speeds
        gatherRate: 0.08 + (i % 20) * 0.003,
        disperseRate: 0.05 + (i % 15) * 0.0025,

        size: 1.0 + Math.random() * 2.2,
        spriteIndex: i % starSprites.length,
        twinkleSpeed: 1.4 + Math.random() * 2.8,
        twinklePhase: Math.random() * Math.PI * 2,
        isSparkle: i % 3 === 0,
      });
    }

    let lastTime = performance.now();
    let time = 0;

    // ─────────────────────────────────────────────────────────────
    // 3. Draw Lake Water Surface (Dynamic Undulating Waves)
    // ─────────────────────────────────────────────────────────────
    const drawLake = (t: number) => {
      const lakeTop = height * 0.51;
      const lakeHeight = height - lakeTop;

      // Lake gradient
      const lakeGrad = ctx.createLinearGradient(0, lakeTop, 0, height);
      lakeGrad.addColorStop(0, 'rgba(7, 12, 30, 0.90)');
      lakeGrad.addColorStop(0.3, 'rgba(4, 8, 20, 0.96)');
      lakeGrad.addColorStop(1, '#02040d');
      ctx.fillStyle = lakeGrad;
      ctx.fillRect(0, lakeTop, width, lakeHeight);

      // Horizon mist
      const mistGrad = ctx.createLinearGradient(0, lakeTop - 18, 0, lakeTop + 35);
      mistGrad.addColorStop(0, 'rgba(20, 32, 64, 0.5)');
      mistGrad.addColorStop(0.5, 'rgba(28, 46, 88, 0.22)');
      mistGrad.addColorStop(1, 'transparent');
      ctx.fillStyle = mistGrad;
      ctx.fillRect(0, lakeTop - 18, width, 53);

      // Ambient Moon reflection on water
      const moonX = width * 0.5;
      const shimmerGrad = ctx.createRadialGradient(
        moonX, lakeTop + 45, 10,
        moonX, lakeTop + 160, width * 0.24
      );
      shimmerGrad.addColorStop(0, 'rgba(212, 175, 122, 0.24)');
      shimmerGrad.addColorStop(0.35, 'rgba(242, 217, 166, 0.11)');
      shimmerGrad.addColorStop(0.7, 'rgba(124, 147, 179, 0.04)');
      shimmerGrad.addColorStop(1, 'transparent');
      ctx.fillStyle = shimmerGrad;
      ctx.fillRect(moonX - width * 0.25, lakeTop, width * 0.5, lakeHeight);

      // 14 Dynamic undulating wavelets
      const waveRows = 14;
      for (let r = 0; r < waveRows; r++) {
        const rowProg = r / waveRows;
        const waveY = lakeTop + 12 + Math.pow(rowProg, 1.45) * (lakeHeight - 25);
        const waveWidth = 110 + rowProg * (width * 0.78);
        const startX = moonX - waveWidth * 0.5;

        const speed = 1.1 + r * 0.12;
        const amplitude = 1.2 + rowProg * 3.4;
        const offset = Math.sin(t * speed + r * 0.8) * amplitude;
        const alpha = (0.30 - rowProg * 0.18) * (0.8 + 0.2 * Math.sin(t * 1.8 + r));

        ctx.beginPath();
        ctx.moveTo(startX, waveY + offset);

        for (let x = startX; x <= startX + waveWidth; x += 18) {
          const waveSine = Math.sin((x * 0.018) + t * 2.2 + r) * amplitude;
          ctx.lineTo(x, waveY + offset + waveSine);
        }

        ctx.strokeStyle = `rgba(212, 175, 122, ${Math.max(0, alpha)})`;
        ctx.lineWidth = 1 + rowProg * 1.6;
        ctx.stroke();

        if (r % 2 === 0) {
          ctx.beginPath();
          const subW = waveWidth * 1.35;
          const subStart = moonX - subW * 0.5;
          ctx.moveTo(subStart, waveY + offset + 2);
          for (let x = subStart; x <= subStart + subW; x += 28) {
            const subSine = Math.cos((x * 0.014) - t * 1.6 + r) * 1.5;
            ctx.lineTo(x, waveY + offset + 2 + subSine);
          }
          ctx.strokeStyle = `rgba(201, 214, 227, ${alpha * 0.32})`;
          ctx.lineWidth = 0.75;
          ctx.stroke();
        }
      }
    };

    // ─────────────────────────────────────────────────────────────
    // 4. Draw Moon and Celestial Glow
    // ─────────────────────────────────────────────────────────────
    const drawMoon = (t: number) => {
      const moonX = width * 0.5;
      const moonY = height * 0.175;
      const moonRadius = 55;

      // Soft breathing corona aura
      const pulse = Math.sin(t * 0.8) * 0.04 + 1;
      const coronaRadius = moonRadius * 4.2 * pulse;
      const coronaGrad = ctx.createRadialGradient(
        moonX, moonY, moonRadius * 0.7,
        moonX, moonY, coronaRadius
      );
      coronaGrad.addColorStop(0, 'rgba(212, 175, 122, 0.32)');
      coronaGrad.addColorStop(0.28, 'rgba(242, 217, 166, 0.14)');
      coronaGrad.addColorStop(0.65, 'rgba(124, 147, 179, 0.05)');
      coronaGrad.addColorStop(1, 'transparent');
      ctx.fillStyle = coronaGrad;
      ctx.beginPath();
      ctx.arc(moonX, moonY, coronaRadius, 0, Math.PI * 2);
      ctx.fill();

      // Vertical moonbeam column
      const beamGrad = ctx.createLinearGradient(moonX, moonY + moonRadius, moonX, height * 0.58);
      beamGrad.addColorStop(0, 'rgba(242, 217, 166, 0.28)');
      beamGrad.addColorStop(0.4, 'rgba(212, 175, 122, 0.12)');
      beamGrad.addColorStop(1, 'transparent');

      ctx.beginPath();
      ctx.moveTo(moonX - 3, moonY + moonRadius);
      ctx.lineTo(moonX + 3, moonY + moonRadius);
      ctx.lineTo(moonX + 45, height * 0.58);
      ctx.lineTo(moonX - 45, height * 0.58);
      ctx.closePath();
      ctx.fillStyle = beamGrad;
      ctx.fill();

      // Lunar disc body
      const moonBodyGrad = ctx.createRadialGradient(
        moonX - moonRadius * 0.25, moonY - moonRadius * 0.25, moonRadius * 0.1,
        moonX, moonY, moonRadius
      );
      moonBodyGrad.addColorStop(0, '#FFFDF8');
      moonBodyGrad.addColorStop(0.25, '#F6EEDC');
      moonBodyGrad.addColorStop(0.6, '#E5D6BA');
      moonBodyGrad.addColorStop(0.85, '#C8B695');
      moonBodyGrad.addColorStop(1, '#A99778');

      ctx.fillStyle = moonBodyGrad;
      ctx.beginPath();
      ctx.arc(moonX, moonY, moonRadius, 0, Math.PI * 2);
      ctx.fill();

      // Craters / Maria
      const craters = [
        { cx: moonX - 12, cy: moonY - 14, r: 9,  o: 0.18 },
        { cx: moonX + 18, cy: moonY + 6,  r: 14, o: 0.22 },
        { cx: moonX + 6,  cy: moonY - 22, r: 7,  o: 0.15 },
        { cx: moonX - 20, cy: moonY + 12, r: 12, o: 0.24 },
        { cx: moonX + 8,  cy: moonY + 24, r: 8,  o: 0.17 },
        { cx: moonX - 8,  cy: moonY + 28, r: 6,  o: 0.14 },
      ];

      for (let c = 0; c < craters.length; c++) {
        const cr = craters[c];
        const cGrad = ctx.createRadialGradient(cr.cx, cr.cy, 1, cr.cx, cr.cy, cr.r);
        cGrad.addColorStop(0, `rgba(130, 115, 92, ${cr.o})`);
        cGrad.addColorStop(0.85, `rgba(150, 135, 110, ${cr.o * 0.4})`);
        cGrad.addColorStop(1, 'transparent');
        ctx.fillStyle = cGrad;
        ctx.beginPath();
        ctx.arc(cr.cx, cr.cy, cr.r, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    // ─────────────────────────────────────────────────────────────
    // 5. Draw the Celestial Star Road Bed (Pure Organic Starlight, No Hard Edges)
    // ─────────────────────────────────────────────────────────────
    const drawStarRoadRunway = (targetX: number, targetY: number, progress: number) => {
      if (progress <= 0.01) return;

      const bottomY = height;
      const topY = targetY + 14;
      const roadH = bottomY - topY;

      // 1. Soft, organic ambient starlight mist underneath (completely borderless, no hard lines)
      const glowGrad = ctx.createRadialGradient(
        targetX, topY + roadH * 0.55, 15,
        targetX, topY + roadH * 0.55, 260 * progress
      );
      glowGrad.addColorStop(0, `rgba(242, 217, 166, ${0.28 * progress})`);
      glowGrad.addColorStop(0.4, `rgba(212, 175, 122, ${0.16 * progress})`);
      glowGrad.addColorStop(0.75, `rgba(124, 147, 179, ${0.06 * progress})`);
      glowGrad.addColorStop(1, 'transparent');

      ctx.fillStyle = glowGrad;
      ctx.fillRect(targetX - 300, topY, 600, roadH);

      // 2. Subtle, natural water wave reflection rungs along the center path
      const rungs = 7;
      ctx.beginPath();
      for (let i = 1; i <= rungs; i++) {
        const rungT = i / (rungs + 1);
        const rungY = bottomY - Math.pow(rungT, 1.25) * roadH;
        const rungWidth = (30 + (1 - rungT) * 160) * progress;

        ctx.moveTo(targetX - rungWidth * 0.5, rungY);
        ctx.lineTo(targetX + rungWidth * 0.5, rungY);
      }
      ctx.strokeStyle = `rgba(242, 217, 166, ${0.22 * progress})`;
      ctx.lineWidth = 1.2 * progress;
      ctx.stroke();

      // 3. Starlight arrival burst under the button
      const burstRadius = (44 + Math.sin(time * 7) * 7) * progress;
      const burstGrad = ctx.createRadialGradient(targetX, topY, 2, targetX, topY, burstRadius);
      burstGrad.addColorStop(0, 'rgba(255, 255, 255, 0.95)');
      burstGrad.addColorStop(0.35, 'rgba(242, 217, 166, 0.65)');
      burstGrad.addColorStop(0.7, 'rgba(212, 175, 122, 0.3)');
      burstGrad.addColorStop(1, 'transparent');

      ctx.fillStyle = burstGrad;
      ctx.beginPath();
      ctx.arc(targetX, topY, burstRadius, 0, Math.PI * 2);
      ctx.fill();

      // Pulsing outer ripple ring
      const ringR = (20 + (time * 45) % 55) * progress;
      const ringAlpha = Math.max(0, (1 - ringR / 75) * 0.60 * progress);
      ctx.strokeStyle = `rgba(255, 240, 200, ${ringAlpha})`;
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.arc(targetX, topY, ringR, 0, Math.PI * 2);
      ctx.stroke();
    };

    // ─────────────────────────────────────────────────────────────
    // 6. High-Performance 60FPS / 120FPS Render Loop
    // ─────────────────────────────────────────────────────────────
    const render = () => {
      const now = performance.now();
      const dt = Math.min((now - lastTime) / 1000, 0.04); // smooth frame delta time
      lastTime = now;
      time += dt;

      // Global road blend factor
      const targetActive = stateRef.current.active ? 1 : 0;
      stateRef.current.roadBlend += (targetActive - stateRef.current.roadBlend) * Math.min(1, dt * 10);
      const roadBlend = stateRef.current.roadBlend;

      // Clear Canvas with cosmic night sky gradient
      const skyGrad = ctx.createLinearGradient(0, 0, 0, height);
      skyGrad.addColorStop(0, '#030510');
      skyGrad.addColorStop(0.22, '#060B20');
      skyGrad.addColorStop(0.48, '#0C1635');
      skyGrad.addColorStop(0.7, '#111E42');
      skyGrad.addColorStop(1, '#070C1E');
      ctx.fillStyle = skyGrad;
      ctx.fillRect(0, 0, width, height);

      // 1. Draw Moon
      drawMoon(time);

      // 2. Draw Lake Surface
      drawLake(time);

      // Target button coordinates
      const targetX = stateRef.current.targetX || width * 0.5;
      const targetY = stateRef.current.targetY || height * 0.46;

      // 3. Draw Road Runway Bed
      drawStarRoadRunway(targetX, targetY, roadBlend);

      // 4. Update & Draw Stars via GPU-accelerated Sprites (ZERO LAG!)
      const roadBottomY = height;
      const roadTopY = targetY + 10;
      const roadLength = roadBottomY - roadTopY;

      // Batch arrays for cross sparkles and motion trails
      const sparklesToDraw: { x: number; y: number; len: number }[] = [];
      const trailsToDraw: { x: number; y: number; len: number }[] = [];

      for (let i = 0; i < STAR_COUNT; i++) {
        const star = stars[i];

        // Smooth spring physics per star (independent, no sudden pops)
        const rate = stateRef.current.active ? star.gatherRate : star.disperseRate;
        star.currentEase += (targetActive - star.currentEase) * Math.min(1, rate * (dt * 60));
        // Smoothstep easing
        const ease = star.currentEase * star.currentEase * (3 - 2 * star.currentEase);

        // --- Ambient coordinates: drifting strictly in the night sky above sea horizon ---
        const currentHorizonY = height * 0.50;
        const currentSkyMaxY = currentHorizonY - 14;
        const ambX = star.originX + Math.sin(time * star.driftSpeedX + star.driftPhase) * star.driftRadiusX;
        const rawAmbY = star.originY + Math.cos(time * star.driftSpeedY + star.driftPhase) * star.driftRadiusY;
        const ambY = Math.min(currentSkyMaxY, Math.max(8, rawAmbY));

        // --- Road coordinates: streaming upward ---
        if (ease > 0.05) {
          const accel = 1 + (1 - star.roadProgress) * 0.8;
          star.roadProgress += star.roadSpeed * accel * (dt * 60);
          if (star.roadProgress > 1.0) {
            star.roadProgress -= 1.0;
            const rawCluster = Math.pow(Math.random(), 1.6);
            star.roadLateralNorm = rawCluster * (Math.random() < 0.5 ? -1 : 1);
          }
        }

        // Perspective road width
        const progressFromBottom = star.roadProgress;
        const roadCurrentY = roadBottomY - progressFromBottom * roadLength;
        const currentHalfWidth = 20 + Math.pow(1 - progressFromBottom, 1.4) * 230;
        const roadCurrentX = targetX + star.roadLateralNorm * currentHalfWidth;

        // Final interpolated position (buttery smooth blend)
        const currentX = ambX + (roadCurrentX - ambX) * ease;
        const currentY = ambY + (roadCurrentY - ambY) * ease;

        // Twinkle and alpha
        const twinkle = 0.5 + 0.5 * Math.sin(time * star.twinkleSpeed + star.twinklePhase);
        const roadAlphaBoost = ease * 0.45;
        const currentAlpha = Math.min(1, 0.4 + twinkle * 0.4 + roadAlphaBoost);
        const currentSize = star.size * (1 + ease * 0.8);

        // Draw pre-rendered glowing star sprite (GPU BLIT - INSTANT!)
        ctx.globalAlpha = currentAlpha;
        const renderR = currentSize * 3.5;
        const sprite = starSprites[star.spriteIndex];
        ctx.drawImage(
          sprite,
          currentX - renderR,
          currentY - renderR,
          renderR * 2,
          renderR * 2
        );

        // Collect 4-point cross sparkles for batch stroke
        if (star.isSparkle || (ease > 0.35 && i % 2 === 0)) {
          sparklesToDraw.push({
            x: currentX,
            y: currentY,
            len: currentSize * (ease > 0.4 ? 3.6 : 2.2),
          });
        }

        // Collect motion trails for stars streaming on the road
        if (ease > 0.4 && star.roadSpeed > 0.005) {
          trailsToDraw.push({
            x: currentX,
            y: currentY,
            len: 8 + star.roadSpeed * 1100,
          });
        }
      }

      // ───────────────────────────────────────────────────────────
      // Batch Draw Cross Sparkles (1 single draw call for all!)
      // ───────────────────────────────────────────────────────────
      if (sparklesToDraw.length > 0) {
        ctx.beginPath();
        for (let s = 0; s < sparklesToDraw.length; s++) {
          const sp = sparklesToDraw[s];
          ctx.moveTo(sp.x - sp.len, sp.y);
          ctx.lineTo(sp.x + sp.len, sp.y);
          ctx.moveTo(sp.x, sp.y - sp.len);
          ctx.lineTo(sp.x, sp.y + sp.len);
        }
        ctx.strokeStyle = '#FFFFFF';
        ctx.globalAlpha = 0.85;
        ctx.lineWidth = 0.75;
        ctx.stroke();
      }

      // ───────────────────────────────────────────────────────────
      // Batch Draw Motion Trails (1 single draw call for all!)
      // ───────────────────────────────────────────────────────────
      if (trailsToDraw.length > 0) {
        ctx.beginPath();
        for (let tIdx = 0; tIdx < trailsToDraw.length; tIdx++) {
          const tr = trailsToDraw[tIdx];
          ctx.moveTo(tr.x, tr.y);
          ctx.lineTo(tr.x, tr.y + tr.len);
        }
        ctx.strokeStyle = colors.warmGold;
        ctx.globalAlpha = 0.45;
        ctx.lineWidth = 1.2;
        ctx.stroke();
      }

      ctx.globalAlpha = 1.0;
      animFrameRef.current = requestAnimationFrame(render);
    };

    animFrameRef.current = requestAnimationFrame(render);

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <canvas
        ref={canvasRef}
        style={{
          display: 'block',
          width: '100%',
          height: '100%',
          position: 'absolute',
          inset: 0,
        }}
      />
    </div>
  );
};
