import { CORE_COUNT, EDGE_COUNT, TENDRIL_COUNT, PARTICLE_COUNT } from '../constants';

function gaussianRandom(): number {
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
}

export interface ParticleData {
  positions: Float32Array;
  seeds: Float32Array;
  densities: Float32Array;
  colorVariants: Float32Array;
}

export function generateParticles(): ParticleData {
  const positions = new Float32Array(PARTICLE_COUNT * 3);
  const seeds = new Float32Array(PARTICLE_COUNT);
  const densities = new Float32Array(PARTICLE_COUNT);
  const colorVariants = new Float32Array(PARTICLE_COUNT);

  let idx = 0;

  for (let i = 0; i < CORE_COUNT; i++) {
    const x = gaussianRandom() * 0.6;
    const y = gaussianRandom() * 0.8;
    const z = gaussianRandom() * 0.5;
    positions[idx * 3] = x;
    positions[idx * 3 + 1] = y;
    positions[idx * 3 + 2] = z;
    seeds[idx] = Math.random();
    const dist = Math.sqrt(x * x + y * y + z * z);
    densities[idx] = Math.max(0, 1 - dist / 1.5);
    colorVariants[idx] = Math.random();
    idx++;
  }

  for (let i = 0; i < EDGE_COUNT; i++) {
    const x = gaussianRandom() * 1.5;
    const y = gaussianRandom() * 1.5;
    const z = gaussianRandom() * 1.5;
    positions[idx * 3] = x;
    positions[idx * 3 + 1] = y;
    positions[idx * 3 + 2] = z;
    seeds[idx] = Math.random();
    const dist = Math.sqrt(x * x + y * y + z * z);
    densities[idx] = Math.max(0, 0.5 - dist / 4.0);
    colorVariants[idx] = Math.random();
    idx++;
  }

  for (let i = 0; i < TENDRIL_COUNT; i++) {
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    const dx = Math.sin(phi) * Math.cos(theta);
    const dy = Math.sin(phi) * Math.sin(theta);
    const dz = Math.cos(phi);
    const r = -Math.log(1 - Math.random() * 0.95) * 1.2;
    positions[idx * 3] = dx * r;
    positions[idx * 3 + 1] = dy * r;
    positions[idx * 3 + 2] = dz * r;
    seeds[idx] = Math.random();
    densities[idx] = Math.max(0, 0.2 - r / 10.0);
    colorVariants[idx] = Math.random();
    idx++;
  }

  return { positions, seeds, densities, colorVariants };
}
