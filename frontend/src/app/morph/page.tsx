"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const API = "http://localhost:8000";

// Types
interface Sound {
  id: string;
  name: string;
  description: string;
  category: string;
  duration: number;
  tags: string[];
}

interface MorphParams {
  spectral_resolution: number;
  sharpness: number;
  harmonic_balance: number;
  blend_ratio: number;
  formant_shift: number;
  preserve_transients: boolean;
  smoothing: number;
}

const PRESETS = [
  { id: "subtle", name: "Subtle", description: "Light touch, mostly source" },
  { id: "moderate", name: "Moderate", description: "Balanced blend" },
  { id: "intense", name: "Intense", description: "Strong modulator influence" },
  { id: "extreme", name: "Extreme", description: "Maximum transformation" },
];

const CATEGORIES: Record<string, { label: string; color: string; icon: string }> = {
  mechanical: { label: "Mechanical", color: "text-orange-400", icon: "⚙️" },
  instruments: { label: "Instruments", color: "text-blue-400", icon: "🎸" },
  synthetic: { label: "Synthetic", color: "text-purple-400", icon: "🔮" },
  percussion: { label: "Percussion", color: "text-yellow-400", icon: "🥁" },
  nature: { label: "Nature", color: "text-green-400", icon: "🌿" },
  vocal: { label: "Vocal", color: "text-pink-400", icon: "🎤" },
  urban: { label: "Urban", color: "text-gray-400", icon: "🏙️" },
  fx: { label: "FX", color: "text-red-400", icon: "✨" },
};

export default function MorphPage() {
  // Sounds data
  const [sounds, setSounds] = useState<Sound[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Selection state
  const [sourceSound, setSourceSound] = useState<Sound | null>(null);
  const [modulatorSound, setModulatorSound] = useState<Sound | null>(null);
  const [sourceFile, setSourceFile] = useState<File | null>(null);
  const [modulatorFile, setModulatorFile] = useState<File | null>(null);
  const [activeTab, setActiveTab] = useState<"source" | "modulator">("source");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  
  // Parameters
  const [params, setParams] = useState<MorphParams>({
    spectral_resolution: 2048,
    sharpness: 0.5,
    harmonic_balance: 0.5,
    blend_ratio: 0.5,
    formant_shift: 0,
    preserve_transients: true,
    smoothing: 0.3,
  });
  const [usePreset, setUsePreset] = useState<string | null>(null);
  
  // Processing state
  const [morphing, setMorphing] = useState(false);
  const [resultUrl, setResultUrl] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Fetch sounds on mount
  useEffect(() => {
    fetch(`${API}/api/sounds`)
      .then(r => r.json())
      .then(data => {
        setSounds(data.sounds || []);
        setCategories(data.categories || []);
        setLoading(false);
      })
      .catch(() => {
        setError("Failed to load sound library");
        setLoading(false);
      });
  }, []);

  // Filter sounds by category
  const filteredSounds = selectedCategory
    ? sounds.filter(s => s.category === selectedCategory)
    : sounds;

  // Handle file upload
  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>, type: "source" | "modulator") => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    if (type === "source") {
      setSourceFile(file);
      setSourceSound(null);
    } else {
      setModulatorFile(file);
      setModulatorSound(null);
    }
  }, []);

  // Apply preset
  const applyPreset = useCallback((presetId: string) => {
    setUsePreset(presetId);
    const presets: Record<string, Partial<MorphParams>> = {
      subtle: { blend_ratio: 0.25, sharpness: 0.3, smoothing: 0.5 },
      moderate: { blend_ratio: 0.5, sharpness: 0.5, smoothing: 0.3 },
      intense: { blend_ratio: 0.75, sharpness: 0.7, smoothing: 0.2 },
      extreme: { blend_ratio: 0.9, sharpness: 0.9, smoothing: 0.1 },
    };
    setParams(p => ({ ...p, ...presets[presetId] }));
  }, []);

  // Quick morph (for preset/style morphing)
  const quickMorph = useCallback(async () => {
    if ((!sourceSound && !sourceFile) || (!modulatorSound && !modulatorFile)) {
      setError("Please select both source and modulator sounds");
      return;
    }
    
    setMorphing(true);
    setError(null);
    
    try {
      const formData = new FormData();
      
      // Source
      if (sourceFile) {
        formData.append("source_type", "upload");
        formData.append("source_file", sourceFile);
      } else if (sourceSound) {
        formData.append("source_type", "library");
        formData.append("source_id", sourceSound.id);
      }
      
      // Modulator
      if (modulatorFile) {
        formData.append("modulator_type", "upload");
        formData.append("modulator_file", modulatorFile);
      } else if (modulatorSound) {
        formData.append("modulator_type", "library");
        formData.append("modulator_id", modulatorSound.id);
      }
      
      // Use style endpoint for quick morph
      if (usePreset) {
        formData.append("style", usePreset);
      } else {
        formData.append("style", "moderate");
      }
      
      const res = await fetch(`${API}/api/morph/style`, {
        method: "POST",
        body: formData,
      });
      
      if (!res.ok) throw new Error("Morphing failed");
      
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      setResultUrl(url);
      
      // Auto-play result
      if (audioRef.current) {
        audioRef.current.pause();
      }
      const a = new Audio(url);
      audioRef.current = a;
      a.onplay = () => setPlaying(true);
      a.onpause = () => setPlaying(false);
      a.onended = () => setPlaying(false);
      a.play().catch(() => {});
      
    } catch (err) {
      setError(err instanceof Error ? err.message : "Morphing failed");
    } finally {
      setMorphing(false);
    }
  }, [sourceSound, sourceFile, modulatorSound, modulatorFile, usePreset]);

  // Full morph with all parameters
  const fullMorph = useCallback(async () => {
    if ((!sourceSound && !sourceFile) || (!modulatorSound && !modulatorFile)) {
      setError("Please select both source and modulator sounds");
      return;
    }
    
    setMorphing(true);
    setError(null);
    
    try {
      const formData = new FormData();
      
      // Source
      if (sourceFile) {
        formData.append("source_type", "upload");
        formData.append("source_file", sourceFile);
      } else if (sourceSound) {
        formData.append("source_type", "library");
        formData.append("source_id", sourceSound.id);
      }
      
      // Modulator
      if (modulatorFile) {
        formData.append("modulator_type", "upload");
        formData.append("modulator_file", modulatorFile);
      } else if (modulatorSound) {
        formData.append("modulator_type", "library");
        formData.append("modulator_id", modulatorSound.id);
      }
      
      // Parameters
      formData.append("spectral_resolution", params.spectral_resolution.toString());
      formData.append("sharpness", params.sharpness.toString());
      formData.append("harmonic_balance", params.harmonic_balance.toString());
      formData.append("blend_ratio", params.blend_ratio.toString());
      formData.append("formant_shift", params.formant_shift.toString());
      formData.append("preserve_transients", params.preserve_transients.toString());
      formData.append("smoothing", params.smoothing.toString());
      formData.append("output_format", "wav");
      
      const res = await fetch(`${API}/api/morph`, {
        method: "POST",
        body: formData,
      });
      
      if (!res.ok) throw new Error("Morphing failed");
      
      const data = await res.json();
      
      // Poll for result
      const checkResult = async () => {
        const statusRes = await fetch(`${API}/api/morph/${data.job_id}/status`);
        const status = await statusRes.json();
        
        if (status.status === "completed") {
          const resultRes = await fetch(`${API}/api/morph/${data.job_id}/result`);
          const blob = await resultRes.blob();
          const url = URL.createObjectURL(blob);
          setResultUrl(url);
          setMorphing(false);
        } else if (status.status === "failed") {
          setError(status.error || "Morphing failed");
          setMorphing(false);
        } else {
          setTimeout(checkResult, 1000);
        }
      };
      
      checkResult();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : "Morphing failed");
      setMorphing(false);
    }
  }, [sourceSound, sourceFile, modulatorSound, modulatorFile, params]);

  // Toggle play/pause
  const togglePlay = useCallback(() => {
    const a = audioRef.current;
    if (!a) return;
    a.paused ? a.play() : a.pause();
  }, []);

  // Download result
  const downloadResult = useCallback(() => {
    if (!resultUrl) return;
    const a = document.createElement("a");
    a.href = resultUrl;
    a.download = `morphed_${Date.now()}.wav`;
    a.click();
  }, [resultUrl]);

  // Cleanup
  useEffect(() => {
    return () => {
      audioRef.current?.pause();
      if (resultUrl) URL.revokeObjectURL(resultUrl);
    };
  }, [resultUrl]);

  if (loading) {
    return (
      <main className="min-h-screen bg-black text-white pt-24 px-6">
        <div className="max-w-6xl mx-auto text-center py-20">
          <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-zinc-500 text-sm">Loading sound library...</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-black text-white pt-24 px-6 pb-16">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-8">
        <h1 className="text-3xl font-bold gradient-text mb-2">Sound Morphing Studio</h1>
        <p className="text-sm text-zinc-500 max-w-2xl">
          Blend two sounds together using spectral cross-synthesis. 
          Like shining light through colored glass — the source sound passes through the spectral characteristics of the modulator.
        </p>
      </div>

      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-6">
        
        {/* Left: Sound Selection */}
        <div className="space-y-6">
          
          {/* Source / Modulator Tabs */}
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab("source")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === "source"
                  ? "bg-violet-600 text-white"
                  : "bg-white/5 text-zinc-400 hover:bg-white/10"
              }`}
            >
              1. Source Sound
              {sourceSound && <span className="ml-2 text-xs opacity-70">({sourceSound.name})</span>}
              {sourceFile && <span className="ml-2 text-xs opacity-70">({sourceFile.name})</span>}
            </button>
            <button
              onClick={() => setActiveTab("modulator")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === "modulator"
                  ? "bg-fuchsia-600 text-white"
                  : "bg-white/5 text-zinc-400 hover:bg-white/10"
              }`}
            >
              2. Modulator Sound
              {modulatorSound && <span className="ml-2 text-xs opacity-70">({modulatorSound.name})</span>}
              {modulatorFile && <span className="ml-2 text-xs opacity-70">({modulatorFile.name})</span>}
            </button>
          </div>

          {/* Upload or Library */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-zinc-300">
                {activeTab === "source" ? "Select Source" : "Select Modulator"}
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-3 py-1.5 rounded-lg text-xs bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white transition-all"
                >
                  📁 Upload File
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="audio/*"
                  className="hidden"
                  onChange={e => handleFileSelect(e, activeTab)}
                />
              </div>
            </div>

            {/* Selected file indicator */}
            {(activeTab === "source" ? sourceFile : modulatorFile) && (
              <div className="mb-4 p-3 rounded-lg bg-green-500/10 border border-green-500/30">
                <div className="flex items-center gap-2">
                  <span className="text-green-400">✓</span>
                  <span className="text-sm text-green-300">
                    {activeTab === "source" ? sourceFile?.name : modulatorFile?.name}
                  </span>
                  <button
                    onClick={() => activeTab === "source" ? setSourceFile(null) : setModulatorFile(null)}
                    className="ml-auto text-xs text-zinc-500 hover:text-red-400"
                  >
                    Remove
                  </button>
                </div>
              </div>
            )}

            {/* Category Filter */}
            <div className="flex flex-wrap gap-1.5 mb-4">
              <button
                onClick={() => setSelectedCategory(null)}
                className={`px-2.5 py-1 rounded-md text-[10px] font-medium transition-all ${
                  selectedCategory === null
                    ? "bg-white/20 text-white"
                    : "bg-white/5 text-zinc-500 hover:bg-white/10"
                }`}
              >
                All
              </button>
              {categories.map(cat => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat === selectedCategory ? null : cat)}
                  className={`px-2.5 py-1 rounded-md text-[10px] font-medium transition-all ${
                    selectedCategory === cat
                      ? "bg-white/20 text-white"
                      : "bg-white/5 text-zinc-500 hover:bg-white/10"
                  }`}
                >
                  {CATEGORIES[cat]?.icon} {CATEGORIES[cat]?.label || cat}
                </button>
              ))}
            </div>

            {/* Sound Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-[400px] overflow-y-auto pr-1">
              {filteredSounds.map(sound => {
                const isSelected = activeTab === "source"
                  ? sourceSound?.id === sound.id
                  : modulatorSound?.id === sound.id;
                const cat = CATEGORIES[sound.category];
                
                return (
                  <button
                    key={sound.id}
                    onClick={() => {
                      if (activeTab === "source") {
                        setSourceSound(sound);
                        setSourceFile(null);
                      } else {
                        setModulatorSound(sound);
                        setModulatorFile(null);
                      }
                    }}
                    className={`p-3 rounded-xl text-left transition-all border ${
                      isSelected
                        ? "bg-violet-500/20 border-violet-500/50"
                        : "bg-white/5 border-white/5 hover:bg-white/10 hover:border-white/10"
                    }`}
                  >
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="text-sm">{cat?.icon}</span>
                      <span className={`text-[10px] uppercase tracking-wide ${cat?.color || "text-zinc-500"}`}>
                        {cat?.label || sound.category}
                      </span>
                    </div>
                    <div className="font-medium text-sm text-zinc-200 truncate">
                      {sound.name}
                    </div>
                    <div className="text-[10px] text-zinc-600 line-clamp-2 mt-0.5">
                      {sound.description}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Selected Sounds Summary */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
            <h3 className="text-sm font-semibold text-zinc-300 mb-4">Selected Pair</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className={`p-4 rounded-xl border ${sourceSound || sourceFile ? "border-violet-500/30 bg-violet-500/5" : "border-white/5 bg-white/5"}`}>
                <div className="text-[10px] uppercase tracking-wide text-violet-400 mb-1">Source</div>
                <div className="font-medium text-sm">
                  {sourceFile?.name || sourceSound?.name || "Not selected"}
                </div>
                {sourceSound && (
                  <div className="text-[10px] text-zinc-500 mt-1">{sourceSound.description}</div>
                )}
              </div>
              <div className={`p-4 rounded-xl border ${modulatorSound || modulatorFile ? "border-fuchsia-500/30 bg-fuchsia-500/5" : "border-white/5 bg-white/5"}`}>
                <div className="text-[10px] uppercase tracking-wide text-fuchsia-400 mb-1">Modulator</div>
                <div className="font-medium text-sm">
                  {modulatorFile?.name || modulatorSound?.name || "Not selected"}
                </div>
                {modulatorSound && (
                  <div className="text-[10px] text-zinc-500 mt-1">{modulatorSound.description}</div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Right: Parameters & Controls */}
        <div className="space-y-4">
          
          {/* Presets */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
            <h3 className="text-sm font-semibold text-zinc-300 mb-3">Quick Presets</h3>
            <div className="grid grid-cols-2 gap-2">
              {PRESETS.map(preset => (
                <button
                  key={preset.id}
                  onClick={() => applyPreset(preset.id)}
                  className={`p-3 rounded-xl text-left transition-all border ${
                    usePreset === preset.id
                      ? "bg-gradient-to-r from-violet-500/20 to-fuchsia-500/20 border-violet-500/50"
                      : "bg-white/5 border-white/5 hover:bg-white/10"
                  }`}
                >
                  <div className="font-medium text-sm">{preset.name}</div>
                  <div className="text-[10px] text-zinc-500">{preset.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Parameters */}
          <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-zinc-300">Parameters</h3>
              <button
                onClick={() => {
                  setUsePreset(null);
                  setParams({
                    spectral_resolution: 2048,
                    sharpness: 0.5,
                    harmonic_balance: 0.5,
                    blend_ratio: 0.5,
                    formant_shift: 0,
                    preserve_transients: true,
                    smoothing: 0.3,
                  });
                }}
                className="text-[10px] text-zinc-500 hover:text-white"
              >
                Reset
              </button>
            </div>

            <div className="space-y-4">
              {/* Blend Ratio */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-zinc-400">Blend Ratio</span>
                  <span className="text-zinc-500">{Math.round(params.blend_ratio * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={params.blend_ratio}
                  onChange={e => setParams(p => ({ ...p, blend_ratio: parseFloat(e.target.value) }))}
                  className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-violet-500"
                />
                <div className="flex justify-between text-[10px] text-zinc-600 mt-0.5">
                  <span>Source</span>
                  <span>Modulator</span>
                </div>
              </div>

              {/* Sharpness */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-zinc-400">Sharpness</span>
                  <span className="text-zinc-500">{Math.round(params.sharpness * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={params.sharpness}
                  onChange={e => setParams(p => ({ ...p, sharpness: parseFloat(e.target.value) }))}
                  className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-violet-500"
                />
              </div>

              {/* Harmonic Balance */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-zinc-400">Harmonic Balance</span>
                  <span className="text-zinc-500">{Math.round(params.harmonic_balance * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={params.harmonic_balance}
                  onChange={e => setParams(p => ({ ...p, harmonic_balance: parseFloat(e.target.value) }))}
                  className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-violet-500"
                />
              </div>

              {/* Spectral Resolution */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-zinc-400">Spectral Resolution</span>
                  <span className="text-zinc-500">{params.spectral_resolution}</span>
                </div>
                <input
                  type="range"
                  min="512"
                  max="4096"
                  step="512"
                  value={params.spectral_resolution}
                  onChange={e => setParams(p => ({ ...p, spectral_resolution: parseInt(e.target.value) }))}
                  className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-violet-500"
                />
              </div>

              {/* Formant Shift */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-zinc-400">Formant Shift</span>
                  <span className="text-zinc-500">{params.formant_shift > 0 ? "+" : ""}{params.formant_shift} semitones</span>
                </div>
                <input
                  type="range"
                  min="-12"
                  max="12"
                  step="1"
                  value={params.formant_shift}
                  onChange={e => setParams(p => ({ ...p, formant_shift: parseInt(e.target.value) }))}
                  className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-violet-500"
                />
              </div>

              {/* Smoothing */}
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-zinc-400">Smoothing</span>
                  <span className="text-zinc-500">{Math.round(params.smoothing * 100)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={params.smoothing}
                  onChange={e => setParams(p => ({ ...p, smoothing: parseFloat(e.target.value) }))}
                  className="w-full h-1.5 bg-white/10 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-violet-500"
                />
              </div>

              {/* Preserve Transients Toggle */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={params.preserve_transients}
                  onChange={e => setParams(p => ({ ...p, preserve_transients: e.target.checked }))}
                  className="w-4 h-4 rounded border-white/20 bg-white/5 text-violet-500 focus:ring-violet-500"
                />
                <span className="text-xs text-zinc-400">Preserve transients (keep sharp attacks)</span>
              </label>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="space-y-2">
            <button
              onClick={quickMorph}
              disabled={morphing || ((!sourceSound && !sourceFile) || (!modulatorSound && !modulatorFile))}
              className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-violet-600 to-fuchsia-600 text-white font-medium text-sm hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {morphing ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Processing...
                </span>
              ) : (
                "Quick Morph"
              )}
            </button>
            
            <button
              onClick={fullMorph}
              disabled={morphing || ((!sourceSound && !sourceFile) || (!modulatorSound && !modulatorFile))}
              className="w-full py-3 px-4 rounded-xl bg-white/5 text-white font-medium text-sm hover:bg-white/10 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              Full Morph (Background)
            </button>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
              {error}
            </div>
          )}

          {/* Result Player */}
          {resultUrl && (
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
              <h3 className="text-sm font-semibold text-zinc-300 mb-3">Result</h3>
              <div className="flex items-center gap-3">
                <button
                  onClick={togglePlay}
                  className="w-10 h-10 rounded-full bg-violet-600 flex items-center justify-center hover:bg-violet-500 transition-colors"
                >
                  {playing ? (
                    <span className="text-white text-xs">⏸</span>
                  ) : (
                    <span className="text-white text-xs">▶</span>
                  )}
                </button>
                <div className="flex-1">
                  <div className="text-sm font-medium text-zinc-200">Morphed Result</div>
                  <div className="text-[10px] text-zinc-500">
                    {sourceSound?.name || sourceFile?.name} + {modulatorSound?.name || modulatorFile?.name}
                  </div>
                </div>
                <button
                  onClick={downloadResult}
                  className="px-3 py-1.5 rounded-lg text-xs bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white transition-all"
                >
                  Download
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
