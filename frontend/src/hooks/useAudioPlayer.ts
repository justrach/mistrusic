import { useRef, useCallback, useState } from 'react';

export function useAudioPlayer() {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const rafRef = useRef<number>(0);

  const stopTracking = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
  }, []);

  const startTracking = useCallback(() => {
    const tick = () => {
      if (audioRef.current) {
        setCurrentTime(audioRef.current.currentTime);
        setDuration(audioRef.current.duration || 0);
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    tick();
  }, []);

  const stop = useCallback(() => {
    stopTracking();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    setIsPlaying(false);
    setCurrentTime(0);
  }, [stopTracking]);

  const play = useCallback((url: string) => {
    stop();
    const audio = new Audio(url);
    audio.onended = () => {
      setIsPlaying(false);
      stopTracking();
    };
    audio.onloadedmetadata = () => {
      setDuration(audio.duration);
    };
    audioRef.current = audio;
    setIsPlaying(true);
    startTracking();
    audio.play().catch((err) => {
      console.warn('Audio play failed:', err);
      setIsPlaying(false);
    });
  }, [stop, startTracking, stopTracking]);

  const togglePause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audio.paused) {
      audio.play();
      setIsPlaying(true);
      startTracking();
    } else {
      audio.pause();
      setIsPlaying(false);
      stopTracking();
    }
  }, [startTracking, stopTracking]);

  return { play, stop, togglePause, isPlaying, currentTime, duration, audioRef };
}
