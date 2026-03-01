export interface AudioFeatures {
  duration: number;
  rms: number;
  centroid: number;
  tempo: number;
  zcr: number;
}

export interface Classification {
  label: string;
  confidence: number;
}

export interface SoundEntry {
  id: string;
  name: string;
  features: AudioFeatures | null;
  classification: Classification[] | null;
  colorIndex: number;
}

export interface MorphStep {
  step_number: number;
  model_output: string;
  observations: string;
}

export type Phase = 'idle' | 'uploading' | 'analyzing' | 'ready' | 'morphing' | 'complete' | 'error';

export interface AppState {
  phase: Phase;
  soundA: SoundEntry | null;
  soundB: SoundEntry | null;
  intent: string;
  outputId: string | null;
  outputFeatures: AudioFeatures | null;
  outputClassification: Classification[] | null;
  morphSteps: MorphStep[];
  currentStep: number;
  error: string | null;
  nextColorIndex: number;
}
