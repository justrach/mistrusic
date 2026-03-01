export const COLORS = {
  bg: '#F5F3EF',
  text: '#1A1A1A',
  border: '#E5E3DF',
  muted: 'rgba(0,0,0,0.4)',
  dotBase: '#D1CFC9',
  dotHover: '#999999',
} as const;

export const PALETTE = [
  '#2DD4BF', // teal
  '#F97316', // coral
  '#A78BFA', // violet
  '#FB7185', // rose
  '#34D399', // emerald
  '#FBBF24', // amber
  '#60A5FA', // sky
  '#E879F9', // fuchsia
] as const;

export const PARTICLE_COUNT = 12_000;
export const CORE_COUNT = 8_000;
export const EDGE_COUNT = 3_000;
export const TENDRIL_COUNT = 1_000;

export const DOT_GRID_SPACING = 24;
export const DOT_RADIUS = 1.5;
export const DOT_HOVER_RADIUS = 120;

export const ENTRANCE_DURATION = 1500;
export const LERP_FACTOR = 0.05;

export interface Vibe {
  label: string;
  emoji: string;
  prompt: string;
  lib: string;
}

export const VIBES: Vibe[] = [
  { label: 'Haunted House', emoji: '\u{1F47B}', prompt: 'eerie haunted house with creaking doors and ghostly whispers', lib: 'haunted' },
  { label: 'Dark Forest', emoji: '\u{1F33F}', prompt: 'dark forest with mysterious rustling and distant howls', lib: 'haunted' },
  { label: 'Hip Hop', emoji: '\u{1F3B9}', prompt: 'classic hip hop beat with deep bass and crisp snares', lib: 'hiphop' },
  { label: 'Late Night Drive', emoji: '\u{1F319}', prompt: 'late night drive through empty city streets with chill vibes', lib: 'hiphop' },
  { label: 'Euphoric Sunrise', emoji: '\u{1F305}', prompt: 'euphoric sunrise with building energy and uplifting melodies', lib: 'trance' },
  { label: 'Space Station', emoji: '\u{1F680}', prompt: 'space station floating in orbit with cosmic synth pads', lib: 'trance' },
  { label: 'Festival Peak', emoji: '\u{1F525}', prompt: 'festival peak time with maximum energy and crowd euphoria', lib: 'trance' },
  { label: 'Arctic Drift', emoji: '\u{2744}\u{FE0F}', prompt: 'arctic drift through frozen landscapes with crystalline textures', lib: 'trance' },
];

export const DEFAULT_SPLICE_COUNT = 3;
export const DEFAULT_SPLICE_CLIP_S = 5.0;

export const VIBE_COLORS: Record<string, string> = {
  haunted: '#A78BFA',
  hiphop: '#F97316',
  trance: '#2DD4BF',
};

export const BREATH_RATES: Record<string, number> = {
  trance: 1.2,
  haunted: 0.6,
  hiphop: 0.9,
};
