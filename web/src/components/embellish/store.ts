"use client";

import { create } from "zustand";
import { API, type Aggregate, type RetrievedRecord } from "@/lib/api";

export type Status =
  | "streaming"
  | "answered"
  | "fallback"
  | "out_of_scope"
  | "withheld"
  | "retrieval_only"
  | "smalltalk"
  | "error";

export type Analysis = {
  scope: string;
  standalone_question: string;
  operation: string;
  sort_by: string | null;
  sub_queries: { text: string; filters: Record<string, unknown> }[];
  unsupported_parts: string[];
};

export type Msg = {
  id: string;
  role: "user" | "assistant";
  text: string;
  status?: Status;
  records?: RetrievedRecord[];
  aggregates?: Aggregate[];
  analysis?: Analysis;
  analyzer?: string;
  reason?: string;
  topScore?: number | null;
  problems?: string[];
  suggestions?: string[];
  cited?: string[];
  latencyMs?: number;
};

export type OrbMode = "idle" | "listening" | "thinking" | "speaking";

export type ContextProduct = { id: string; title: string; price: number };

type State = {
  open: boolean;
  messages: Msg[];
  busy: boolean;
  orbMode: OrbMode;
  level: number; // 0..1, mic or speech energy, drives the orb surface
  speakReplies: boolean;
  context: ContextProduct | null;
  heroSlot: HTMLElement | null;
  setOpen: (open: boolean) => void;
  setOrb: (mode: OrbMode) => void;
  setLevel: (level: number) => void;
  setSpeak: (on: boolean) => void;
  setContext: (p: ContextProduct | null) => void;
  setHeroSlot: (el: HTMLElement | null) => void;
  ask: (question: string) => Promise<Msg | undefined>;
  reset: () => void;
};

const uid = () => Math.random().toString(36).slice(2, 10);

export const useEmbellish = create<State>()((set, get) => ({
  open: false,
  messages: [],
  busy: false,
  orbMode: "idle",
  level: 0,
  speakReplies: false,
  context: null,
  heroSlot: null,
  setOpen: (open) => set({ open }),
  setOrb: (orbMode) => set({ orbMode }),
  setLevel: (level) => set({ level }),
  setSpeak: (speakReplies) => set({ speakReplies }),
  setContext: (context) => set({ context }),
  setHeroSlot: (heroSlot) => set({ heroSlot }),
  reset: () => set({ messages: [] }),

  ask: async (question) => {
    const q = question.trim();
    if (!q || get().busy) return;
    const history = get()
      .messages.filter((m) => m.text && m.status !== "streaming")
      .slice(-12)
      .map((m) => ({ role: m.role, content: m.text.slice(0, 3000) }));
    const user: Msg = { id: uid(), role: "user", text: q };
    const bot: Msg = { id: uid(), role: "assistant", text: "", status: "streaming" };
    set((s) => ({ messages: [...s.messages, user, bot], busy: true, open: true, orbMode: "thinking" }));

    const patch = (p: Partial<Msg>) =>
      set((s) => ({ messages: s.messages.map((m) => (m.id === bot.id ? { ...m, ...p } : m)) }));
    const current = () => get().messages.find((m) => m.id === bot.id);

    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: q, history, product_id: get().context?.id ?? null }),
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let cut: number;
        while ((cut = buf.indexOf("\n\n")) >= 0) {
          const block = buf.slice(0, cut);
          buf = buf.slice(cut + 2);
          const data = block.split("\n").find((l) => l.startsWith("data: "));
          if (!data) continue;
          const ev = JSON.parse(data.slice(6));
          if (ev.type === "analysis") patch({ analysis: ev.analysis, analyzer: ev.analyzer });
          else if (ev.type === "sources")
            patch({ records: ev.records, aggregates: ev.aggregates, reason: ev.reason, topScore: ev.top_score });
          else if (ev.type === "token") patch({ text: (current()?.text ?? "") + ev.text });
          else if (ev.type === "final")
            patch({
              text: ev.answer,
              status: ev.status,
              problems: ev.problems,
              suggestions: ev.suggestions,
              cited: ev.cited,
              latencyMs: ev.latency_ms,
              reason: ev.reason ?? current()?.reason,
            });
        }
      }
      if (current()?.status === "streaming") patch({ status: "error", text: "The answer stopped part-way. Ask again to retry." });
    } catch {
      patch({
        status: "error",
        text: "I can't reach the catalogue right now. Check that the API is running on port 8000, then ask again.",
      });
    } finally {
      set({ busy: false, orbMode: "idle" });
    }
    return current();
  },
}));
