import { useRef, useEffect, useState } from 'react';
import { ParticleCloud } from './ParticleCloud';
import { featuresToUniforms } from './featureMap';
import { Phase, TrackFeatures } from '../types';
import { VIBE_COLORS, ENTRANCE_DURATION } from '../constants';

interface Props {
  phase: Phase;
  outputFeatures: TrackFeatures | null;
  vibeLib: string | null;
  onClickCloud: () => void;
}

export function SingleCloudLayout({ phase, outputFeatures, vibeLib, onClickCloud }: Props) {
  const [entranceProgress, setEntranceProgress] = useState(0);
  const entranceStartRef = useRef<number | null>(null);
  const showCloud = phase === 'loading' || phase === 'playing';

  useEffect(() => {
    if (phase === 'playing' && entranceStartRef.current === null) {
      entranceStartRef.current = performance.now();
      const animate = () => {
        const elapsed = performance.now() - entranceStartRef.current!;
        const t = Math.min(1, elapsed / ENTRANCE_DURATION);
        // Ease out cubic
        const eased = 1 - Math.pow(1 - t, 3);
        setEntranceProgress(eased);
        if (t < 1) requestAnimationFrame(animate);
      };
      requestAnimationFrame(animate);
    }
    if (phase === 'idle') {
      entranceStartRef.current = null;
      setEntranceProgress(0);
    }
  }, [phase]);

  if (!showCloud) return null;

  const color = vibeLib ? (VIBE_COLORS[vibeLib] ?? '#2DD4BF') : '#2DD4BF';
  const ghostOpacity = phase === 'loading' ? 0.2 : 1.0;
  const targetUniforms = featuresToUniforms(outputFeatures, vibeLib);

  return (
    <ParticleCloud
      color={color}
      targetUniforms={targetUniforms}
      entranceProgress={phase === 'loading' ? 0.3 : entranceProgress}
      ghostOpacity={ghostOpacity}
      onClick={phase === 'playing' ? onClickCloud : undefined}
      position={[0, 0.5, 0]}
    />
  );
}
