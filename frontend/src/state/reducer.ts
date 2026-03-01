import { AppState, Phase, Mode, PlanSegment, TrackFeatures } from '../types';
import { DEFAULT_SPLICE_COUNT, DEFAULT_SPLICE_CLIP_S } from '../constants';

export type Action =
  | { type: 'SET_PHASE'; phase: Phase }
  | { type: 'SET_MODE'; mode: Mode }
  | { type: 'SET_VIBE'; index: number }
  | { type: 'SET_JOURNEY'; journey: string }
  | { type: 'SET_SPLICE_COUNT'; count: number }
  | { type: 'SET_SPLICE_CLIP_S'; clipS: number }
  | { type: 'GENERATION_COMPLETE'; audioUrl: string; plan: PlanSegment[]; vibeLib: string }
  | { type: 'SPLICE_COMPLETE'; audioUrl: string }
  | { type: 'SET_OUTPUT_FEATURES'; features: TrackFeatures }
  | { type: 'SET_ERROR'; error: string }
  | { type: 'RESET' };

export const initialState: AppState = {
  phase: 'idle',
  mode: 'generate',
  selectedVibe: -1,
  journey: '',
  spliceCount: DEFAULT_SPLICE_COUNT,
  spliceClipS: DEFAULT_SPLICE_CLIP_S,
  audioUrl: null,
  plan: [],
  outputFeatures: null,
  vibeLib: null,
  error: null,
};

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'SET_PHASE':
      return { ...state, phase: action.phase, error: action.phase === 'error' ? state.error : null };

    case 'SET_MODE':
      return { ...state, mode: action.mode };

    case 'SET_VIBE':
      return { ...state, selectedVibe: action.index };

    case 'SET_JOURNEY':
      return { ...state, journey: action.journey };

    case 'SET_SPLICE_COUNT':
      return { ...state, spliceCount: action.count };

    case 'SET_SPLICE_CLIP_S':
      return { ...state, spliceClipS: action.clipS };

    case 'GENERATION_COMPLETE': {
      // Revoke previous blob URL
      if (state.audioUrl) URL.revokeObjectURL(state.audioUrl);
      return {
        ...state,
        phase: 'playing',
        audioUrl: action.audioUrl,
        plan: action.plan,
        vibeLib: action.vibeLib,
        error: null,
      };
    }

    case 'SPLICE_COMPLETE': {
      if (state.audioUrl) URL.revokeObjectURL(state.audioUrl);
      return {
        ...state,
        phase: 'playing',
        audioUrl: action.audioUrl,
        plan: [],
        error: null,
      };
    }

    case 'SET_OUTPUT_FEATURES':
      return { ...state, outputFeatures: action.features };

    case 'SET_ERROR':
      return { ...state, phase: 'error', error: action.error };

    case 'RESET': {
      if (state.audioUrl) URL.revokeObjectURL(state.audioUrl);
      return { ...initialState };
    }

    default:
      return state;
  }
}
