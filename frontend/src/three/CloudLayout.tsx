import { useState, useEffect } from 'react';
import { ParticleCloud } from './ParticleCloud';
import { featuresToUniforms, DEFAULT_UNIFORMS, ShaderUniforms } from './featureMap';
import { getColor, blendColors } from './colors';
import { SoundEntry, AudioFeatures, MorphStep, Phase } from '../types';

interface Props {
  soundA: SoundEntry | null;
  soundB: SoundEntry | null;
  phase: Phase;
  currentStep: number;
  morphSteps: MorphStep[];
  outputFeatures: AudioFeatures | null;
  outputId: string | null;
  onClickCloud: (id: string) => void;
}

function getMorphPhaseValues(phase: Phase, currentStep: number) {
  if (phase === 'complete') return { morphPhase: 1.0, ghostOpacity: 1.0 };
  if (phase !== 'morphing') return { morphPhase: 0, ghostOpacity: 0 };
  if (currentStep <= 0) return { morphPhase: 0.0, ghostOpacity: 0.15 };
  if (currentStep === 1) return { morphPhase: 0.33, ghostOpacity: 0.35 };
  if (currentStep === 2) return { morphPhase: 0.66, ghostOpacity: 0.65 };
  return { morphPhase: 1.0, ghostOpacity: 1.0 };
}

function parseStepCues(steps: MorphStep[]) {
  let spikinessBoost = 0;
  let scatterBoost = 0;
  let blendWeight = 0.5;

  for (const step of steps) {
    const text = step.model_output || '';
    if (text.includes('spectral_imprint') || text.includes('cross_synth')) {
      spikinessBoost = 0.3;
    }
    if (text.includes('convolution')) {
      scatterBoost = 0.3;
    }
    const ratioMatch = text.match(/ratio[=:]?\s*([\d.]+)/);
    if (ratioMatch) {
      blendWeight = parseFloat(ratioMatch[1]);
      if (blendWeight > 1) blendWeight = blendWeight / 100;
    }
  }

  return { spikinessBoost, scatterBoost, blendWeight };
}

export function CloudLayout({
  soundA,
  soundB,
  phase,
  currentStep,
  morphSteps,
  outputFeatures,
  outputId,
  onClickCloud,
}: Props) {
  const [entranceA, setEntranceA] = useState(0);
  const [entranceB, setEntranceB] = useState(0);
  const [entranceOut, setEntranceOut] = useState(0);

  useEffect(() => {
    if (soundA) {
      const start = performance.now();
      const animate = () => {
        const elapsed = performance.now() - start;
        const progress = Math.min(1, elapsed / 1500);
        setEntranceA(1 - Math.pow(1 - progress, 3));
        if (progress < 1) requestAnimationFrame(animate);
      };
      requestAnimationFrame(animate);
    }
  }, [soundA?.id]);

  useEffect(() => {
    if (soundB) {
      const start = performance.now();
      const animate = () => {
        const elapsed = performance.now() - start;
        const progress = Math.min(1, elapsed / 1500);
        setEntranceB(1 - Math.pow(1 - progress, 3));
        if (progress < 1) requestAnimationFrame(animate);
      };
      requestAnimationFrame(animate);
    }
  }, [soundB?.id]);

  useEffect(() => {
    if (phase === 'morphing' || phase === 'complete') {
      const start = performance.now();
      const animate = () => {
        const elapsed = performance.now() - start;
        const progress = Math.min(1, elapsed / 1500);
        setEntranceOut(1 - Math.pow(1 - progress, 3));
        if (progress < 1) requestAnimationFrame(animate);
      };
      requestAnimationFrame(animate);
    }
  }, [phase === 'morphing']);

  const hasBoth = soundA && soundB;
  const { morphPhase, ghostOpacity } = getMorphPhaseValues(phase, currentStep);
  const showOutput = phase === 'morphing' || phase === 'complete';

  // Tighter positions — keep clouds well within view
  const posA: [number, number, number] = hasBoth ? [-1.8, 0.6, 0] : [0, 0.3, 0];
  const posB: [number, number, number] = [1.8, 0.6, 0];
  const posOut: [number, number, number] = [0, -1.0, 0];

  const cues = parseStepCues(morphSteps);
  const colorA = soundA ? getColor(soundA.colorIndex) : '#888888';
  const colorB = soundB ? getColor(soundB.colorIndex) : colorA;
  const outputColor = showOutput
    ? morphPhase < 0.33
      ? '#888888'
      : blendColors(colorA, colorB, cues.blendWeight)
    : '#888888';

  const outputUniforms: ShaderUniforms = outputFeatures
    ? featuresToUniforms(outputFeatures)
    : {
        ...DEFAULT_UNIFORMS,
        uSpikiness: DEFAULT_UNIFORMS.uSpikiness + cues.spikinessBoost,
        uScatter: DEFAULT_UNIFORMS.uScatter + cues.scatterBoost,
      };

  return (
    <>
      {soundA && (
        <ParticleCloud
          position={posA}
          color={getColor(soundA.colorIndex)}
          targetUniforms={featuresToUniforms(soundA.features)}
          entranceProgress={entranceA}
          ghostOpacity={1}
          onClick={() => onClickCloud(soundA.id)}
        />
      )}
      {soundB && (
        <ParticleCloud
          position={posB}
          color={getColor(soundB.colorIndex)}
          targetUniforms={featuresToUniforms(soundB.features)}
          entranceProgress={entranceB}
          ghostOpacity={1}
          onClick={() => onClickCloud(soundB.id)}
        />
      )}
      {showOutput && (
        <ParticleCloud
          position={posOut}
          color={outputColor}
          targetUniforms={outputUniforms}
          entranceProgress={entranceOut}
          ghostOpacity={ghostOpacity}
          onClick={phase === 'complete' && outputId ? () => onClickCloud(outputId) : undefined}
        />
      )}
    </>
  );
}
