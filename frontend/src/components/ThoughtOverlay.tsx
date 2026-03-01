import { PlanSegment } from '../types';

interface Props {
  plan: PlanSegment[];
  phase: string;
}

export function ThoughtOverlay({ plan, phase }: Props) {
  if (phase !== 'loading' && phase !== 'playing') return null;
  if (phase === 'playing' && plan.length === 0) return null;

  return (
    <div
      style={{
        position: 'fixed',
        right: 24,
        top: '50%',
        transform: 'translateY(-50%)',
        width: 260,
        maxHeight: '40vh',
        zIndex: 10,
        pointerEvents: 'none',
      }}
    >
      {phase === 'loading' && (
        <div
          style={{
            fontFamily: 'monospace',
            fontSize: 11,
            color: 'var(--muted)',
            lineHeight: 1.6,
            fontWeight: 600,
            letterSpacing: '0.04em',
            animation: 'pulse 1.5s ease-in-out infinite',
          }}
        >
          Planning journey...
        </div>
      )}

      {phase === 'playing' && plan.length > 0 && (
        <>
          <div
            style={{
              fontFamily: 'monospace',
              fontSize: 11,
              color: 'var(--muted)',
              lineHeight: 1.6,
              marginBottom: 8,
              fontWeight: 600,
              letterSpacing: '0.04em',
            }}
          >
            Journey Plan
          </div>
          <div style={{ maxHeight: 'calc(40vh - 24px)', overflow: 'hidden' }}>
            {plan.map((segment, i) => (
              <div
                key={segment.id}
                style={{
                  fontFamily: 'monospace',
                  fontSize: 10,
                  color: 'var(--muted)',
                  lineHeight: 1.5,
                  marginBottom: 6,
                  opacity: 0,
                  animation: `fadeIn 0.3s ease forwards ${i * 0.1}s`,
                }}
              >
                <span style={{ color: 'var(--text)', opacity: 0.3, marginRight: 4 }}>
                  #{String(segment.id).padStart(3, '0')}
                </span>
                {segment.reason}
              </div>
            ))}
          </div>
        </>
      )}

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
