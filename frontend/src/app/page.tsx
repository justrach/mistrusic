"use client";

import { useEffect, useRef, useState, useCallback } from "react";

const API = "http://localhost:8000";
type PlanSegment = { id: number; reason: string };
type Vibe = typeof VIBES[0];

// ── Static starfield ────────────────────────────────────────────────────────
const STARS = Array.from({ length: 80 }, (_, i) => ({
  id: i,
  x: ((i * 137.5) % 100),
  y: ((i * 97.3)  % 100),
  size: 1 + (i % 3) * 0.6,
  d: 2 + (i % 5),
  delay: -(i % 7),
}));

// ── Helpers ─────────────────────────────────────────────────────────────────
function fmt(s: number) {
  if (!isFinite(s) || isNaN(s)) return "–:––";
  return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
}

function EqBars({ color = "bg-violet-400" }: { color?: string }) {
  return (
    <div className="flex items-end gap-[3px] h-7">
      {[0,1,2,3,4].map((i) => (
        <div key={i} className={`playing-bar w-[3px] rounded-full ${color}`}
          style={{ animationDelay: `${[0,.15,.30,.45,.10][i]}s` }} />
      ))}
    </div>
  );
}

// ── Expanded Vibes with all categories ───────────────────────────────────────
const VIBES = [
  // Original vibes
  { label: "👻 Haunted House",   prompt: "creepy haunted mansion, dark minor chords, eerie atmosphere building to terrifying climax",    lib: "haunted" },
  { label: "🌿 Dark Forest",      prompt: "lost deep in an ancient forest at night, mysterious organic textures, building dread then wonder", lib: "haunted" },
  { label: "🎹 Hip Hop",          prompt: "smooth late-night hip hop, soulful Rhodes chords, laid-back groove building to a head-nodding peak", lib: "hiphop"  },
  { label: "🌙 Late Night Drive", prompt: "dark city highway at 3am, melancholic and hypnotic, neon lights blurring past",                lib: "hiphop"  },
  { label: "🌅 Euphoric Sunrise", prompt: "start cold and misty at dawn, slowly build to a euphoric trance sunrise anthem",               lib: "trance"  },
  { label: "🚀 Space Station",    prompt: "floating weightless in deep space, cosmic and cinematic, slow build to interstellar euphoria",   lib: "trance"  },
  { label: "🔥 Festival Peak",    prompt: "massive festival main stage, crowd going insane, huge drop, pure euphoric energy",              lib: "trance"  },
  { label: "❄️ Arctic Drift",     prompt: "vast frozen tundra, sparse and isolating, cold pads, slowly warming into something beautiful",  lib: "trance"  },
  // NEW: Mechanical vibes
  { label: "⚙️ Industrial",       prompt: "heavy machinery and grinding gears, mechanical rhythms, industrial noise becoming musical",       lib: "haunted" },
  { label: "🚂 Train Journey",    prompt: "rhythmic train wheels on tracks, steady motion, building steam and momentum",                  lib: "hiphop"  },
  // NEW: Nature vibes
  { label: "🌊 Ocean Waves",      prompt: "gentle ocean waves building to powerful surf, water rhythms, deep blue calm to storm",         lib: "trance"  },
  { label: "⛈️ Thunder Storm",    prompt: "distant thunder rumbling, rain building, electric energy in the air, powerful release",         lib: "haunted" },
  { label: "🐋 Whale Song",       prompt: "deep underwater whale calls, vast ocean depths, mysterious and ancient marine sounds",          lib: "trance"  },
  // NEW: Percussion vibes
  { label: "🥁 Tribal Drums",     prompt: "primitive tribal drums, rhythmic pulse, ceremonial energy building to ecstatic dance",          lib: "hiphop"  },
  { label: "🔔 Gong Meditation",  prompt: "large metal gong resonance, overtones building, meditative drone to cosmic expansion",          lib: "trance"  },
  // NEW: Vocal vibes
  { label: "🎤 Choir Voices",     prompt: "ethereal choir voices, heavenly harmonies, angelic build to celestial power",                   lib: "trance"  },
  { label: "🗣️ Tuvan Throat",     prompt: "deep throat singing drones, harmonic overtones, ancient Mongolian steppes",                     lib: "haunted" },
  // NEW: Urban vibes
  { label: "🏙️ City Traffic",     prompt: "urban city sounds, traffic rhythms, subway rumbles, concrete jungle symphony",                  lib: "hiphop"  },
  { label: "☕ Coffee Shop",      prompt: "muffled cafe ambience, quiet conversation, intimate acoustic warmth",                          lib: "hiphop"  },
];

const KEYWORDS: { words: string[]; lib: string }[] = [
  { words: ["haunt","ghost","spook","horror","eerie","creep","scary","mansion","zombie","gothic","sinister","dark forest","shadow","macabre","witch","cursed","industrial","machine","gear","factory","thunder","storm","lightning","tuvan","throat"], lib: "haunted" },
  { words: ["hip hop","hiphop","rap","groove","beat","rhodes","soul","bounce","lofi","lo-fi","chill","r&b","boom bap","trap","sample","train","tribal","drums","percussion","city","urban","traffic","subway","coffee","cafe"], lib: "hiphop"  },
  { words: ["trance","rave","festival","euphoric","epic","space","cosmic","float","anthem","sunrise","edm","plur","uplift","drop","ocean","waves","whale","underwater","choir","voices","angelic","gong","meditation"],       lib: "trance"  },
];

function detectLib(text: string) {
  const l = text.toLowerCase();
  for (const { words, lib } of KEYWORDS) if (words.some(w => l.includes(w))) return lib;
  return null;
}

function pickTrackId(text: string) {
  let h = 0;
  for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) & 0xffffffff;
  return (Math.abs(h) % 100) + 1;
}

// ── Theme per lib ────────────────────────────────────────────────────────────
const THEME: Record<string, { glow: string; ring: string; bar: string; chip: string; eqColor: string; border: string; btn: string }> = {
  haunted: {
    glow:    "bg-emerald-600/15",
    ring:    "border-emerald-500",
    bar:     "from-emerald-500 to-green-400",
    chip:    "bg-green-900/30 border-green-500/50 text-green-300",
    eqColor: "bg-emerald-400",
    border:  "border-emerald-500/30 focus:border-emerald-500/60",
    btn:     "from-emerald-700 to-green-600",
  },
  hiphop: {
    glow:    "bg-amber-600/15",
    ring:    "border-amber-400",
    bar:     "from-amber-500 to-yellow-400",
    chip:    "bg-amber-900/30 border-amber-500/50 text-amber-300",
    eqColor: "bg-amber-400",
    border:  "border-amber-500/30 focus:border-amber-500/60",
    btn:     "from-amber-600 to-yellow-500",
  },
  trance: {
    glow:    "bg-violet-600/20",
    ring:    "border-violet-500",
    bar:     "from-violet-500 to-fuchsia-500",
    chip:    "bg-violet-600/30 border-violet-500/60 text-violet-300",
    eqColor: "bg-violet-400",
    border:  "border-violet-500/30 focus:border-violet-500/60",
    btn:     "from-violet-600 to-fuchsia-600",
  },
};
const DEFAULT_THEME = THEME.trance;

// ── Main ─────────────────────────────────────────────────────────────────────
export default function Home() {
  const [journey,     setJourney]     = useState("");
  const [loading,     setLoading]     = useState(false);
  const [loadingMsg,  setLoadingMsg]  = useState("");
  const [plan,        setPlan]        = useState<PlanSegment[]>([]);
  const [playing,     setPlaying]     = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration,    setDuration]    = useState(0);
  const [label,       setLabel]       = useState<string | null>(null);
  const [activeVibe,  setActiveVibe]  = useState<Vibe | null>(null);
  const [detectedLib, setDetectedLib] = useState<string | null>(null);
  const [error,       setError]       = useState("");

  const audioRef    = useRef<HTMLAudioElement | null>(null);
  const rafRef      = useRef<number>(0);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const previewMode = useRef(false);

  const theme = THEME[detectedLib ?? ""] ?? DEFAULT_THEME;

  // ── Audio engine ────────────────────────────────────────────────────────
  function tick() {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
      if (isFinite(audioRef.current.duration)) setDuration(audioRef.current.duration);
    }
    rafRef.current = requestAnimationFrame(tick);
  }

  function stopCurrent() {
    cancelAnimationFrame(rafRef.current);
    if (audioRef.current) { audioRef.current.pause(); audioRef.current.src = ""; }
    setPlaying(false); setCurrentTime(0); setDuration(0); setLabel(null);
    previewMode.current = false;
  }

  function playUrl(url: string, lbl: string) {
    stopCurrent();
    const a = new Audio(url);
    audioRef.current = a;
    a.onloadedmetadata = () => { if (isFinite(a.duration)) setDuration(a.duration); };
    a.onplay  = () => { setPlaying(true);  rafRef.current = requestAnimationFrame(tick); };
    a.onended = () => { setPlaying(false); cancelAnimationFrame(rafRef.current); };
    a.onpause = () => { setPlaying(false); cancelAnimationFrame(rafRef.current); };
    a.play().catch(() => {});
    setLabel(lbl);
  }

  useEffect(() => () => cancelAnimationFrame(rafRef.current), []);

  function seek(e: React.MouseEvent<HTMLDivElement>) {
    if (!audioRef.current || !duration) return;
    const r = e.currentTarget.getBoundingClientRect();
    audioRef.current.currentTime = ((e.clientX - r.left) / r.width) * duration;
  }

  // ── Auto-detect ──────────────────────────────────────────────────────────
  const startPreview = useCallback((lib: string, text: string) => {
    previewMode.current = true;
    playUrl(`${API}/track/${pickTrackId(text)}/audio?vibe=${lib}&clip_s=25`, `preview · ${lib}`);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!journey.trim()) { setDetectedLib(null); setActiveVibe(null); if (previewMode.current) stopCurrent(); return; }

    const lib = detectLib(journey);
    setDetectedLib(lib);
    if (lib) {
      const match = VIBES.find(v => v.lib === lib);
      if (match && activeVibe?.lib !== lib) setActiveVibe(match);
    }

    debounceRef.current = setTimeout(() => {
      if (lib) startPreview(lib, journey);
    }, 650);

    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [journey]);

  // ── Actions ──────────────────────────────────────────────────────────────
  async function generate(text = journey) {
    if (!text.trim()) return;
    previewMode.current = false; stopCurrent();
    setLoading(true); setError(""); setPlan([]);
    setLoadingMsg("Mistral is planning your journey…");
    try {
      const lib = activeVibe?.lib ?? detectedLib ?? "trance";
      const res = await fetch(`${API}/generate`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ journey: text, vibe: lib }),
      });
      if (!res.ok) throw new Error(await res.text());
      const ph = res.headers.get("X-Plan");
      if (ph) setPlan(JSON.parse(ph));
      setLoadingMsg("Rendering pads…");
      playUrl(URL.createObjectURL(await res.blob()), activeVibe?.label ?? "Journey");
    } catch (e: unknown) { setError(String(e)); }
    finally { setLoading(false); setLoadingMsg(""); }
  }

  async function generateSplice() {
    previewMode.current = false; stopCurrent();
    setLoading(true); setError(""); setPlan([]);
    setLoadingMsg("Building DJ splice…");
    try {
      const lib = activeVibe?.lib ?? detectedLib ?? "trance";
      const res = await fetch(`${API}/splice`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ count: 8, clip_s: 12, vibe: lib }),
      });
      playUrl(URL.createObjectURL(await res.blob()), `DJ Splice · ${lib}`);
    } catch (e: unknown) { setError(String(e)); }
    finally { setLoading(false); setLoadingMsg(""); }
  }

  function pickVibe(v: Vibe) {
    setJourney(v.prompt); setActiveVibe(v); setDetectedLib(v.lib);
    previewMode.current = false; startPreview(v.lib, v.prompt);
  }

  const progress = duration > 0 ? currentTime / duration : 0;

  return (
    <div className="relative min-h-screen bg-black flex flex-col items-center justify-center px-6 py-20 overflow-hidden">

      {/* Starfield */}
      <div className="stars" aria-hidden>
        {STARS.map(s => (
          <div key={s.id} className="star"
            style={{
              left: `${s.x}%`, top: `${s.y}%`,
              width: s.size, height: s.size,
              "--d": `${s.d}s`, "--delay": `${s.delay}s`,
            } as React.CSSProperties} />
        ))}
      </div>

      {/* Nebula tint */}
      <div className={`fixed inset-0 pointer-events-none transition-all duration-1000 ${theme.glow} blur-[120px] opacity-60`} />

      {/* Header */}
      <header className="absolute top-0 left-0 right-0 flex items-center justify-between px-8 py-5 z-10">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-600 flex items-center justify-center shadow-lg shadow-violet-500/30">
            <span className="text-[11px] font-bold text-white">M</span>
          </div>
          <span className="font-semibold tracking-tight text-white text-sm">Mistrusic</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-zinc-600 font-mono">mistral-small-latest</span>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-violet-500/30 bg-violet-950/40 text-[10px] text-violet-400 font-medium">
            <div className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
            Mistral Hackathon 2025
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="relative z-10 w-full max-w-md flex flex-col items-center gap-7">

        {/* Hero */}
        <div className="text-center space-y-2 mb-2">
          <h1 className="text-3xl font-bold tracking-tight gradient-text">
            Describe a vibe.
          </h1>
          <p className="text-sm text-zinc-500">Music starts as you type — powered by Mistral AI</p>
        </div>

        {/* Orb */}
        <div className="relative flex items-center justify-center select-none" style={{ animation: "float 4s ease-in-out infinite" }}>
          {/* outer glow */}
          <div className={`absolute w-64 h-64 rounded-full blur-3xl transition-all duration-1000
            ${theme.glow} ${playing ? "opacity-80 scale-110" : "opacity-30 scale-90"}`} />
          {/* outer ring — spins */}
          <div className={`absolute w-52 h-52 rounded-full border border-dashed border-white/5
            ${playing ? "animate-[spin-slow_20s_linear_infinite]" : ""}`} />
          {/* mid ring — counter-spins */}
          <div className={`absolute w-44 h-44 rounded-full border transition-colors duration-700
            ${playing ? `border-white/10 animate-[spin-rev_14s_linear_infinite]` : "border-white/5"}`} />
          {/* inner glow ring */}
          <div className={`absolute w-36 h-36 rounded-full transition-all duration-500
            ${playing ? `border-2 ${theme.ring} glow animate-[pulse-ring_2s_ease-in-out_infinite]` : "border border-white/10"}`} />
          {/* core */}
          <div className="relative w-28 h-28 rounded-full flex flex-col items-center justify-center gap-1.5">
            {playing ? (
              <>
                <EqBars color={theme.eqColor} />
                <button onClick={stopCurrent} className="text-zinc-500 hover:text-white transition-colors mt-0.5">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="6" y="6" width="4" height="12" rx="1.5"/>
                    <rect x="14" y="6" width="4" height="12" rx="1.5"/>
                  </svg>
                </button>
              </>
            ) : loading ? (
              <p className="text-zinc-500 text-[11px] text-center px-5 leading-relaxed">{loadingMsg}</p>
            ) : (
              <p className="text-zinc-700 text-xs">ready</p>
            )}
          </div>
        </div>

        {/* Timer */}
        <div className="w-full flex flex-col gap-1.5">
          <div className="w-full h-[3px] bg-white/8 rounded-full overflow-hidden cursor-pointer group" onClick={seek}>
            <div className={`h-full bg-gradient-to-r ${theme.bar} rounded-full transition-all duration-100`}
              style={{ width: `${progress * 100}%` }} />
          </div>
          <div className="flex justify-between items-center text-[11px] font-mono">
            <span className="text-zinc-700">{fmt(currentTime)}</span>
            {label && <span className={`text-xs font-sans font-medium transition-colors duration-300
              ${detectedLib === "haunted" ? "text-emerald-400" : detectedLib === "hiphop" ? "text-amber-400" : "text-violet-400"}`}>
              {label}
            </span>}
            <span className="text-zinc-700">{duration > 0 ? fmt(duration) : "–:––"}</span>
          </div>
        </div>

        {/* Vibe chips */}
        <div className="w-full flex flex-col gap-2">
          {(["haunted","hiphop","trance"] as const).map(lib => {
            const t = THEME[lib];
            return (
              <div key={lib} className="flex items-center gap-2 flex-wrap">
                <span className="text-[9px] text-zinc-700 uppercase tracking-[0.15em] w-12 shrink-0">
                  {lib === "haunted" ? "horror" : lib === "hiphop" ? "hip hop" : "trance"}
                </span>
                {VIBES.filter(v => v.lib === lib).map(v => (
                  <button key={v.label} onClick={() => pickVibe(v)}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 border
                      ${activeVibe?.label === v.label ? t.chip : "bg-white/4 border-white/8 text-zinc-500 hover:border-white/20 hover:text-zinc-300"}`}>
                    {v.label}
                  </button>
                ))}
              </div>
            );
          })}
        </div>

        {/* Input */}
        <div className="w-full flex flex-col gap-3">
          <textarea
            value={journey}
            onChange={e => setJourney(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) generate(); }}
            placeholder="Type a vibe… haunted house, hip hop groove, trance festival — music starts as you type"
            rows={3}
            className={`w-full bg-white/4 border rounded-2xl px-5 py-4 text-sm text-white
              placeholder:text-zinc-700 focus:outline-none resize-none transition-colors duration-500
              ${detectedLib ? theme.border : "border-white/8 focus:border-white/20"}`}
          />
          <div className="flex gap-2.5">
            <button onClick={() => generate()} disabled={loading || !journey.trim()}
              className={`flex-1 h-12 rounded-xl text-sm font-semibold text-white transition-all duration-500
                hover:opacity-90 disabled:opacity-25 disabled:cursor-not-allowed bg-gradient-to-r ${theme.btn}`}>
              {loading && loadingMsg ? loadingMsg : "Generate Journey  ⌘↵"}
            </button>
            <button onClick={generateSplice} disabled={loading}
              className="h-12 px-5 rounded-xl border border-white/10 text-sm text-zinc-400
                hover:bg-white/5 hover:text-white transition-all disabled:opacity-25 disabled:cursor-not-allowed whitespace-nowrap">
              DJ Splice
            </button>
          </div>
        </div>

        {/* Mistral's plan */}
        {plan.length > 0 && (
          <div className="w-full rounded-2xl border border-white/8 bg-white/3 px-5 py-4 space-y-2.5">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-4 h-4 rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-600 flex items-center justify-center">
                <span className="text-[8px] font-bold text-white">M</span>
              </div>
              <span className="text-[10px] text-zinc-500 uppercase tracking-widest">Mistral's arc</span>
            </div>
            {plan.map((seg, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                <span className={`font-mono shrink-0 text-xs pt-0.5
                  ${detectedLib === "haunted" ? "text-emerald-500" : detectedLib === "hiphop" ? "text-amber-500" : "text-violet-500"}`}>
                  {String(i + 1).padStart(2,"0")}
                </span>
                <span className="text-zinc-400 leading-relaxed">{seg.reason}</span>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="text-xs text-red-400 bg-red-950/40 border border-red-500/20 rounded-xl px-4 py-3 w-full">
            {error}
          </div>
        )}

        {/* Footer */}
        <p className="text-[10px] text-zinc-800 text-center mt-2">
          300 pre-rendered progressions · trance · horror · hip hop · Mistral La Plateforme
        </p>
      </div>
    </div>
  );
}
