import { useRef, useState, useCallback } from 'react';
import { audioUrl } from '../api/upload';

interface AudioPlayer {
  play: (id: string) => void;
  stop: () => void;
  toggle: (id: string) => void;
  isPlaying: boolean;
  currentId: string | null;
}

export function useAudioPlayer(): AudioPlayer {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [currentId, setCurrentId] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    setIsPlaying(false);
    setCurrentId(null);
  }, []);

  const play = useCallback((id: string) => {
    stop();
    const audio = new Audio(audioUrl(id));
    audio.onended = () => {
      setIsPlaying(false);
      setCurrentId(null);
    };
    audioRef.current = audio;
    setCurrentId(id);
    setIsPlaying(true);
    audio.play();
  }, [stop]);

  const toggle = useCallback((id: string) => {
    if (currentId === id && isPlaying) {
      stop();
    } else {
      play(id);
    }
  }, [currentId, isPlaying, play, stop]);

  return { play, stop, toggle, isPlaying, currentId };
}
