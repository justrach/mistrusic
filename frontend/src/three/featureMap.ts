import { AudioFeatures } from '../types';

export interface ShaderUniforms {
  uScale: number;
  uSpikiness: number;
  uBreathRate: number;
  uScatter: number;
}

export const DEFAULT_UNIFORMS: ShaderUniforms = {
  uScale: 1.0,
  uSpikiness: 0.3,
  uBreathRate: 1.0,
  uScatter: 0.2,
};

export function featuresToUniforms(features: AudioFeatures | null): ShaderUniforms {
  if (!features) return DEFAULT_UNIFORMS;

  return {
    uScale: Math.min(2.1, 0.6 + features.rms * 3.0),
    uSpikiness: Math.max(0, Math.min(1, (features.centroid - 500) / 7500)),
    uBreathRate: features.tempo / 120,
    uScatter: Math.max(0, Math.min(1, features.zcr * 5.0)),
  };
}
