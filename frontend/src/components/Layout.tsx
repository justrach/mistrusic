import { ReactNode } from 'react';
import { Page } from '../types';

interface Props {
  children: ReactNode;
  footer: ReactNode;
  currentPage?: Page;
}

const NAV_ITEMS: { page: Page; label: string; hash: string }[] = [
  { page: 'generate', label: 'Generate', hash: '#/' },
  { page: 'studio', label: 'Studio', hash: '#/studio' },
  { page: 'arch', label: 'Architecture', hash: '#/arch' },
];

export function Layout({ children, footer, currentPage = 'generate' }: Props) {
  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', zIndex: 2, pointerEvents: 'none' }}>
      <header
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          padding: '16px 24px',
          zIndex: 10,
          pointerEvents: 'none',
          display: 'flex',
          alignItems: 'center',
          gap: 24,
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
        <nav style={{ display: 'flex', gap: 4, pointerEvents: 'auto' }}>
          {NAV_ITEMS.map(({ page, label, hash }) => (
            <a
              key={page}
              href={hash}
              style={{
                fontSize: 11,
                fontFamily: 'monospace',
                fontWeight: currentPage === page ? 600 : 400,
                color: currentPage === page ? 'var(--text)' : 'var(--muted)',
                textDecoration: 'none',
                padding: '4px 10px',
                borderRadius: 4,
                background: currentPage === page ? 'rgba(0,0,0,0.05)' : 'transparent',
                transition: 'all 0.15s ease',
              }}
            >
              {label}
            </a>
          ))}
        </nav>
      </header>
      {children}
      {footer}
    </div>
  );
}
