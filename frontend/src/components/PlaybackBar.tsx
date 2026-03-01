interface Props {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  onToggle: () => void;
}

function formatTime(s: number): string {
  if (!isFinite(s) || s < 0) return '0:00';
  const mins = Math.floor(s / 60);
  const secs = Math.floor(s % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function PlaybackBar({ isPlaying, currentTime, duration, onToggle }: Props) {
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 160,
        left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        zIndex: 10,
        pointerEvents: 'auto',
      }}
    >
      <button
        onClick={onToggle}
        style={{
          border: 'none',
          background: 'none',
          cursor: 'pointer',
          fontSize: 16,
          color: 'var(--text)',
          fontFamily: 'monospace',
          padding: '4px 8px',
        }}
      >
        {isPlaying ? '\u23F8' : '\u25B6'}
      </button>

      <div
        style={{
          width: 200,
          height: 3,
          background: 'var(--border)',
          borderRadius: 2,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            height: '100%',
            width: `${progress}%`,
            background: 'var(--text)',
            borderRadius: 2,
            transition: 'width 0.1s linear',
          }}
        />
      </div>

      <span
        style={{
          fontFamily: 'monospace',
          fontSize: 10,
          color: 'var(--muted)',
          minWidth: 70,
        }}
      >
        {formatTime(currentTime)} / {formatTime(duration)}
      </span>
    </div>
  );
}
