import { VIBES } from '../constants';

interface Props {
  selectedIndex: number;
  onSelect: (index: number) => void;
}

export function VibePicker({ selectedIndex, onSelect }: Props) {
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 6,
        justifyContent: 'center',
      }}
    >
      {VIBES.map((vibe, i) => {
        const isSelected = i === selectedIndex;
        return (
          <button
            key={i}
            onClick={() => onSelect(i)}
            style={{
              border: 'none',
              borderRadius: 20,
              padding: '6px 14px',
              fontSize: 12,
              fontFamily: 'Inter, sans-serif',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              background: isSelected ? '#1A1A1A' : 'rgba(0,0,0,0.06)',
              color: isSelected ? '#fff' : '#1A1A1A',
            }}
          >
            {vibe.emoji} {vibe.label}
          </button>
        );
      })}
    </div>
  );
}
