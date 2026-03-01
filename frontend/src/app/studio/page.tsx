"use client";
import { useCallback, useEffect, useRef, useState } from "react";

const API = "http://localhost:8000";

type Vibe = "trance" | "haunted" | "hiphop";

interface DeckTrack {
  uid: string;
  id: number;
  vibe: Vibe;
  volume: number;
  offset_s: number;
}

const VIBE_META: Record<Vibe, { label: string; color: string; dot: string; border: string; ring: string }> = {
  trance:  { label: "Trance",  color: "text-violet-400",  dot: "bg-violet-500",  border: "border-violet-500/40",  ring: "ring-violet-500/50" },
  haunted: { label: "Haunted", color: "text-emerald-400", dot: "bg-emerald-500", border: "border-emerald-500/40", ring: "ring-emerald-500/50" },
  hiphop:  { label: "Hip Hop", color: "text-amber-400",   dot: "bg-amber-500",   border: "border-amber-500/40",   ring: "ring-amber-500/50" },
};

function makeUid() { return Math.random().toString(36).slice(2); }

function fmt(s: number) {
  if (!isFinite(s) || isNaN(s)) return "–:––";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

const TRACK_IDS = Array.from({ length: 100 }, (_, i) => i + 1);

// Sound library categories
const SOUND_CATEGORIES: Record<string, { label: string; icon: string; color: string }> = {
  mechanical: { label: "Mechanical", icon: "⚙️", color: "text-orange-400" },
  instruments: { label: "Instruments", icon: "🎸", color: "text-blue-400" },
  synthetic: { label: "Synthetic", icon: "🔮", color: "text-purple-400" },
  percussion: { label: "Percussion", icon: "🥁", color: "text-yellow-400" },
  nature: { label: "Nature", icon: "🌿", color: "text-green-400" },
  vocal: { label: "Vocal", icon: "🎤", color: "text-pink-400" },
  urban: { label: "Urban", icon: "🏙️", color: "text-gray-400" },
  fx: { label: "FX", icon: "✨", color: "text-red-400" },
};

interface Sound {
  id: string;
  name: string;
  description: string;
  category: string;
}

export default function StudioPage() {
  const [deck, setDeck]         = useState<DeckTrack[]>([]);
  const [mixing, setMixing]     = useState(false);
  const [playing, setPlaying]   = useState(false);
  const [elapsed, setElapsed]   = useState(0);
  const [duration, setDuration] = useState(0);
  const [clipS, setClipS]       = useState(30);
  const [preview, setPreview]   = useState<number | null>(null);
  const [hasMix, setHasMix]     = useState(false);
  
  // Sound library state
  const [sounds, setSounds]     = useState<Sound[]>([]);
  const [soundCats, setSoundCats] = useState<string[]>([]);
  const [selectedSoundCat, setSelectedSoundCat] = useState<string | null>(null);

  const audioRef   = useRef<HTMLAudioElement | null>(null);
  const rafRef     = useRef<number>(0);
  const prevAudRef = useRef<HTMLAudioElement | null>(null);

  // Fetch sound library
  useEffect(() => {
    fetch(`${API}/api/sounds`)
      .then(r => r.json())
      .then(data => {
        setSounds(data.sounds || []);
        setSoundCats(data.categories || []);
      })
      .catch(() => {});
  }, []);

  const addTrack = useCallback((id: number, vibe: Vibe) => {
    setDeck(d => [...d, { uid: makeUid(), id, vibe, volume: 0.8, offset_s: 0 }]);
  }, []);

  const removeTrack = useCallback((u: string) => {
    setDeck(d => d.filter(t => t.uid !== u));
  }, []);

  const updateTrack = useCallback((u: string, patch: Partial<DeckTrack>) => {
    setDeck(d => d.map(t => t.uid === u ? { ...t, ...patch } : t));
  }, []);

  const previewTrack = useCallback((id: number, vibe: Vibe) => {
    prevAudRef.current?.pause();
    const a = new Audio(`${API}/track/${id}/audio?vibe=${vibe}&clip_s=8`);
    a.play().catch(() => {});
    prevAudRef.current = a;
    setPreview(id);
    a.onended = () => setPreview(null);
  }, []);

  const tickTimer = useCallback(() => {
    const a = audioRef.current;
    if (!a || a.paused) return;
    setElapsed(a.currentTime);
    rafRef.current = requestAnimationFrame(tickTimer);
  }, []);

  const playMix = useCallback(async () => {
    if (deck.length === 0) return;
    setMixing(true);
    try {
      const res = await fetch(`${API}/mix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tracks: deck.map(t => ({ id: t.id, vibe: t.vibe, volume: t.volume, offset_s: t.offset_s })),
          clip_s: clipS,
        }),
      });
      if (!res.ok) throw new Error("mix failed");
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);

      audioRef.current?.pause();
      const a = new Audio(url);
      audioRef.current = a;
      setElapsed(0);
      setHasMix(true);

      a.onloadedmetadata = () => setDuration(a.duration);
      a.onplay  = () => { setPlaying(true);  rafRef.current = requestAnimationFrame(tickTimer); };
      a.onpause = () => { setPlaying(false); cancelAnimationFrame(rafRef.current); };
      a.onended = () => { setPlaying(false); setElapsed(0); cancelAnimationFrame(rafRef.current); };
      a.play().catch(() => {});
    } catch {
      // silent
    } finally {
      setMixing(false);
    }
  }, [deck, clipS, tickTimer]);

  const togglePlay = useCallback(() => {
    const a = audioRef.current;
    if (!a) return;
    a.paused ? a.play() : a.pause();
  }, []);

  useEffect(() => () => {
    audioRef.current?.pause();
    prevAudRef.current?.pause();
    cancelAnimationFrame(rafRef.current);
  }, []);

  const pct = duration > 0 ? (elapsed / duration) * 100 : 0;

  return (
    <main className="min-h-screen bg-black text-white pt-20 px-6 pb-16">
      {/* header */}
      <div className="max-w-6xl mx-auto mb-8">
        <h1 className="text-2xl font-bold gradient-text mb-1">Studio</h1>
        <p className="text-xs text-zinc-500">
          Click tracks to add them to your mix deck · Shift+click to preview · adjust volume &amp; offset · hit Mix
        </p>
      </div>

      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">

        {/* ── left: track browser ── */}
        <div className="space-y-5">
          {(["trance", "haunted", "hiphop"] as Vibe[]).map(vibe => {
            const meta = VIBE_META[vibe];
            const inDeck = new Set(deck.filter(t => t.vibe === vibe).map(t => t.id));
            return (
              <div key={vibe} className={`rounded-2xl border ${meta.border} bg-white/[0.02] p-4`}>
                <div className="flex items-center gap-2 mb-3">
                  <div className={`w-2 h-2 rounded-full ${meta.dot}`} />
                  <span className={`text-xs font-semibold ${meta.color} uppercase tracking-widest`}>{meta.label}</span>
                  <span className="ml-1 text-[10px] text-zinc-600">· {inDeck.size} in deck</span>
                  <span className="ml-auto text-[10px] text-zinc-700">click to add · shift+click to preview</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {TRACK_IDS.map(id => {
                    const active = inDeck.has(id);
                    const isPreviewing = preview === id;
                    return (
                      <button
                        key={id}
                        title={`Track ${id} · ${meta.label}${active ? " (in deck)" : ""}`}
                        onClick={e => e.shiftKey ? previewTrack(id, vibe) : addTrack(id, vibe)}
                        className={[
                          "w-8 h-8 rounded-lg text-[10px] font-mono font-semibold transition-all",
                          active
                            ? `${meta.dot} text-black scale-105`
                            : "bg-white/5 text-zinc-500 hover:bg-white/10 hover:text-white",
                          isPreviewing ? "ring-2 ring-white/70 scale-110" : "",
                        ].join(" ")}
                      >
                        {id}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
          
          {/* ── Sound Library Browser ── */}
          {sounds.length > 0 && (
            <div className="rounded-2xl border border-violet-500/20 bg-violet-500/5 p-4 mt-6">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <span className="text-xs font-semibold text-violet-300 uppercase tracking-widest">Sound Library</span>
                  <span className="ml-2 text-[10px] text-zinc-600">{sounds.length} sounds</span>
                </div>
                <a href="/morph" className="text-[10px] text-violet-400 hover:text-violet-300 flex items-center gap-1">
                  Open Morph Studio →
                </a>
              </div>
              
              {/* Category filter */}
              <div className="flex flex-wrap gap-1.5 mb-3">
                <button
                  onClick={() => setSelectedSoundCat(null)}
                  className={`px-2 py-1 rounded-md text-[10px] font-medium transition-all ${
                    selectedSoundCat === null
                      ? "bg-violet-500/30 text-white"
                      : "bg-white/5 text-zinc-500 hover:bg-white/10"
                  }`}
                >
                  All
                </button>
                {soundCats.map(cat => (
                  <button
                    key={cat}
                    onClick={() => setSelectedSoundCat(cat === selectedSoundCat ? null : cat)}
                    className={`px-2 py-1 rounded-md text-[10px] font-medium transition-all ${
                      selectedSoundCat === cat
                        ? "bg-violet-500/30 text-white"
                        : "bg-white/5 text-zinc-500 hover:bg-white/10"
                    }`}
                  >
                    {SOUND_CATEGORIES[cat]?.icon} {SOUND_CATEGORIES[cat]?.label || cat}
                  </button>
                ))}
              </div>
              
              {/* Sounds grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-[200px] overflow-y-auto pr-1">
                {(selectedSoundCat ? sounds.filter(s => s.category === selectedSoundCat) : sounds).map(sound => {
                  const cat = SOUND_CATEGORIES[sound.category];
                  return (
                    <a
                      key={sound.id}
                      href="/morph"
                      className="p-2 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 hover:border-violet-500/30 transition-all text-left"
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm">{cat?.icon}</span>
                        <span className={`text-[9px] uppercase ${cat?.color || "text-zinc-500"}`}>
                          {cat?.label || sound.category}
                        </span>
                      </div>
                      <div className="font-medium text-xs text-zinc-300 truncate mt-0.5">
                        {sound.name}
                      </div>
                    </a>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* ── right: mix deck ── */}
        <div className="lg:sticky lg:top-24 h-fit space-y-4">

          {/* deck */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-zinc-300 uppercase tracking-widest">Mix Deck</span>
              <span className="text-[10px] text-zinc-600">{deck.length} track{deck.length !== 1 ? "s" : ""}</span>
            </div>

            {deck.length === 0 ? (
              <div className="flex items-center justify-center h-20 rounded-xl border border-dashed border-white/10 text-zinc-700 text-xs">
                No tracks yet — click any number on the left
              </div>
            ) : (
              <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                {deck.map(t => {
                  const meta = VIBE_META[t.vibe];
                  return (
                    <div key={t.uid} className={`rounded-xl border ${meta.border} bg-white/[0.02] p-3`}>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-1.5">
                          <div className={`w-1.5 h-1.5 rounded-full ${meta.dot}`} />
                          <span className={`text-[10px] font-semibold ${meta.color}`}>{meta.label}</span>
                          <span className="text-[10px] text-zinc-500 font-mono">#{t.id}</span>
                        </div>
                        <button
                          onClick={() => removeTrack(t.uid)}
                          className="text-zinc-600 hover:text-red-400 text-sm w-5 h-5 flex items-center justify-center rounded transition-colors"
                        >
                          ×
                        </button>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-[9px] text-zinc-600 mb-0.5 block">
                            Vol {Math.round(t.volume * 100)}%
                          </label>
                          <input
                            type="range" min={0} max={1} step={0.05} value={t.volume}
                            onChange={e => updateTrack(t.uid, { volume: parseFloat(e.target.value) })}
                            className="w-full accent-violet-500 h-1"
                          />
                        </div>
                        <div>
                          <label className="text-[9px] text-zinc-600 mb-0.5 block">
                            Offset {t.offset_s}s
                          </label>
                          <input
                            type="range" min={0} max={20} step={0.5} value={t.offset_s}
                            onChange={e => updateTrack(t.uid, { offset_s: parseFloat(e.target.value) })}
                            className="w-full accent-fuchsia-500 h-1"
                          />
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* clip length */}
          <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] text-zinc-500 uppercase tracking-widest">Clip length</span>
              <span className="text-[10px] text-zinc-300 font-mono">{clipS}s</span>
            </div>
            <input
              type="range" min={10} max={120} step={5} value={clipS}
              onChange={e => setClipS(parseInt(e.target.value))}
              className="w-full accent-violet-500 h-1"
            />
          </div>

          {/* player — only visible after first mix */}
          {hasMix && (
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
              <div className="flex items-center gap-3">
                <button
                  onClick={togglePlay}
                  className="w-8 h-8 rounded-full bg-violet-600 hover:bg-violet-500 flex items-center justify-center transition-colors flex-shrink-0"
                >
                  {playing ? (
                    <span className="flex gap-0.5 items-center">
                      {[0, 1].map(i => (
                        <span key={i} className="w-0.5 h-3 bg-white playing-bar" />
                      ))}
                    </span>
                  ) : (
                    <span className="ml-0.5 w-0 h-0 border-t-[5px] border-b-[5px] border-l-[8px] border-t-transparent border-b-transparent border-l-white" />
                  )}
                </button>
                <div className="flex-1 min-w-0">
                  <div className="h-1 bg-white/10 rounded-full overflow-hidden cursor-pointer"
                    onClick={e => {
                      const a = audioRef.current;
                      if (!a || !duration) return;
                      const rect = e.currentTarget.getBoundingClientRect();
                      a.currentTime = ((e.clientX - rect.left) / rect.width) * duration;
                    }}
                  >
                    <div className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 transition-none"
                      style={{ width: `${pct}%` }} />
                  </div>
                  <div className="flex justify-between text-[9px] text-zinc-600 mt-1 font-mono">
                    <span>{fmt(elapsed)}</span>
                    <span>{fmt(duration)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* mix button */}
          <button
            onClick={playMix}
            disabled={deck.length === 0 || mixing}
            className="w-full py-3 rounded-xl font-semibold text-sm transition-all
              bg-gradient-to-r from-violet-600 to-fuchsia-600
              hover:from-violet-500 hover:to-fuchsia-500
              disabled:opacity-40 disabled:cursor-not-allowed glow"
          >
            {mixing ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-3 h-3 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                Mixing…
              </span>
            ) : (
              `Mix + Play${deck.length > 0 ? ` (${deck.length} tracks)` : ""}`
            )}
          </button>

          {deck.length > 0 && (
            <button
              onClick={() => setDeck([])}
              className="w-full py-2 rounded-xl text-xs text-zinc-700 hover:text-zinc-400 transition-colors"
            >
              Clear deck
            </button>
          )}
        </div>
      </div>
    </main>
  );
}
