import { useState, useCallback } from 'react';
import { DeckTrack } from '../types';
import { mix } from '../api/generate';
import { useAudioPlayer } from '../hooks/useAudioPlayer';
import { VIBE_COLORS } from '../constants';

const VIBES = ['trance', 'haunted', 'hiphop'] as const;
const TRACK_COUNT = 100;

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

export function StudioPage() {
  const [deck, setDeck] = useState<DeckTrack[]>([]);
  const [clipS, setClipS] = useState(30);
  const [isMixing, setIsMixing] = useState(false);
  const player = useAudioPlayer();

  const addTrack = useCallback((id: number, vibe: string) => {
    setDeck((prev) => [...prev, { id, vibe, volume: 0.8, offset_s: 0 }]);
  }, []);

  const removeTrack = useCallback((index: number) => {
    setDeck((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const updateTrack = useCallback((index: number, updates: Partial<DeckTrack>) => {
    setDeck((prev) =>
      prev.map((t, i) => (i === index ? { ...t, ...updates } : t))
    );
  }, []);

  const handleMix = useCallback(async () => {
    if (deck.length === 0) return;
    setIsMixing(true);
    try {
      const result = await mix(deck, clipS);
      player.play(result.audioUrl);
    } catch (err) {
      console.error('Mix failed:', err);
    } finally {
      setIsMixing(false);
    }
  }, [deck, clipS, player]);

  const handlePreview = useCallback((id: number, vibe: string) => {
    const url = `http://localhost:8000/track/${id}/audio?vibe=${vibe}`;
    player.play(url);
  }, [player]);

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        display: 'flex',
        pointerEvents: 'auto',
      }}
    >
      {/* Track Browser */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '80px 16px 16px',
          borderRight: '1px solid var(--border)',
        }}
      >
        <h2
          style={{
            fontSize: 14,
            fontWeight: 600,
            fontFamily: 'monospace',
            color: 'var(--text)',
            marginBottom: 16,
          }}
        >
          TRACK BROWSER
        </h2>
        {VIBES.map((vibe) => (
          <div key={vibe} style={{ marginBottom: 24 }}>
            <div
              style={{
                fontSize: 11,
                fontWeight: 600,
                fontFamily: 'monospace',
                color: VIBE_COLORS[vibe],
                marginBottom: 8,
                textTransform: 'uppercase',
              }}
            >
              {vibe}
            </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(40px, 1fr))',
                gap: 4,
              }}
            >
              {Array.from({ length: TRACK_COUNT }, (_, i) => i + 1).map((id) => (
                <button
                  key={id}
                  onClick={(e) => {
                    if (e.shiftKey) {
                      handlePreview(id, vibe);
                    } else {
                      addTrack(id, vibe);
                    }
                  }}
                  style={{
                    padding: '6px 4px',
                    fontSize: 10,
                    fontFamily: 'monospace',
                    color: 'var(--text)',
                    background: '#fff',
                    border: '1px solid var(--border)',
                    borderRadius: 4,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = VIBE_COLORS[vibe];
                    e.currentTarget.style.background = VIBE_COLORS[vibe] + '10';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border)';
                    e.currentTarget.style.background = '#fff';
                  }}
                >
                  {id}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Mix Deck */}
      <div
        style={{
          width: 400,
          display: 'flex',
          flexDirection: 'column',
          padding: '80px 16px 16px',
          background: 'rgba(0,0,0,0.02)',
        }}
      >
        <h2
          style={{
            fontSize: 14,
            fontWeight: 600,
            fontFamily: 'monospace',
            color: 'var(--text)',
            marginBottom: 16,
          }}
        >
          MIX DECK ({deck.length})
        </h2>

        <div style={{ flex: 1, overflowY: 'auto', marginBottom: 16 }}>
          {deck.length === 0 ? (
            <div
              style={{
                fontSize: 11,
                fontFamily: 'monospace',
                color: 'var(--muted)',
                textAlign: 'center',
                padding: 32,
              }}
            >
              Click tracks to add
              <br />
              Shift+click to preview
            </div>
          ) : (
            deck.map((t, i) => (
              <div
                key={i}
                style={{
                  padding: 12,
                  marginBottom: 8,
                  background: '#fff',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  borderLeft: `3px solid ${VIBE_COLORS[t.vibe]}`,
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: 8,
                  }}
                >
                  <span
                    style={{
                      fontSize: 11,
                      fontFamily: 'monospace',
                      fontWeight: 600,
                      color: 'var(--text)',
                    }}
                  >
                    #{t.id} · {t.vibe}
                  </span>
                  <button
                    onClick={() => removeTrack(i)}
                    style={{
                      fontSize: 10,
                      fontFamily: 'monospace',
                      color: 'var(--muted)',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      padding: 4,
                    }}
                  >
                    ✕
                  </button>
                </div>

                <label
                  style={{
                    display: 'block',
                    fontSize: 9,
                    fontFamily: 'monospace',
                    color: 'var(--muted)',
                    marginBottom: 4,
                  }}
                >
                  VOLUME: {(t.volume * 100).toFixed(0)}%
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={t.volume}
                  onChange={(e) =>
                    updateTrack(i, { volume: parseFloat(e.target.value) })
                  }
                  style={{ width: '100%', marginBottom: 8 }}
                />

                <label
                  style={{
                    display: 'block',
                    fontSize: 9,
                    fontFamily: 'monospace',
                    color: 'var(--muted)',
                    marginBottom: 4,
                  }}
                >
                  OFFSET: {t.offset_s.toFixed(1)}s
                </label>
                <input
                  type="range"
                  min="0"
                  max={clipS}
                  step="0.1"
                  value={t.offset_s}
                  onChange={(e) =>
                    updateTrack(i, { offset_s: parseFloat(e.target.value) })
                  }
                  style={{ width: '100%' }}
                />
              </div>
            ))
          )}
        </div>

        <div style={{ marginBottom: 16 }}>
          <label
            style={{
              display: 'block',
              fontSize: 10,
              fontFamily: 'monospace',
              color: 'var(--text)',
              marginBottom: 8,
            }}
          >
            CLIP LENGTH: {clipS}s
          </label>
          <input
            type="range"
            min="10"
            max="60"
            step="5"
            value={clipS}
            onChange={(e) => setClipS(parseInt(e.target.value))}
            style={{ width: '100%' }}
          />
        </div>

        <button
          onClick={handleMix}
          disabled={deck.length === 0 || isMixing}
          style={{
            padding: '12px 16px',
            fontSize: 12,
            fontFamily: 'monospace',
            fontWeight: 600,
            color: deck.length === 0 || isMixing ? 'var(--muted)' : '#fff',
            background:
              deck.length === 0 || isMixing ? 'var(--border)' : 'var(--text)',
            border: 'none',
            borderRadius: 6,
            cursor: deck.length === 0 || isMixing ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s ease',
          }}
        >
          {isMixing ? 'MIXING...' : 'MIX + PLAY'}
        </button>

        {player.isPlaying && (
          <div
            style={{
              marginTop: 16,
              padding: 12,
              background: '#fff',
              border: '1px solid var(--border)',
              borderRadius: 6,
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: 10,
                fontFamily: 'monospace',
                color: 'var(--muted)',
                marginBottom: 8,
              }}
            >
              <span>{formatTime(player.currentTime)}</span>
              <span>{formatTime(player.duration)}</span>
            </div>
            <div
              style={{
                width: '100%',
                height: 4,
                background: 'var(--border)',
                borderRadius: 2,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${(player.currentTime / player.duration) * 100}%`,
                  height: '100%',
                  background: 'var(--text)',
                  transition: 'width 0.1s linear',
                }}
              />
            </div>
            <button
              onClick={player.togglePause}
              style={{
                marginTop: 8,
                width: '100%',
                padding: '8px',
                fontSize: 10,
                fontFamily: 'monospace',
                color: 'var(--text)',
                background: '#fff',
                border: '1px solid var(--border)',
                borderRadius: 4,
                cursor: 'pointer',
              }}
            >
              {player.isPlaying ? 'PAUSE' : 'PLAY'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
