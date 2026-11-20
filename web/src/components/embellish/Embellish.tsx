"use client";

import { AnimatePresence, motion } from "motion/react";
import { ArrowUp, Mic, RotateCcw, Square, Volume2, VolumeX, X } from "lucide-react";
import { useEffect, useEffectEvent, useRef, useState } from "react";
import { inr } from "@/lib/format";
import MessageView from "./MessageView";
import Orb from "./Orb";
import { useEmbellish, type Msg } from "./store";
import { browserVoice, getVoice, speakable, type VoiceProvider } from "./voice";

const HOST = 320; // the orb renders at this size and is scaled to its target

const STARTERS = [
  "Best rated Lakme lipstick under ₹500",
  "Cheapest SPF 50 sunscreen",
  "Compare Maybelline Fit Me foundation and Lakme 9to5 primer",
  "How many Biotique shampoos do you have?",
];

function contextStarters(price: number) {
  return ["Is this on offer?", "What other shades are there?", `Show similar products under ${inr(Math.ceil(price / 100) * 100)}`, "How is it rated?"];
}

type Rect = { x: number; y: number; s: number };

/**
 * One orb, three homes: the hero mirror (home page), the corner launcher, and the panel header.
 * Its position is computed every frame from whichever home applies, then eased toward it, so the
 * orb visibly travels from the hero into the corner as you scroll, and into the panel when it opens.
 */
function useOrbHost(hostRef: React.RefObject<HTMLButtonElement | null>, panelSlotRef: React.RefObject<HTMLDivElement | null>) {
  useEffect(() => {
    const el = hostRef.current!;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let cur: Rect | null = null;
    let raf = 0;
    const smooth = (x: number) => x * x * (3 - 2 * x);

    const corner = (): Rect => {
      const mobile = window.innerWidth < 640;
      const s = mobile ? 56 : 68;
      const m = mobile ? 16 : 24;
      return { x: window.innerWidth - m - s, y: window.innerHeight - m - s, s };
    };

    const target = (): Rect => {
      const { open, heroSlot } = useEmbellish.getState();
      if (open && panelSlotRef.current) {
        const r = panelSlotRef.current.getBoundingClientRect();
        return { x: r.left, y: r.top, s: r.width };
      }
      const c = corner();
      if (heroSlot && heroSlot.isConnected && heroSlot.offsetParent !== null) {
        const r = heroSlot.getBoundingClientRect();
        const p = smooth(Math.min(1, Math.max(0, window.scrollY / Math.max(240, r.height * 0.9))));
        const h = { x: r.left, y: r.top, s: r.width };
        return { x: h.x + (c.x - h.x) * p, y: h.y + (c.y - h.y) * p, s: h.s + (c.s - h.s) * p };
      }
      return c;
    };

    const frame = () => {
      const t = target();
      const { open } = useEmbellish.getState();
      // scroll-linked docking tracks tightly; open/close transitions ease more softly
      const k = reduce ? 1 : open ? 0.2 : 0.32;
      cur = cur ? { x: cur.x + (t.x - cur.x) * k, y: cur.y + (t.y - cur.y) * k, s: cur.s + (t.s - cur.s) * k } : t;
      el.style.transform = `translate3d(${cur.x}px, ${cur.y}px, 0) scale(${cur.s / HOST})`;
      el.style.opacity = "1";
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [hostRef, panelSlotRef]);
}

export default function Embellish() {
  const { open, messages, busy, speakReplies, context, orbMode } = useEmbellish();
  const setOpen = useEmbellish((s) => s.setOpen);
  const ask = useEmbellish((s) => s.ask);
  const reset = useEmbellish((s) => s.reset);
  const setSpeak = useEmbellish((s) => s.setSpeak);
  const setContext = useEmbellish((s) => s.setContext);
  const setOrb = useEmbellish((s) => s.setOrb);
  const setLevel = useEmbellish((s) => s.setLevel);
  const [draft, setDraft] = useState("");
  const [listening, setListening] = useState(false);
  const [voiceNote, setVoiceNote] = useState<string | null>(null);
  const [voice, setVoice] = useState<VoiceProvider | null>(null);
  const [heroDocked, setHeroDocked] = useState(true);
  const [pill, setPill] = useState(false);
  const [hover, setHover] = useState(false);
  const hostRef = useRef<HTMLButtonElement>(null);
  const panelSlotRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const spokenRef = useRef<string | null>(null);

  useOrbHost(hostRef, panelSlotRef);

  useEffect(() => {
    getVoice().then(setVoice);
  }, []);

  // the corner hint only shows once the orb has left the hero
  useEffect(() => {
    const onScroll = () => {
      const slot = useEmbellish.getState().heroSlot;
      setHeroDocked(!!slot && slot.isConnected && slot.offsetParent !== null && window.scrollY < 200);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    const unsub = useEmbellish.subscribe((s, p) => s.heroSlot !== p.heroSlot && onScroll());
    return () => {
      window.removeEventListener("scroll", onScroll);
      unsub();
    };
  }, []);

  useEffect(() => {
    if (heroDocked || open) return;
    const show = setTimeout(() => setPill(true), 0);
    const hide = setTimeout(() => setPill(false), 4000);
    return () => {
      clearTimeout(show);
      clearTimeout(hide);
    };
  }, [heroDocked, open]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 250);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, setOpen]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const speak = (m: Msg) => {
    const v = voice ?? browserVoice();
    if (!v.canSpeak) return;
    setOrb("speaking");
    v.speak(speakable(m.text), {
      onLevel: setLevel,
      onEnd: () => {
        setOrb("idle");
        setLevel(0);
      },
    });
  };

  // read finished answers aloud when the shopper has turned that on
  const speakReply = useEffectEvent((m: Msg) => speak(m));
  useEffect(() => {
    const last = messages[messages.length - 1];
    if (!speakReplies || !last || last.role !== "assistant" || !last.status || last.status === "streaming") return;
    if (spokenRef.current === last.id) return;
    spokenRef.current = last.id;
    speakReply(last);
  }, [messages, speakReplies]);

  const send = (text = draft) => {
    if (!text.trim() || busy) return;
    (voice ?? browserVoice()).stopSpeaking();
    ask(text);
    setDraft("");
  };

  const toggleMic = () => {
    const v = voice ?? browserVoice();
    if (listening) {
      v.stopListening();
      return;
    }
    setVoiceNote(null);
    v.stopSpeaking();
    setListening(true);
    setOrb("listening");
    v.listen({
      onInterim: setDraft,
      onFinal: (t) => {
        setDraft("");
        ask(t);
      },
      onLevel: setLevel,
      onEnd: () => {
        setListening(false);
        setLevel(0);
        if (useEmbellish.getState().orbMode === "listening") setOrb("idle");
      },
      onError: (msg) => {
        setVoiceNote(msg);
        setListening(false);
        setOrb("idle");
      },
    });
  };

  const starters = context ? contextStarters(context.price) : STARTERS;
  const canListen = voice?.canListen ?? false;

  return (
    <>
      {/* the orb host: a fixed, transform-positioned button that travels between homes */}
      <button
        ref={hostRef}
        onClick={() => !open && setOpen(true)}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        aria-label={open ? "embellish" : "Ask embellish about our products"}
        tabIndex={open ? -1 : 0}
        className="fixed left-0 top-0 z-[60] origin-top-left rounded-full opacity-0 outline-none [&:focus-visible]:ring-4 [&:focus-visible]:ring-rani/40"
        style={{ width: HOST, height: HOST, cursor: open ? "default" : "pointer" }}
      >
        <Orb className="h-full w-full" />
      </button>

      <AnimatePresence>
        {!open && !heroDocked && (pill || hover) && (
          <motion.button
            initial={{ opacity: 0, x: 8 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 8 }}
            onClick={() => setOpen(true)}
            className="fixed bottom-[42px] right-[100px] z-[59] hidden rounded-full bg-kohl px-3.5 py-1.5 text-[13px] text-white shadow-lg sm:block"
          >
            Ask embellish
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {open && (
          <motion.section
            role="dialog"
            aria-label="embellish, the catalogue assistant"
            initial={{ clipPath: "circle(34px at calc(100% - 58px) calc(100% - 58px))" }}
            animate={{ clipPath: "circle(150% at calc(100% - 58px) calc(100% - 58px))" }}
            exit={{ clipPath: "circle(34px at calc(100% - 58px) calc(100% - 58px))" }}
            transition={{ duration: 0.55, ease: [0.65, 0, 0.2, 1] }}
            className="fixed inset-0 z-50 flex flex-col overflow-hidden bg-[#fffafb] sm:inset-auto sm:bottom-6 sm:right-6 sm:h-[min(740px,calc(100dvh-48px))] sm:w-[430px] sm:rounded-[28px] sm:border sm:border-line sm:shadow-[0_30px_80px_-20px_rgba(60,14,46,0.35)]"
          >
            <header className="flex items-center gap-3 border-b border-line/70 px-4 py-3">
              <div ref={panelSlotRef} className="h-10 w-10 shrink-0" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="display text-[22px] leading-none">embellish</p>
                <p className="mt-1 text-[12px] text-mauve">
                  {orbMode === "listening" ? "Listening…" : orbMode === "speaking" ? "Speaking…" : busy ? "Checking the catalogue…" : "Answers from this catalogue only"}
                </p>
              </div>
              <button
                onClick={() => {
                  setSpeak(!speakReplies);
                  if (speakReplies) (voice ?? browserVoice()).stopSpeaking();
                }}
                aria-pressed={speakReplies}
                aria-label={speakReplies ? "Stop reading answers aloud" : "Read answers aloud"}
                title={speakReplies ? "Reading answers aloud" : "Read answers aloud"}
                className={`grid h-9 w-9 place-items-center rounded-full transition-colors ${speakReplies ? "bg-rani text-white" : "text-kohl-soft hover:bg-petal"}`}
              >
                {speakReplies ? <Volume2 size={18} /> : <VolumeX size={18} />}
              </button>
              <button onClick={reset} aria-label="Start a new conversation" title="New conversation" className="grid h-9 w-9 place-items-center rounded-full text-kohl-soft hover:bg-petal">
                <RotateCcw size={17} />
              </button>
              <button onClick={() => setOpen(false)} aria-label="Close embellish" className="grid h-9 w-9 place-items-center rounded-full text-kohl-soft hover:bg-petal">
                <X size={19} />
              </button>
            </header>

            {context && (
              <div className="flex items-center gap-2 border-b border-line/70 bg-petal/60 px-4 py-2 text-[12.5px]">
                <span className="text-mauve">Asking about</span>
                <span className="min-w-0 flex-1 truncate font-medium">{context.title}</span>
                <button onClick={() => setContext(null)} aria-label="Stop asking about this product" className="text-mauve hover:text-rani">
                  <X size={14} />
                </button>
              </div>
            )}

            <div ref={scrollRef} className="thin-scroll flex-1 space-y-5 overflow-y-auto px-4 py-5" data-lenis-prevent>
              {messages.length === 0 && (
                <div className="pt-2">
                  <p className="display text-[30px] leading-[1.05]">
                    {context ? "What would you like to know about it?" : "What are you looking for today?"}
                  </p>
                  <p className="mt-3 max-w-[34ch] text-[14px] text-kohl-soft">
                    I know every product on these shelves: prices, offers, shades, ratings and stock. If something isn&apos;t in the catalogue, I&apos;ll tell you rather than guess.
                  </p>
                  <div className="mt-5 flex flex-col items-start gap-2">
                    {starters.map((s) => (
                      <button
                        key={s}
                        onClick={() => send(s)}
                        className="rounded-2xl border border-line bg-white px-3.5 py-2 text-left text-[13.5px] text-kohl-soft transition-colors hover:border-rani hover:text-rani"
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map((m) => (
                <MessageView key={m.id} m={m} onSpeak={speak} />
              ))}
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                send();
              }}
              className="border-t border-line/70 p-3"
            >
              {voiceNote && <p className="mb-2 px-1 text-[12px] text-rani-deep">{voiceNote}</p>}
              <div className={`flex items-end gap-2 rounded-[22px] border bg-white p-1.5 pl-4 transition-colors ${listening ? "border-rani" : "border-line focus-within:border-kohl-soft"}`}>
                <textarea
                  ref={inputRef}
                  rows={1}
                  value={draft}
                  maxLength={1000}
                  onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      send();
                    }
                  }}
                  placeholder={listening ? "Listening…" : "Ask about a product, price or shade"}
                  aria-label="Your question"
                  className="max-h-28 min-h-[38px] flex-1 resize-none bg-transparent py-2 text-[15px] outline-none placeholder:text-mauve/70 focus-visible:outline-none"
                />
                {canListen && (
                  <button
                    type="button"
                    onClick={toggleMic}
                    aria-pressed={listening}
                    aria-label={listening ? "Stop listening" : "Ask with your voice"}
                    className={`grid h-[38px] w-[38px] shrink-0 place-items-center rounded-full transition-colors ${listening ? "bg-rani text-white" : "text-kohl-soft hover:bg-petal"}`}
                  >
                    {listening ? <Square size={14} fill="currentColor" /> : <Mic size={18} />}
                  </button>
                )}
                <button
                  type="submit"
                  disabled={!draft.trim() || busy}
                  aria-label="Send"
                  className="grid h-[38px] w-[38px] shrink-0 place-items-center rounded-full bg-kohl text-white transition-opacity disabled:opacity-30"
                >
                  <ArrowUp size={18} strokeWidth={2.4} />
                </button>
              </div>
            </form>
          </motion.section>
        )}
      </AnimatePresence>
    </>
  );
}
