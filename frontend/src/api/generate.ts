import { PlanSegment } from '../types';

const BASE_URL = 'http://localhost:8000';

export interface GenerateResult {
  audioUrl: string;
  plan: PlanSegment[];
  vibe: string;
}

export interface SpliceResult {
  audioUrl: string;
}

export async function generate(journey: string, vibe: string): Promise<GenerateResult> {
  const res = await fetch(`${BASE_URL}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ journey, vibe }),
  });

  if (!res.ok) {
    let msg = `Generate failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.error) msg = body.error;
    } catch { /* ignore */ }
    throw new Error(msg);
  }

  const planHeader = res.headers.get('X-Plan');
  let plan: PlanSegment[] = [];
  try {
    if (planHeader) plan = JSON.parse(planHeader);
  } catch {
    // ignore parse errors
  }

  const vibeHeader = res.headers.get('X-Vibe') || vibe;
  const blob = await res.blob();
  const audioUrl = URL.createObjectURL(blob);

  return { audioUrl, plan, vibe: vibeHeader };
}

export async function splice(count: number, clipS: number, vibe: string): Promise<SpliceResult> {
  const res = await fetch(`${BASE_URL}/splice`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ count, clip_s: clipS, vibe }),
  });

  if (!res.ok) {
    let msg = `Splice failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.error) msg = body.error;
    } catch { /* ignore */ }
    throw new Error(msg);
  }

  const blob = await res.blob();
  const audioUrl = URL.createObjectURL(blob);

  return { audioUrl };
}

export interface HealthResponse {
  status: string;
  mistral: boolean;
  libraries: { trance: number; haunted: number; hiphop: number };
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${BASE_URL}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}
