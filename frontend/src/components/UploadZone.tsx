import { useRef, useState, useCallback } from 'react';

interface Props {
  label: string;
  fileName?: string;
  onFile: (file: File) => void;
  disabled?: boolean;
}

export function UploadZone({ label, fileName, onFile, disabled }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      if (disabled) return;
      const file = e.dataTransfer.files[0];
      if (file) onFile(file);
    },
    [onFile, disabled],
  );

  return (
    <div
      onClick={() => !disabled && inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setIsDragOver(true);
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
      style={{
        border: `1px solid ${isDragOver ? 'var(--text)' : 'var(--border)'}`,
        padding: '8px 16px',
        cursor: disabled ? 'default' : 'pointer',
        minWidth: 120,
        textAlign: 'center',
        fontSize: 13,
        color: fileName ? 'var(--text)' : 'var(--muted)',
        opacity: disabled ? 0.5 : 1,
        transition: 'border-color 0.15s',
        background: 'transparent',
      }}
    >
      {fileName || label}
      <input
        ref={inputRef}
        type="file"
        accept="audio/*"
        style={{ display: 'none' }}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
        }}
      />
    </div>
  );
}
