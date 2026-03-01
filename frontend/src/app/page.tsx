"use client";

import { useEffect, useRef, useState } from "react";

const API = "http://localhost:8000";

type PlanSegment = { id: number; reason: string };

function EqBars() {
  return (
    <div className="flex items-end gap-[3px] h-6">
      {[1, 2, 3, 4, 5].map((i) => (
        <div
          key={i}
          className="playing-bar w-[3px] rounded-full bg-violet-400"
          style={{ animationDelay: `${i * 0.12}s` }}
        />
      ))}
    </div>
  );
}

function fmt(s: number) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${String(sec).padStart(2, "0")}`;
}

export default function Home() {
  const [journey, setJourney] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState("");
  const [plan, setPlan] = useState<PlanSegment[]>([]);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState("");
  const [label, setLabel] = useState<string | null>(null);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const rafRef = useRef<number>(0);

  function tick() {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
      setDuration(audioRef.current.duration || 0);
    }
    rafRef.current = requestAnimationFrame(tick);
  }

  function stopCurrent() {
    cancelAnimationFrame(rafRef.current);
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
    }
    setPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    setLabel(null);
  }

  function playUrl(url: string, lbl: string) {
    stopCurrent();
    const audio = new Audio(url);
    audioRef.current = audio;
    audio.onplay    = () => { setPlaying(true); rafRef.current = requestAnimationFrame(tick); };
    audio.onended   = () => { setPlaying(false); cancelAnimationFrame(rafRef.current); };
    audio.onpause   = () => { setPlaying(false); cancelAnimationFrame(rafRef.current); };
    audio.play();
    setLabel(lbl);
  }

  useEffect(() => () => { cancelAnimationFrame(rafRef.current); }, []);

  function seek(e: React.MouseEvent<HTMLDivElement>) {
    if (!audioRef.current || !duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    audioRef.current.currentTime = ratio * duration;
  }

  async function generate() {
    if (!journey.trim()) return;
    stopCurrent();
    setLoading(true);
    setError("");
    setPlan([]);
    setLoadingMsg("Mistral is planning your journey…");
    try {
      const res = await fetch(`${API}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ journey }),
      });
      if (!res.ok) throw new Error(await res.text());
      const planHeader = res.headers.get("X-Plan");
      if (planHeader) setPlan(JSON.parse(planHeader));
      setLoadingMsg("Rendering trance pads…");
      const blob = await res.blob();
      playUrl(URL.createObjectURL(blob), "Journey");
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
      setLoadingMsg("");
    }
  }

  async function generateSplice() {
    stopCurrent();
    setLoading(true);
    setError("");
    setLoadingMsg("Building DJ splice…");
    setPlan([]);
    try {
      const res  = await fetch(`${API}/splice`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ count: 8, clip_s: 12 }),
      });
      const blob = await res.blob();
      playUrl(URL.createObjectURL(blob), "DJ Splice");
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
      setLoadingMsg("");
    }
  }

  const progress = duration > 0 ? currentTime / duration : 0;

  return (
    <div className="min-h-screen bg-black flex flex-col items-center justify-center px-6">
      {/* Logo */}
      <div className="absolute top-6 left-1/2 -translate-x-1/2 flex items-center gap-2">
        <div className="w-6 h-6 rounded-full bg-gradient-to-br from-violet-500 to-fuchsia-600 flex items-center justify-center">
          <span className="text-[10px] font-bold text-white">M</span>
        </div>
        <span className="text-sm font-semibold tracking-tight text-white">Mistrusic</span>
        <span className="text-zinc-600 text-sm">× Mistral AI</span>
      </div>

      <div className="w-full max-w-lg flex flex-col items-center gap-10">
        {/* Orb */}
        <div className="relative flex items-center justify-center select-none">
          {/* glow */}
          <div className={`absolute w-56 h-56 rounded-full bg-violet-600/20 blur-3xl transition-all duration-700
            ${playing ? "scale-125 opacity-100" : "scale-90 opacity-40"}`} />
          {/* outer ring */}
          <div className={`absolute w-44 h-44 rounded-full border border-violet-500/20
            ${playing ? "animate-[spin-slow_10s_linear_infinite]" : ""}`} />
          {/* main circle */}
          <div className={`relative w-36 h-36 rounded-full border-2 flex flex-col items-center justify-center gap-1
            transition-all duration-500
            ${playing ? "border-violet-500 animate-[pulse-ring_2s_ease-in-out_infinite]" : "border-white/10"}`}>
            {playing ? (
              <>
                <EqBars />
                <button
                  onClick={stopCurrent}
                  className="mt-1 text-violet-300 hover:text-white transition-colors"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="6" y="6" width="4" height="12" rx="1"/>
                    <rect x="14" y="6" width="4" height="12" rx="1"/>
                  </svg>
                </button>
              </>
            ) : loading ? (
              <div className="text-zinc-500 text-xs text-center px-4 leading-relaxed">{loadingMsg || "…"}</div>
            ) : (
              <div className="text-zinc-600 text-xs">ready</div>
            )}
          </div>
        </div>

        {/* Timer + progress bar */}
        <div className="w-full flex flex-col gap-2">
          <div
            className="w-full h-1 bg-white/10 rounded-full overflow-hidden cursor-pointer group"
            onClick={seek}
          >
            <div
              className="h-full bg-gradient-to-r from-violet-500 to-fuchsia-500 rounded-full transition-all duration-100"
              style={{ width: `${progress * 100}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-zinc-600 font-mono">
            <span>{fmt(currentTime)}</span>
            {label && <span className="text-violet-500">{label}</span>}
            <span>{duration > 0 ? fmt(duration) : "–:––"}</span>
          </div>
        </div>

        {/* Input */}
        <div className="w-full flex flex-col gap-3">
          <textarea
            value={journey}
            onChange={(e) => setJourney(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) generate(); }}
            placeholder="Describe a journey… e.g. start dark and sparse, build to euphoric trance climax"
            rows={3}
            className="w-full bg-white/5 border border-white/10 rounded-2xl px-5 py-4 text-sm text-white
              placeholder:text-zinc-600 focus:outline-none focus:border-violet-500/50 resize-none"
          />
          <div className="flex gap-3">
            <button
              onClick={generate}
              disabled={loading || !journey.trim()}
              className="flex-1 h-12 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600
                text-sm font-medium text-white transition-all hover:opacity-90
                disabled:opacity-30 disabled:cursor-not-allowed"
            >
              {loading && loadingMsg ? loadingMsg : "Generate Journey  ⌘↵"}
            </button>
            <button
              onClick={generateSplice}
              disabled={loading}
              className="h-12 px-5 rounded-xl border border-white/10 text-sm text-zinc-300
                hover:bg-white/5 transition-all disabled:opacity-30 disabled:cursor-not-allowed whitespace-nowrap"
            >
              DJ Splice
            </button>
          </div>
        </div>

        {/* Mistral plan */}
        {plan.length > 0 && (
          <div className="w-full space-y-2">
            <p className="text-xs text-zinc-600 uppercase tracking-widest">Mistral's Plan</p>
            {plan.map((seg, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                <span className="text-violet-500 font-mono shrink-0">#{String(seg.id).padStart(3, "0")}</span>
                <span className="text-zinc-400">{seg.reason}</span>
              </div>
            ))}
          </div>
        )}

        {error && (
          <div className="text-xs text-red-400 bg-red-900/20 border border-red-500/20 rounded-xl px-4 py-3 w-full">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
