import { AudioFeatures, Classification, MorphStep } from '../types';

export type Action =
  | { type: 'SET_PHASE'; phase: 'idle' | 'uploading' | 'analyzing' | 'ready' | 'morphing' | 'complete' | 'error' }
  | { type: 'SET_SOUND_A'; id: string; name: string; colorIndex: number }
  | { type: 'SET_SOUND_B'; id: string; name: string; colorIndex: number }
  | { type: 'SET_FEATURES_A'; features: AudioFeatures; classification: Classification[] }
  | { type: 'SET_FEATURES_B'; features: AudioFeatures; classification: Classification[] }
  | { type: 'SET_INTENT'; intent: string }
  | { type: 'MORPH_STEP'; step: MorphStep }
  | { type: 'MORPH_COMPLETE'; output_id: string; features: AudioFeatures; classification: Classification[] }
  | { type: 'SET_ERROR'; error: string }
  | { type: 'RESET' };
