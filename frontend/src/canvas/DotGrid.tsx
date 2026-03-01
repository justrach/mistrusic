import { useEffect, useRef } from 'react';
import { DOT_GRID_SPACING, DOT_RADIUS, DOT_HOVER_RADIUS } from '../constants';

interface Props {
  isMorphing: boolean;
}

export function DotGrid({ isMorphing }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouseRef = useRef({ x: -9999, y: -9999 });
  const morphingRef = useRef(isMorphing);
  const pulseOpacityRef = useRef(0);

  morphingRef.current = isMorphing;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    let raf: number;
    let startTime = performance.now();

    const resize = () => {
      canvas.width = window.innerWidth * devicePixelRatio;
      canvas.height = window.innerHeight * devicePixelRatio;
      canvas.style.width = window.innerWidth + 'px';
      canvas.style.height = window.innerHeight + 'px';
      ctx.scale(devicePixelRatio, devicePixelRatio);
    };

    const onMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };

    const draw = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      ctx.clearRect(0, 0, w, h);

      const t = (performance.now() - startTime) / 1000;
      const mx = mouseRef.current.x;
      const my = mouseRef.current.y;

      const targetPulse = morphingRef.current ? 1 : 0;
      pulseOpacityRef.current += (targetPulse - pulseOpacityRef.current) * 0.03;

      const spacing = DOT_GRID_SPACING;
      const cols = Math.ceil(w / spacing) + 1;
      const rows = Math.ceil(h / spacing) + 1;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const x = c * spacing;
          const y = r * spacing;

          const dx = x - mx;
          const dy = y - my;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const hoverFactor = Math.max(0, 1 - dist / DOT_HOVER_RADIUS);

          const pulse = Math.sin(t * 3 + (x + y) * 0.02) * 0.5 + 0.5;
          const pulseContrib = pulse * pulseOpacityRef.current * 0.3;

          const baseAlpha = 0.35;
          const alpha = Math.min(1, baseAlpha + hoverFactor * 0.5 + pulseContrib);

          const baseR = 209, baseG = 207, baseB = 201;
          const hoverR = 153, hoverG = 153, hoverB = 153;
          const f = hoverFactor;
          const cr = Math.round(baseR + (hoverR - baseR) * f);
          const cg = Math.round(baseG + (hoverG - baseG) * f);
          const cb = Math.round(baseB + (hoverB - baseB) * f);

          ctx.beginPath();
          ctx.arc(x, y, DOT_RADIUS, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${cr},${cg},${cb},${alpha})`;
          ctx.fill();
        }
      }

      raf = requestAnimationFrame(draw);
    };

    resize();
    window.addEventListener('resize', resize);
    window.addEventListener('mousemove', onMove);
    raf = requestAnimationFrame(draw);

    return () => {
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', onMove);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: 0,
        pointerEvents: 'none',
      }}
    />
  );
}
