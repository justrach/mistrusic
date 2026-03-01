import { UploadZone } from './UploadZone';
import { IntentInput } from './IntentInput';

interface Props {
  soundAName?: string;
  soundBName?: string;
  intent: string;
  onUploadA: (file: File) => void;
  onUploadB: (file: File) => void;
  onIntentChange: (v: string) => void;
  onGo: () => void;
  canGo: boolean;
  isBusy: boolean;
}

export function FooterBar({
  soundAName,
  soundBName,
  intent,
  onUploadA,
  onUploadB,
  onIntentChange,
  onGo,
  canGo,
  isBusy,
}: Props) {
  return (
    <footer
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        borderTop: '1px solid var(--border)',
        background: 'var(--bg)',
        padding: '12px 24px',
        display: 'flex',
        gap: 12,
        alignItems: 'center',
        zIndex: 10,
      }}
    >
      <UploadZone label="Sound A" fileName={soundAName} onFile={onUploadA} disabled={isBusy} />
      <UploadZone label="Sound B" fileName={soundBName} onFile={onUploadB} disabled={isBusy} />
      <IntentInput value={intent} onChange={onIntentChange} disabled={isBusy} />
      <button
        onClick={onGo}
        disabled={!canGo || isBusy}
        style={{
          background: canGo && !isBusy ? 'var(--text)' : 'var(--border)',
          color: canGo && !isBusy ? '#fff' : 'var(--muted)',
          border: 'none',
          padding: '8px 24px',
          fontSize: 13,
          fontFamily: 'Inter, sans-serif',
          fontWeight: 500,
          cursor: canGo && !isBusy ? 'pointer' : 'default',
          transition: 'background 0.15s',
        }}
      >
        Go
      </button>
    </footer>
  );
}
