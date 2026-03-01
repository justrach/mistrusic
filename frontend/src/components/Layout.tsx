import { ReactNode } from 'react';

interface Props {
  children: ReactNode;
  footer: ReactNode;
}

export function Layout({ children, footer }: Props) {
  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', zIndex: 2 }}>
      <header
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          padding: '16px 24px',
          zIndex: 10,
          pointerEvents: 'none',
        }}
      >
        <span
          style={{
            fontWeight: 600,
            fontSize: 14,
            letterSpacing: '0.08em',
            color: 'var(--text)',
            pointerEvents: 'auto',
          }}
        >
          MISTRUSIC
        </span>
      </header>
      {children}
      {footer}
    </div>
  );
}
