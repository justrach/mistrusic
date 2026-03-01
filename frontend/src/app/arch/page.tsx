"use client";

const VIOLET = "border-violet-500/40 bg-violet-950/20";
const EMERALD = "border-emerald-500/40 bg-emerald-950/20";
const AMBER  = "border-amber-500/40 bg-amber-950/20";
const BLUE   = "border-blue-500/40 bg-blue-950/20";
const FUCHSIA = "border-fuchsia-500/40 bg-fuchsia-950/20";
const ZINC   = "border-white/10 bg-white/[0.03]";

function Arrow({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center gap-1 my-1">
      {label && <span className="text-[9px] text-zinc-600 font-mono">{label}</span>}
      <svg width="2" height="28" viewBox="0 0 2 28">
        <line x1="1" y1="0" x2="1" y2="22" stroke="#3f3f46" strokeWidth="1.5" strokeDasharray="3 2"/>
        <polygon points="1,28 -3,18 5,18" fill="#3f3f46"/>
      </svg>
    </div>
  );
}

function HArrow({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center px-2 self-center">
      {label && <span className="text-[9px] text-zinc-600 font-mono mb-0.5">{label}</span>}
      <svg width="40" height="2" viewBox="0 0 40 2">
        <line x1="0" y1="1" x2="34" y2="1" stroke="#3f3f46" strokeWidth="1.5" strokeDasharray="3 2"/>
        <polygon points="40,1 30,-3 30,5" fill="#3f3f46"/>
      </svg>
    </div>
  );
}

function Tag({ children, color = "text-zinc-500" }: { children: React.ReactNode; color?: string }) {
  return (
    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded bg-white/5 ${color}`}>
      {children}
    </span>
  );
}

function Card({
  title, subtitle, color, tags, children
}: {
  title: string; subtitle?: string; color: string;
  tags?: { label: string; color?: string }[];
  children?: React.ReactNode;
}) {
  return (
    <div className={`rounded-2xl border ${color} p-4 flex flex-col gap-2`}>
      <div>
        <div className="text-xs font-bold text-white">{title}</div>
        {subtitle && <div className="text-[10px] text-zinc-500 mt-0.5">{subtitle}</div>}
      </div>
      {tags && (
        <div className="flex flex-wrap gap-1">
          {tags.map(t => <Tag key={t.label} color={t.color}>{t.label}</Tag>)}
        </div>
      )}
      {children && <div className="text-[10px] text-zinc-400 leading-relaxed space-y-1">{children}</div>}
    </div>
  );
}

function Section({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 my-6">
      <div className="flex-1 h-px bg-white/5" />
      <span className="text-[10px] text-zinc-600 uppercase tracking-widest font-semibold">{label}</span>
      <div className="flex-1 h-px bg-white/5" />
    </div>
  );
}

export default function ArchPage() {
  return (
    <main className="min-h-screen bg-black text-white pt-20 px-6 pb-20">
      <div className="max-w-4xl mx-auto">

        {/* header */}
        <div className="mb-10">
          <h1 className="text-2xl font-bold gradient-text mb-1">Architecture</h1>
          <p className="text-xs text-zinc-500">
            How Mistrusic turns three words into a full personalized soundtrack
          </p>
        </div>

        {/* ── Pipeline overview ── */}
        <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-6 mb-10">
          <div className="text-[10px] text-zinc-600 uppercase tracking-widest font-semibold mb-5">Full Pipeline</div>
          <div className="flex flex-col items-center text-center">

            {/* User */}
            <div className="rounded-xl border border-white/15 bg-white/5 px-6 py-3 w-60">
              <div className="text-xs font-semibold text-white">User types a vibe</div>
              <div className="text-[10px] text-zinc-500 mt-0.5 font-mono">"dark haunted forest"</div>
            </div>

            <Arrow label="debounce 700ms" />

            {/* Client keyword detect */}
            <div className="rounded-xl border border-blue-500/30 bg-blue-950/20 px-6 py-3 w-60">
              <div className="text-xs font-semibold text-blue-300">Keyword Detector</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">Next.js · client-side regex</div>
              <div className="text-[9px] text-blue-400/70 font-mono mt-1">haunted → lib: "haunted"</div>
            </div>

            <Arrow label="POST /generate" />

            {/* Mistral Planner */}
            <div className="rounded-xl border border-fuchsia-500/40 bg-fuchsia-950/20 px-6 py-4 w-72">
              <div className="text-xs font-bold text-fuchsia-300">Mistral Journey Planner</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">mistral-small-latest · JSON mode</div>
              <div className="text-[9px] text-zinc-400 mt-2 leading-relaxed text-left">
                Reads track index (energy, brightness, duration for all 100 tracks)<br />
                → Returns ordered segment list with reasoning
              </div>
              <div className="mt-2 rounded-lg bg-black/40 px-2 py-1.5 font-mono text-[9px] text-fuchsia-300/80 text-left">
                {`{ "segments": [`}<br />
                {`  { "id": 73, "reason": "dark opening" },`}<br />
                {`  { "id": 12, "reason": "tension build" },`}<br />
                {`  ...`}<br />
                {`]}`}
              </div>
            </div>

            <Arrow label="stream segments" />

            {/* Render engine */}
            <div className="rounded-xl border border-violet-500/40 bg-violet-950/20 px-6 py-4 w-72">
              <div className="text-xs font-bold text-violet-300">Audio Render Engine</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">FastAPI · ThreadPoolExecutor</div>
              <div className="text-[9px] text-zinc-400 mt-2 leading-relaxed text-left">
                Cache hit → read WAV directly<br />
                Cache miss → FluidSynth render + FX chain → cache
              </div>
            </div>

            <Arrow label="WAV bytes" />

            {/* Frontend player */}
            <div className="rounded-xl border border-white/15 bg-white/5 px-6 py-3 w-60">
              <div className="text-xs font-semibold text-white">Browser Audio Player</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">Web Audio API · requestAnimationFrame</div>
            </div>
          </div>
        </div>

        {/* ── Layer 1: MIDI Library ── */}
        <Section label="Layer 1 · MIDI Library" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card
            title="EDM Chord Progressions"
            subtitle="100 hand-crafted MIDI files"
            color={ZINC}
            tags={[
              { label: ".mid files", color: "text-zinc-400" },
              { label: "EDM patterns" },
              { label: "4/4 time" },
            ]}
          >
            <p>100 chord progressions sourced from a curated EDM library. Each is a MIDI file — pure note data, no audio. All progressions are analyzed at startup for energy, brightness, and duration to populate the track index Mistral reads.</p>
          </Card>
          <Card
            title="Track Index"
            subtitle="JSON metadata for every progression"
            color={ZINC}
            tags={[
              { label: "energy: float", color: "text-amber-400/70" },
              { label: "brightness: float", color: "text-blue-400/70" },
              { label: "duration: seconds", color: "text-violet-400/70" },
            ]}
          >
            <p>Each track is pre-analyzed: RMS energy, spectral brightness, and duration. This index is what Mistral sees — it never touches raw audio or MIDI. It reasons purely from these numeric features to build an emotional arc.</p>
            <div className="mt-1 rounded bg-black/40 px-2 py-1 font-mono text-[9px] text-zinc-400">
              #073: energy=0.821 brightness=0.643 dur=12s
            </div>
          </Card>
        </div>

        {/* ── Layer 2: Mistral ── */}
        <Section label="Layer 2 · The Mistral Planner" />
        <Card
          title="mistral-small-latest — Journey Planning"
          subtitle="The brain that turns a vibe into a setlist"
          color={FUCHSIA}
          tags={[
            { label: "mistral-small-latest", color: "text-fuchsia-400" },
            { label: "JSON mode", color: "text-fuchsia-300/70" },
            { label: "temp: 0.5" },
          ]}
        >
          <p>Given a text description (e.g. "dark haunted forest at 3am") and the full track index, Mistral selects 4–6 progressions that form a narrative arc — tension, peak, release — and returns them in order with a short reason for each pick.</p>
          <p className="mt-1">The system prompt frames it as a DJ planning a set: "You are a trance DJ planning a musical journey." Mistral handles the curatorial intelligence so the selection always feels intentional, not random.</p>
          <div className="mt-2 rounded-lg bg-black/40 px-3 py-2 font-mono text-[9px] text-fuchsia-300/80 leading-relaxed">
            System: "You are a trance DJ... Return JSON: {'{'}"segments": [{'{'}id, reason{'}'}]{'}'}..."<br />
            User: "Journey: "dark haunted forest"\n\nLibrary:\n#001: energy=0.3...\n#002: ..."
          </div>
        </Card>

        {/* ── Layer 3: Render Engine ── */}
        <Section label="Layer 3 · The Render Engine" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card
            title="FluidSynth"
            subtitle="MIDI → WAV synthesis"
            color={VIOLET}
            tags={[
              { label: "fluidsynth -ni", color: "text-violet-400/80" },
              { label: "22050 Hz" },
              { label: "FluidR3 GM SF2" },
            ]}
          >
            <p>FluidSynth renders each MIDI file to a raw WAV using the FluidR3 General MIDI soundfont. The GM program number is injected per-vibe before rendering — so the same MIDI progression sounds completely different across vibes.</p>
          </Card>
          <Card
            title="GM Program Injection"
            subtitle="One MIDI, three instruments"
            color={VIOLET}
            tags={[
              { label: "Trance: #90 Polysynth", color: "text-violet-400/80" },
              { label: "Haunted: #52 Choir Aahs", color: "text-emerald-400/80" },
              { label: "Hip Hop: #4 Rhodes", color: "text-amber-400/80" },
            ]}
          >
            <p>Before FluidSynth runs, the MIDI is patched in-memory to set the GM program number for all channels. This means 100 MIDI files × 3 programs = 300 unique audio renders from a single MIDI library.</p>
          </Card>
          <Card
            title="Loop Engine"
            subtitle="4× seamless looping"
            color={VIOLET}
            tags={[
              { label: "crossfade: 100ms" },
              { label: "loops: 4×" },
              { label: "numpy concat" },
            ]}
          >
            <p>Each rendered clip is looped 4× with a 100ms linear crossfade at each seam, creating smooth ~40-60s tracks from short 8-15s progressions. The crossfade prevents clicks at loop boundaries.</p>
          </Card>
        </div>

        {/* FX chains */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card
            title="Trance FX Chain"
            subtitle="Euphoric + spacey"
            color={VIOLET}
            tags={[{ label: "polysynth", color: "text-violet-400" }]}
          >
            <ol className="list-none space-y-0.5">
              {["Hi-pass 80Hz (remove mud)", "4-voice chorus (±14 cents)", "6s hall reverb (91% decay)", "375ms dotted-8th delay"].map((s,i) => (
                <li key={i} className="flex gap-1.5"><span className="text-violet-500/60">{i+1}.</span>{s}</li>
              ))}
            </ol>
          </Card>
          <Card
            title="Haunted FX Chain"
            subtitle="Dark + atmospheric"
            color={EMERALD}
            tags={[{ label: "choir aahs", color: "text-emerald-400" }]}
          >
            <ol className="list-none space-y-0.5">
              {["Hi-pass 180Hz", "Tremolo 4.5Hz depth 0.35", "7s dark reverb (94% decay)", "72% wet mix"].map((s,i) => (
                <li key={i} className="flex gap-1.5"><span className="text-emerald-500/60">{i+1}.</span>{s}</li>
              ))}
            </ol>
          </Card>
          <Card
            title="Hip Hop FX Chain"
            subtitle="Warm + vintage"
            color={AMBER}
            tags={[{ label: "rhodes", color: "text-amber-400" }]}
          >
            <ol className="list-none space-y-0.5">
              {["Lo-pass 9kHz (warm roll-off)", "Vinyl saturation (tanh clip)", "Room reverb (62% decay)", "32% wet mix"].map((s,i) => (
                <li key={i} className="flex gap-1.5"><span className="text-amber-500/60">{i+1}.</span>{s}</li>
              ))}
            </ol>
          </Card>
        </div>

        {/* ── Layer 4: Cache ── */}
        <Section label="Layer 4 · Pre-render Cache" />
        <Card
          title="300-Track Audio Cache"
          subtitle="Zero-latency playback — all tracks rendered ahead of time"
          color={BLUE}
          tags={[
            { label: "100 × trance", color: "text-violet-400/80" },
            { label: "100 × haunted", color: "text-emerald-400/80" },
            { label: "100 × hiphop", color: "text-amber-400/80" },
            { label: "WAV · 22050Hz · float32" },
          ]}
        >
          <p>All 300 tracks are pre-rendered and saved to disk. When the frontend requests a track, the server reads the cached WAV directly — no synthesis, no FX processing. This is why preview starts in under a second.</p>
          <div className="mt-1 rounded bg-black/40 px-2 py-1 font-mono text-[9px] text-blue-300/80">
            audio/trance_raw/trance_073.wav<br />
            audio/haunted_raw/haunted_073.wav<br />
            audio/hiphop_raw/hiphop_073.wav
          </div>
        </Card>

        {/* ── Layer 5: Frontend ── */}
        <Section label="Layer 5 · Frontend Intelligence" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card
            title="Keyword Detector"
            subtitle="Client-side genre routing"
            color={ZINC}
            tags={[{ label: "Next.js", color: "text-blue-400/70" }, { label: "no API call" }]}
          >
            <p>Regex keyword matching runs locally in the browser — no round-trip needed. Detects ghost, haunt, dark → "haunted"; hip hop, lo-fi, chill → "hiphop"; trance, rave, euphoric → "trance". Fires immediately as you type.</p>
          </Card>
          <Card
            title="Debounced Auto-Preview"
            subtitle="700ms after you stop typing"
            color={ZINC}
            tags={[{ label: "useEffect + clearTimeout" }, { label: "Web Audio API" }]}
          >
            <p>A 700ms debounce triggers after each keystroke. Once stable, it hits <code className="font-mono text-[9px] bg-white/5 px-1 rounded">/generate</code> with the detected vibe, receives an ordered track list from Mistral, and begins streaming the first segment immediately.</p>
          </Card>
          <Card
            title="Streaming Player"
            subtitle="requestAnimationFrame timer loop"
            color={ZINC}
            tags={[{ label: "HTMLAudioElement" }, { label: "rAF loop" }, { label: "onloadedmetadata" }]}
          >
            <p>Each track URL is fed to a fresh <code className="font-mono text-[9px] bg-white/5 px-1 rounded">Audio</code> object. Duration is read on <code className="font-mono text-[9px] bg-white/5 px-1 rounded">onloadedmetadata</code> (guarded for Infinity on streamed WAV). Timer ticks via <code className="font-mono text-[9px] bg-white/5 px-1 rounded">requestAnimationFrame</code> for a smooth mm:ss counter.</p>
          </Card>
          <Card
            title="Studio Mix Engine"
            subtitle="Client-controlled layering"
            color={ZINC}
            tags={[{ label: "POST /mix" }, { label: "volume + offset" }, { label: "normalized WAV" }]}
          >
            <p>The Studio page sends a manifest to <code className="font-mono text-[9px] bg-white/5 px-1 rounded">POST /mix</code>: track IDs, vibes, individual volumes (0–1), and time offsets (seconds). The server pads, sums, and peak-normalizes all layers into one WAV, then streams it back.</p>
          </Card>
        </div>

        {/* ── Stats bar ── */}
        <div className="mt-10 rounded-2xl border border-white/8 bg-white/[0.02] p-6">
          <div className="text-[10px] text-zinc-600 uppercase tracking-widest font-semibold mb-5">By the numbers</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            {[
              { val: "300", label: "Pre-rendered tracks", sub: "3 vibes × 100 progressions" },
              { val: "<1s", label: "Preview latency",     sub: "direct cache read" },
              { val: "1",   label: "Mistral model",       sub: "mistral-small-latest" },
              { val: "3",   label: "FX chains",           sub: "trance · haunted · hip hop" },
            ].map(s => (
              <div key={s.val}>
                <div className="text-2xl font-bold gradient-text">{s.val}</div>
                <div className="text-xs text-zinc-300 mt-1">{s.label}</div>
                <div className="text-[10px] text-zinc-600 mt-0.5">{s.sub}</div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </main>
  );
}
