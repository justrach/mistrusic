import { useRef, useCallback } from 'react';
import { connectMorph, MorphMessage } from '../api/morph';
import { Action } from '../state/actions';
import { AudioFeatures, Classification } from '../types';

export function useMorph(dispatch: React.Dispatch<Action>) {
  const wsRef = useRef<WebSocket | null>(null);

  const startMorph = useCallback(
    (soundAId: string, soundBId: string | undefined, intent: string) => {
      // Close any existing connection
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      dispatch({ type: 'SET_PHASE', phase: 'morphing' });

      wsRef.current = connectMorph(
        soundAId,
        soundBId,
        intent,
        (msg: MorphMessage) => {
          if (msg.type === 'step') {
            dispatch({
              type: 'MORPH_STEP',
              step: {
                step_number: msg.step_number ?? 0,
                model_output: msg.model_output ?? '',
                observations: msg.observations ?? '',
              },
            });
          } else if (msg.type === 'complete') {
            dispatch({
              type: 'MORPH_COMPLETE',
              output_id: msg.output_id ?? '',
              features: (msg.features as unknown as AudioFeatures) ?? {
                duration: 0,
                rms: 0,
                centroid: 0,
                tempo: 0,
                zcr: 0,
              },
              classification: (msg.classification as Classification[]) ?? [],
            });
          }
        },
        (err: string) => {
          dispatch({ type: 'SET_ERROR', error: err });
        },
        () => {
          wsRef.current = null;
        },
      );
    },
    [dispatch],
  );

  const cancelMorph = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  return { startMorph, cancelMorph };
}
