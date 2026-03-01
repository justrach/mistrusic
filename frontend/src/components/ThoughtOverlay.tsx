import { useRef, useEffect } from 'react';
import { MorphStep } from '../types';

interface Props {
  steps: MorphStep[];
  currentStep: number;
  phase: string;
}

function cleanText(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`[^`]+`/g, '')
    .trim()
    .split('\n')
    .filter((l) => l.trim())
    .slice(0, 3)
    .join(' ')
    .slice(0, 300);
}

export function ThoughtOverlay({ steps, currentStep, phase }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [steps.length]);

  if (phase !== 'morphing' && phase !== 'complete') return null;

  const stepLabel = phase === 'complete'
    ? 'Complete'
    : `Step ${currentStep + 1}`;

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
        {stepLabel}
      </div>
      <div
        ref={scrollRef}
        style={{
          maxHeight: 'calc(40vh - 24px)',
          overflow: 'hidden',
        }}
      >
        {steps.map((step, i) => {
          const text = cleanText(step.model_output || '');
          if (!text) return null;
          return (
            <div
              key={i}
              style={{
                fontFamily: 'monospace',
                fontSize: 10,
                color: 'var(--muted)',
                lineHeight: 1.5,
                marginBottom: 6,
                opacity: i === steps.length - 1 ? 1 : 0.5,
                transition: 'opacity 0.3s',
              }}
            >
              <span style={{ color: 'var(--text)', opacity: 0.3, marginRight: 4 }}>
                {step.step_number + 1}.
              </span>
              {text}
            </div>
          );
        })}
        {phase === 'morphing' && (
          <div
            style={{
              fontFamily: 'monospace',
              fontSize: 10,
              color: 'var(--muted)',
              animation: 'pulse 1.5s ease-in-out infinite',
            }}
          >
            ...
          </div>
        )}
      </div>
    </div>
  );
}
