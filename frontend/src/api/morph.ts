export interface MorphMessage {
  type: 'step' | 'complete';
  step_number?: number;
  model_output?: string;
  observations?: string;
  output_id?: string;
  features?: Record<string, number>;
  classification?: { label: string; confidence: number }[];
}

export function connectMorph(
  soundAId: string,
  soundBId: string | undefined,
  intent: string,
  onMessage: (msg: MorphMessage) => void,
  onError: (err: string) => void,
  onClose: () => void,
): WebSocket {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${location.host}/api/morph`);

  ws.onopen = () => {
    const payload: Record<string, string> = { sound_a_id: soundAId, intent };
    if (soundBId) payload.sound_b_id = soundBId;
    ws.send(JSON.stringify(payload));
  };

  ws.onmessage = (e) => {
    try {
      const msg: MorphMessage = JSON.parse(e.data);
      onMessage(msg);
    } catch {
      onError('Invalid message from server');
    }
  };

  ws.onerror = () => onError('WebSocket connection error');
  ws.onclose = onClose;

  return ws;
}
