export type Phase = 'idle' | 'loading' | 'playing' | 'error';
export type Mode = 'generate' | 'splice';

export interface PlanSegment {
  id: number;
  reason: string;
}

export interface TrackFeatures {
  energy: number;
  brightness: number;
  darkness: number;
  spread: number;
}

export interface AppState {
  phase: Phase;
  mode: Mode;
  selectedVibe: number;
  journey: string;
  spliceCount: number;
  spliceClipS: number;
  audioUrl: string | null;
  plan: PlanSegment[];
  outputFeatures: TrackFeatures | null;
  vibeLib: string | null;
  error: string | null;
}
