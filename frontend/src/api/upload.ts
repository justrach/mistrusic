import { AudioFeatures, Classification } from '../types';

interface UploadResponse {
  id: string;
  path: string;
}

interface AnalyzeResponse {
  features: AudioFeatures;
  classification: Classification[];
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch('/api/upload', { method: 'POST', body: form });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function analyzeAudio(audioId: string): Promise<AnalyzeResponse> {
  const res = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: audioId }),
  });
  if (!res.ok) throw new Error(`Analysis failed: ${res.status}`);
  return res.json();
}

export function audioUrl(id: string): string {
  return `/api/audio/${id}`;
}
