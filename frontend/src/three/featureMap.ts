import { TrackFeatures } from '../types';
import { BREATH_RATES } from '../constants';

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

export function featuresToUniforms(features: TrackFeatures | null, vibeLib?: string | null): ShaderUniforms {
  if (!features) return DEFAULT_UNIFORMS;

  return {
    uScale: 0.6 + features.energy * 2.0,
    uSpikiness: features.brightness,
    uBreathRate: vibeLib ? (BREATH_RATES[vibeLib] ?? 1.0) : 1.0,
    uScatter: Math.min(1, features.spread * 3.0),
  };
}
