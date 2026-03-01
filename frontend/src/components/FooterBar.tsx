import { Mode } from '../types';
import { VibePicker } from './VibePicker';

interface Props {
  mode: Mode;
  selectedVibe: number;
  journey: string;
  spliceCount: number;
  spliceClipS: number;
  canGo: boolean;
  isBusy: boolean;
  onModeChange: (mode: Mode) => void;
  onVibeSelect: (index: number) => void;
  onJourneyChange: (text: string) => void;
  onSpliceCountChange: (count: number) => void;
  onSpliceClipSChange: (clipS: number) => void;
  onGo: () => void;
}

const btnBase: React.CSSProperties = {
  border: 'none',
  borderRadius: 6,
  padding: '6px 16px',
  fontSize: 12,
  fontFamily: 'Inter, sans-serif',
  fontWeight: 500,
  cursor: 'pointer',
  transition: 'all 0.15s ease',
};

export function FooterBar({
  mode,
  selectedVibe,
  journey,
  spliceCount,
  spliceClipS,
  canGo,
  isBusy,
  onModeChange,
  onVibeSelect,
  onJourneyChange,
  onSpliceCountChange,
  onSpliceClipSChange,
  onGo,
}: Props) {
  return (
    <div
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        padding: '16px 24px 24px',
        zIndex: 10,
        pointerEvents: 'auto',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 12,
      }}
    >
      {/* Mode toggle */}
      <div style={{ display: 'flex', gap: 4, background: 'rgba(0,0,0,0.06)', borderRadius: 8, padding: 3 }}>
        {(['generate', 'splice'] as Mode[]).map((m) => (
          <button
            key={m}
            onClick={() => onModeChange(m)}
            style={{
              ...btnBase,
              background: mode === m ? '#1A1A1A' : 'transparent',
              color: mode === m ? '#fff' : '#1A1A1A',
            }}
          >
            {m === 'generate' ? 'Generate' : 'Splice'}
          </button>
        ))}
      </div>

      {/* Vibe picker */}
      <VibePicker selectedIndex={selectedVibe} onSelect={onVibeSelect} />

      {/* Input row */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', width: '100%', maxWidth: 600 }}>
        {mode === 'generate' ? (
          <input
            type="text"
            value={journey}
            onChange={(e) => onJourneyChange(e.target.value)}
            placeholder="Describe your musical journey..."
            style={{
              flex: 1,
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '10px 14px',
              fontSize: 13,
              fontFamily: 'Inter, sans-serif',
              background: 'rgba(255,255,255,0.8)',
              color: 'var(--text)',
              outline: 'none',
            }}
          />
        ) : (
          <>
            <label style={{ fontSize: 12, color: 'var(--muted)', whiteSpace: 'nowrap' }}>
              Clips
              <input
                type="number"
                min={1}
                max={10}
                value={spliceCount}
                onChange={(e) => onSpliceCountChange(Math.max(1, Math.min(10, Number(e.target.value))))}
                style={{
                  width: 50,
                  marginLeft: 6,
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  padding: '8px 10px',
                  fontSize: 13,
                  fontFamily: 'Inter, sans-serif',
                  background: 'rgba(255,255,255,0.8)',
                  color: 'var(--text)',
                  outline: 'none',
                }}
              />
            </label>
            <label style={{ fontSize: 12, color: 'var(--muted)', whiteSpace: 'nowrap' }}>
              Duration (s)
              <input
                type="number"
                min={1}
                max={30}
                step={0.5}
                value={spliceClipS}
                onChange={(e) => onSpliceClipSChange(Math.max(1, Math.min(30, Number(e.target.value))))}
                style={{
                  width: 60,
                  marginLeft: 6,
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  padding: '8px 10px',
                  fontSize: 13,
                  fontFamily: 'Inter, sans-serif',
                  background: 'rgba(255,255,255,0.8)',
                  color: 'var(--text)',
                  outline: 'none',
                }}
              />
            </label>
          </>
        )}
        <button
          onClick={onGo}
          disabled={!canGo || isBusy}
          style={{
            ...btnBase,
            padding: '10px 28px',
            fontSize: 13,
            fontWeight: 600,
            background: canGo && !isBusy ? '#1A1A1A' : 'rgba(0,0,0,0.15)',
            color: canGo && !isBusy ? '#fff' : 'rgba(0,0,0,0.3)',
            cursor: canGo && !isBusy ? 'pointer' : 'not-allowed',
          }}
        >
          {isBusy ? '...' : 'Go'}
        </button>
      </div>
    </div>
  );
}
