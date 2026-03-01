interface Props {
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
}

export function IntentInput({ value, onChange, disabled }: Props) {
  return (
    <input
      type="text"
      placeholder="Describe what you want..."
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      style={{
        border: '1px solid var(--border)',
        padding: '8px 16px',
        fontSize: 13,
        fontFamily: 'Inter, sans-serif',
        background: 'transparent',
        color: 'var(--text)',
        outline: 'none',
        flex: 1,
        minWidth: 160,
        opacity: disabled ? 0.5 : 1,
      }}
    />
  );
}
