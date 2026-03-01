import { useReducer, useCallback } from 'react';
import { reducer, initialState } from './state/reducer';
import { uploadFile, analyzeAudio } from './api/upload';
import { useMorph } from './hooks/useMorph';
import { useAudioPlayer } from './hooks/useAudioPlayer';
import { DotGrid } from './canvas/DotGrid';
import { SceneRoot } from './three/SceneRoot';
import { CloudLayout } from './three/CloudLayout';
import { Layout } from './components/Layout';
import { FooterBar } from './components/FooterBar';
import { ThoughtOverlay } from './components/ThoughtOverlay';

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const { startMorph } = useMorph(dispatch);
  const player = useAudioPlayer();

  const handleUpload = useCallback(
    async (slot: 'A' | 'B', file: File) => {
      try {
        dispatch({ type: 'SET_PHASE', phase: 'uploading' });
        const { id } = await uploadFile(file);

        const colorIndex = state.nextColorIndex;
        if (slot === 'A') {
          dispatch({ type: 'SET_SOUND_A', id, name: file.name, colorIndex });
        } else {
          dispatch({ type: 'SET_SOUND_B', id, name: file.name, colorIndex });
        }

        dispatch({ type: 'SET_PHASE', phase: 'analyzing' });
        const analysis = await analyzeAudio(id);

        if (slot === 'A') {
          dispatch({
            type: 'SET_FEATURES_A',
            features: analysis.features,
            classification: analysis.classification,
          });
        } else {
          dispatch({
            type: 'SET_FEATURES_B',
            features: analysis.features,
            classification: analysis.classification,
          });
        }

        dispatch({ type: 'SET_PHASE', phase: 'ready' });
      } catch (err) {
        dispatch({ type: 'SET_ERROR', error: String(err) });
      }
    },
    [state.nextColorIndex],
  );

  const handleGo = useCallback(() => {
    if (!state.soundA) return;
    startMorph(state.soundA.id, state.soundB?.id, state.intent);
  }, [state.soundA, state.soundB, state.intent, startMorph]);

  const handleClickCloud = useCallback(
    (id: string) => {
      player.toggle(id);
    },
    [player.toggle],
  );

  const isBusy = state.phase === 'uploading' || state.phase === 'analyzing' || state.phase === 'morphing';
  const canGo = !!state.soundA && state.intent.trim().length > 0 && !isBusy;

  return (
    <>
      <DotGrid isMorphing={state.phase === 'morphing'} />
      <SceneRoot>
        <CloudLayout
          soundA={state.soundA}
          soundB={state.soundB}
          phase={state.phase}
          currentStep={state.currentStep}
          morphSteps={state.morphSteps}
          outputFeatures={state.outputFeatures}
          outputId={state.outputId}
          onClickCloud={handleClickCloud}
        />
      </SceneRoot>
      <Layout
        footer={
          <FooterBar
            soundAName={state.soundA?.name}
            soundBName={state.soundB?.name}
            intent={state.intent}
            onUploadA={(f) => handleUpload('A', f)}
            onUploadB={(f) => handleUpload('B', f)}
            onIntentChange={(v) => dispatch({ type: 'SET_INTENT', intent: v })}
            onGo={handleGo}
            canGo={canGo}
            isBusy={isBusy}
          />
        }
      >
        <ThoughtOverlay
          steps={state.morphSteps}
          currentStep={state.currentStep}
          phase={state.phase}
        />
        {state.error && (
          <div
            style={{
              position: 'fixed',
              top: 48,
              left: 24,
              right: 24,
              zIndex: 10,
              fontFamily: 'monospace',
              fontSize: 12,
              color: '#c00',
            }}
          >
            {state.error}
          </div>
        )}
      </Layout>
    </>
  );
}
