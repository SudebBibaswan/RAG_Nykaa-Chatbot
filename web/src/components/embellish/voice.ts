"use client";

/**
 * Voice layer. Everything goes through the VoiceProvider interface so a premium
 * provider (ElevenLabs / OpenAI via the API's /api/voice/* routes) can replace the
 * browser implementation without touching the UI.
 */
import { API } from "@/lib/api";

export interface VoiceProvider {
  readonly canListen: boolean;
  readonly canSpeak: boolean;
  listen(h: {
    onInterim: (text: string) => void;
    onFinal: (text: string) => void;
    onLevel: (level: number) => void;
    onEnd: () => void;
    onError: (message: string) => void;
  }): void;
  stopListening(): void;
  speak(text: string, h: { onLevel: (l: number) => void; onEnd: () => void }): void;
  stopSpeaking(): void;
}

/* eslint-disable @typescript-eslint/no-explicit-any */
type SR = any;

function recognitionCtor(): (new () => SR) | null {
  if (typeof window === "undefined") return null;
  const w = window as any;
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

/** Turn an answer into something pleasant to hear: no citations, no markdown, rupees spoken. */
export function speakable(text: string): string {
  return text
    .replace(/\s?\[P:\d+\]/g, "")
    .replace(/₹\s?([\d,]+)/g, (_, n) => `${n.replace(/,/g, "")} rupees`)
    .replace(/(\d+)%/g, "$1 percent")
    .replace(/(\d\.\d)\/5/g, "$1 out of 5")
    .replace(/[*_#`]/g, "")
    .replace(/^\s*-\s+/gm, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

class BrowserVoice implements VoiceProvider {
  private rec: SR | null = null;
  private stream: MediaStream | null = null;
  private ctx: AudioContext | null = null;
  private raf = 0;
  private speakTimer = 0;

  get canListen() {
    return recognitionCtor() !== null;
  }
  get canSpeak() {
    return typeof window !== "undefined" && "speechSynthesis" in window;
  }

  listen(h: Parameters<VoiceProvider["listen"]>[0]) {
    const Ctor = recognitionCtor();
    if (!Ctor) return h.onError("Voice input isn't supported in this browser. Try Chrome or Edge.");
    this.stopListening();
    const rec = new Ctor();
    rec.lang = "en-IN";
    rec.interimResults = true;
    rec.continuous = false;
    rec.maxAlternatives = 1;
    let finalText = "";
    rec.onresult = (e: any) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) finalText += r[0].transcript;
        else interim += r[0].transcript;
      }
      h.onInterim((finalText + interim).trim());
    };
    rec.onerror = (e: any) => {
      const msg =
        e.error === "not-allowed"
          ? "Microphone access is blocked. Allow it in the browser's site settings."
          : e.error === "no-speech"
            ? "I didn't hear anything. Tap the mic and try again."
            : "Voice input stopped. Tap the mic to try again.";
      h.onError(msg);
    };
    rec.onend = () => {
      this.releaseMic();
      if (finalText.trim()) h.onFinal(finalText.trim());
      h.onEnd();
    };
    this.rec = rec;
    rec.start();
    this.meter(h.onLevel);
  }

  /** A separate mic stream feeds an analyser so the orb can react to the voice. */
  private async meter(onLevel: (l: number) => void) {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.ctx = new AudioContext();
      const src = this.ctx.createMediaStreamSource(this.stream);
      const an = this.ctx.createAnalyser();
      an.fftSize = 512;
      src.connect(an);
      const data = new Uint8Array(an.fftSize);
      const tick = () => {
        an.getByteTimeDomainData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i++) {
          const v = (data[i] - 128) / 128;
          sum += v * v;
        }
        onLevel(Math.min(1, Math.sqrt(sum / data.length) * 4));
        this.raf = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      /* the level meter is decoration; recognition still works without it */
    }
  }

  private releaseMic() {
    cancelAnimationFrame(this.raf);
    this.stream?.getTracks().forEach((t) => t.stop());
    this.stream = null;
    this.ctx?.close().catch(() => {});
    this.ctx = null;
  }

  stopListening() {
    try {
      this.rec?.stop();
    } catch {}
    this.rec = null;
    this.releaseMic();
  }

  speak(text: string, h: { onLevel: (l: number) => void; onEnd: () => void }) {
    if (!this.canSpeak) return h.onEnd();
    this.stopSpeaking();
    const u = new SpeechSynthesisUtterance(text);
    const voices = speechSynthesis.getVoices();
    u.voice =
      voices.find((v) => v.lang === "en-IN") ?? voices.find((v) => v.lang.startsWith("en") && /female|samantha|veena/i.test(v.name)) ?? null;
    u.rate = 1.02;
    // speechSynthesis gives no audio levels, so word boundaries pulse the orb instead
    u.onboundary = () => {
      h.onLevel(0.55 + Math.random() * 0.35);
      window.clearTimeout(this.speakTimer);
      this.speakTimer = window.setTimeout(() => h.onLevel(0.15), 180);
    };
    u.onend = () => {
      h.onLevel(0);
      h.onEnd();
    };
    u.onerror = u.onend;
    speechSynthesis.speak(u);
  }

  stopSpeaking() {
    if (this.canSpeak) speechSynthesis.cancel();
  }
}

/** Server voice (ElevenLabs / OpenAI) - used only when the API reports a premium TTS key. */
class ServerVoice extends BrowserVoice {
  private audio: HTMLAudioElement | null = null;

  speak(text: string, h: { onLevel: (l: number) => void; onEnd: () => void }) {
    fetch(`${API}/api/voice/tts`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ text }) })
      .then((r) => (r.ok ? r.blob() : Promise.reject()))
      .then((blob) => {
        this.audio = new Audio(URL.createObjectURL(blob));
        const ctx = new AudioContext();
        const an = ctx.createAnalyser();
        ctx.createMediaElementSource(this.audio).connect(an);
        an.connect(ctx.destination);
        const data = new Uint8Array(an.fftSize);
        let raf = 0;
        const tick = () => {
          an.getByteTimeDomainData(data);
          let s = 0;
          for (const v of data) s += ((v - 128) / 128) ** 2;
          h.onLevel(Math.min(1, Math.sqrt(s / data.length) * 4));
          raf = requestAnimationFrame(tick);
        };
        this.audio.onended = () => {
          cancelAnimationFrame(raf);
          h.onLevel(0);
          ctx.close();
          h.onEnd();
        };
        this.audio.play();
        tick();
      })
      .catch(() => super.speak(text, h)); // not configured -> browser voice
  }

  stopSpeaking() {
    this.audio?.pause();
    super.stopSpeaking();
  }
}

let provider: VoiceProvider | null = null;

export async function getVoice(): Promise<VoiceProvider> {
  if (provider) return provider;
  try {
    const health = await fetch(`${API}/api/health`).then((r) => r.json());
    provider = health?.voice?.tts && health.voice.tts !== "browser" ? new ServerVoice() : new BrowserVoice();
  } catch {
    provider = new BrowserVoice();
  }
  return provider;
}

export function browserVoice(): VoiceProvider {
  return provider ?? new BrowserVoice();
}
