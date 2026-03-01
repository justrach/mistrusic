import { useReducer, useCallback } from 'react';
import { reducer, initialState } from './state/reducer';
import { generate, splice } from './api/generate';
import { useAudioPlayer } from './hooks/useAudioPlayer';
import { DotGrid } from './canvas/DotGrid';
import { SceneRoot } from './three/SceneRoot';
import { SingleCloudLayout } from './three/SingleCloudLayout';
import { Layout } from './components/Layout';
import { FooterBar } from './components/FooterBar';
import { ThoughtOverlay } from './components/ThoughtOverlay';
import { PlaybackBar } from './components/PlaybackBar';
import { VIBES } from './constants';

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const player = useAudioPlayer();

  const handleVibeSelect = useCallback((index: number) => {
    dispatch({ type: 'SET_VIBE', index });
    dispatch({ type: 'SET_JOURNEY', journey: VIBES[index].prompt });
  }, []);

  const handleGo = useCallback(async () => {
    const vibe = state.selectedVibe >= 0 ? VIBES[state.selectedVibe] : null;
    if (!vibe) return;

    dispatch({ type: 'SET_PHASE', phase: 'loading' });

    try {
      if (state.mode === 'generate') {
        const result = await generate(state.journey, vibe.lib);
        dispatch({
          type: 'GENERATION_COMPLETE',
          audioUrl: result.audioUrl,
          plan: result.plan,
          vibeLib: vibe.lib,
        });
        player.play(result.audioUrl);
      } else {
        const result = await splice(state.spliceCount, state.spliceClipS, vibe.lib);
        dispatch({ type: 'SPLICE_COMPLETE', audioUrl: result.audioUrl });
        player.play(result.audioUrl);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      dispatch({ type: 'SET_ERROR', error: msg });
    }
  }, [state.selectedVibe, state.mode, state.journey, state.spliceCount, state.spliceClipS, player]);

  const handleClickCloud = useCallback(() => {
    player.togglePause();
  }, [player]);

  const isBusy = state.phase === 'loading';
  const canGo = state.mode === 'generate'
    ? state.selectedVibe >= 0 && state.journey.trim().length > 0 && !isBusy
    : state.selectedVibe >= 0 && !isBusy;

  return (
    <>
      <DotGrid isMorphing={state.phase === 'loading'} />
      <SceneRoot>
        <SingleCloudLayout
          phase={state.phase}
          outputFeatures={state.outputFeatures}
          vibeLib={state.vibeLib}
          onClickCloud={handleClickCloud}
        />
      </SceneRoot>
      <Layout
        footer={
          <FooterBar
            mode={state.mode}
            selectedVibe={state.selectedVibe}
            journey={state.journey}
            spliceCount={state.spliceCount}
            spliceClipS={state.spliceClipS}
            canGo={canGo}
            isBusy={isBusy}
            onModeChange={(m) => dispatch({ type: 'SET_MODE', mode: m })}
            onVibeSelect={handleVibeSelect}
            onJourneyChange={(t) => dispatch({ type: 'SET_JOURNEY', journey: t })}
            onSpliceCountChange={(c) => dispatch({ type: 'SET_SPLICE_COUNT', count: c })}
            onSpliceClipSChange={(s) => dispatch({ type: 'SET_SPLICE_CLIP_S', clipS: s })}
            onGo={handleGo}
          />
        }
      >
        <ThoughtOverlay plan={state.plan} phase={state.phase} />
        {state.phase === 'playing' && (
          <PlaybackBar
            isPlaying={player.isPlaying}
            currentTime={player.currentTime}
            duration={player.duration}
            onToggle={player.togglePause}
          />
        )}
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
