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
