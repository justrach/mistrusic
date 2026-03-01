export function ArchPage() {
  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        overflowY: 'auto',
        padding: '80px 24px 24px',
        pointerEvents: 'auto',
      }}
    >
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <h1
          style={{
            fontSize: 24,
            fontWeight: 600,
            fontFamily: 'Inter, system-ui, sans-serif',
            color: 'var(--text)',
            marginBottom: 8,
          }}
        >
          Architecture
        </h1>
        <p
          style={{
            fontSize: 13,
            fontFamily: 'monospace',
            color: 'var(--muted)',
            marginBottom: 32,
          }}
        >
          System pipeline and rendering chain
        </p>

        {/* Pipeline Flow */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 48 }}>
          <PipelineCard
            title="MIDI Library"
            desc="100 procedural MIDI patterns per vibe (trance, haunted, hiphop)"
            color="#8B5CF6"
          />
          <Arrow />
          <PipelineCard
            title="Mistral Planner"
            desc="LLM-driven segment planning based on user prompt"
            color="#EC4899"
          />
          <Arrow />
          <PipelineCard
            title="Render Engine"
            desc="FluidSynth + pedalboard FX chain per vibe"
            color="#10B981"
          />
          <Arrow />
          <PipelineCard
            title="Cache Layer"
            desc="Pre-rendered WAV cache for instant playback"
            color="#F59E0B"
          />
          <Arrow />
          <PipelineCard
            title="Frontend"
            desc="React/Vite UI with real-time playback and mixing"
            color="#3B82F6"
          />
        </div>

        {/* FX Chains */}
        <h2
          style={{
            fontSize: 18,
            fontWeight: 600,
            fontFamily: 'Inter, system-ui, sans-serif',
            color: 'var(--text)',
            marginBottom: 16,
          }}
        >
          FX Chains
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: 16, marginBottom: 48 }}>
          <FXCard
            vibe="trance"
            chain={['Reverb (room=0.7)', 'Chorus (rate=1.5Hz)', 'Compressor (-12dB)', 'Limiter (-1dB)']}
          />
          <FXCard
            vibe="haunted"
            chain={['Reverb (room=0.9)', 'Distortion (gain=15dB)', 'Phaser (rate=0.5Hz)', 'Limiter (-1dB)']}
          />
          <FXCard
            vibe="hiphop"
            chain={['Reverb (room=0.3)', 'Compressor (-18dB)', 'Limiter (-1dB)']}
          />
        </div>

        {/* Stats */}
        <div
          style={{
            display: 'flex',
            gap: 24,
            padding: 16,
            background: 'rgba(0,0,0,0.03)',
            border: '1px solid var(--border)',
            borderRadius: 8,
          }}
        >
          <Stat label="MIDI Patterns" value="300" />
          <Stat label="Sample Rate" value="44.1kHz" />
          <Stat label="Vibes" value="3" />
          <Stat label="Cache Size" value="~2GB" />
        </div>
      </div>
    </div>
  );
}

function PipelineCard({ title, desc, color }: { title: string; desc: string; color: string }) {
  return (
    <div
      style={{
        padding: 16,
        background: '#fff',
        border: '1px solid var(--border)',
        borderRadius: 8,
        borderLeft: `4px solid ${color}`,
      }}
    >
      <div
        style={{
          fontSize: 14,
          fontWeight: 600,
          fontFamily: 'monospace',
          color: 'var(--text)',
          marginBottom: 4,
        }}
      >
        {title}
      </div>
      <div
        style={{
          fontSize: 12,
          fontFamily: 'monospace',
          color: 'var(--muted)',
        }}
      >
        {desc}
      </div>
    </div>
  );
}

function Arrow() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', margin: '-8px 0' }}>
      <div
        style={{
          width: 2,
          height: 24,
          background: 'var(--border)',
        }}
      />
    </div>
  );
}

function FXCard({ vibe, chain }: { vibe: string; chain: string[] }) {
  const colors: Record<string, string> = {
    trance: '#8B5CF6',
    haunted: '#10B981',
    hiphop: '#F59E0B',
  };

  return (
    <div
      style={{
        padding: 16,
        background: '#fff',
        border: '1px solid var(--border)',
        borderRadius: 8,
      }}
    >
      <div
        style={{
          fontSize: 13,
          fontWeight: 600,
          fontFamily: 'monospace',
          color: colors[vibe] || 'var(--text)',
          marginBottom: 12,
          textTransform: 'uppercase',
        }}
      >
        {vibe}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {chain.map((fx, i) => (
          <div
            key={i}
            style={{
              fontSize: 11,
              fontFamily: 'monospace',
              color: 'var(--muted)',
              paddingLeft: 8,
              borderLeft: '2px solid var(--border)',
            }}
          >
            {fx}
          </div>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div
        style={{
          fontSize: 10,
          fontFamily: 'monospace',
          color: 'var(--muted)',
          marginBottom: 4,
          textTransform: 'uppercase',
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 18,
          fontWeight: 600,
          fontFamily: 'monospace',
          color: 'var(--text)',
        }}
      >
        {value}
      </div>
    </div>
  );
}
