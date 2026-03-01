import { AppState } from '../types';
import { Action } from './actions';

export const initialState: AppState = {
  phase: 'idle',
  soundA: null,
  soundB: null,
  intent: '',
  outputId: null,
  outputFeatures: null,
  outputClassification: null,
  morphSteps: [],
  currentStep: 0,
  error: null,
  nextColorIndex: 0,
};

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'SET_PHASE':
      return { ...state, phase: action.phase, error: action.phase === 'error' ? state.error : null };

    case 'SET_SOUND_A':
      return {
        ...state,
        soundA: { id: action.id, name: action.name, features: null, classification: null, colorIndex: action.colorIndex },
        nextColorIndex: action.colorIndex + 1,
      };

    case 'SET_SOUND_B':
      return {
        ...state,
        soundB: { id: action.id, name: action.name, features: null, classification: null, colorIndex: action.colorIndex },
        nextColorIndex: action.colorIndex + 1,
      };

    case 'SET_FEATURES_A':
      return {
        ...state,
        soundA: state.soundA ? { ...state.soundA, features: action.features, classification: action.classification } : null,
      };

    case 'SET_FEATURES_B':
      return {
        ...state,
        soundB: state.soundB ? { ...state.soundB, features: action.features, classification: action.classification } : null,
      };

    case 'SET_INTENT':
      return { ...state, intent: action.intent };

    case 'MORPH_STEP':
      return {
        ...state,
        morphSteps: [...state.morphSteps, action.step],
        currentStep: action.step.step_number,
      };

    case 'MORPH_COMPLETE':
      return {
        ...state,
        phase: 'complete',
        outputId: action.output_id,
        outputFeatures: action.features,
        outputClassification: action.classification,
      };

    case 'SET_ERROR':
      return { ...state, phase: 'error', error: action.error };

    case 'RESET':
      return { ...initialState };

    default:
      return state;
  }
}
