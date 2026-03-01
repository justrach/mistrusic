import { useRef, useCallback } from 'react';
import { audioUrl } from '../api/upload';

export function useAudioPlayer() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const currentIdRef = useRef<string | null>(null);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    currentIdRef.current = null;
  }, []);

  const play = useCallback((id: string) => {
    stop();
    const audio = new Audio(audioUrl(id));
    audio.onended = () => {
      currentIdRef.current = null;
      audioRef.current = null;
    };
    audioRef.current = audio;
    currentIdRef.current = id;
    audio.play().catch((err) => {
      console.warn('Audio play failed:', err);
    });
  }, [stop]);

  const toggle = useCallback((id: string) => {
    if (currentIdRef.current === id && audioRef.current && !audioRef.current.paused) {
      stop();
    } else {
      play(id);
    }
  }, [play, stop]);

  return { play, stop, toggle };
}
