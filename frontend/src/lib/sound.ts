let audioContext: AudioContext | null = null;

function ctx(): AudioContext {
  if (!audioContext) {
    audioContext = new AudioContext();
  }
  return audioContext;
}

function tone(start: number, duration: number, frequency: number, gainValue: number): void {
  const context = ctx();
  const oscillator = context.createOscillator();
  const gain = context.createGain();

  oscillator.type = 'sine';
  oscillator.frequency.setValueAtTime(frequency, start);
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(gainValue, start + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);

  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start(start);
  oscillator.stop(start + duration + 0.02);
}

export function playCue(kind: 'success' | 'error' | 'level' | 'badge'): void {
  const context = ctx();
  const base = context.currentTime + 0.01;

  if (kind === 'success') {
    tone(base, 0.1, 660, 0.06);
    tone(base + 0.08, 0.12, 880, 0.05);
    return;
  }

  if (kind === 'error') {
    tone(base, 0.12, 240, 0.05);
    tone(base + 0.08, 0.18, 180, 0.04);
    return;
  }

  if (kind === 'badge') {
    tone(base, 0.08, 620, 0.05);
    tone(base + 0.07, 0.08, 820, 0.05);
    tone(base + 0.14, 0.12, 1040, 0.05);
    return;
  }

  tone(base, 0.08, 520, 0.05);
  tone(base + 0.06, 0.08, 660, 0.05);
  tone(base + 0.12, 0.08, 820, 0.05);
  tone(base + 0.18, 0.16, 1040, 0.05);
}
