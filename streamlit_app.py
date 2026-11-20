"""embellish console: the backstage view of the storefront assistant.

Same pipeline as the storefront, with every step of each answer on show.

    .venv/bin/streamlit run streamlit_app.py
"""
from __future__ import annotations

import json
import re

import streamlit as st

from rag import config, llm, pipeline
from rag.retrieve import table
from ui import render
from ui.orb import orb_html, orb_mode
from ui.styles import CSS

st.set_page_config(page_title="embellish console", page_icon="💄", layout="wide", initial_sidebar_state="auto")
st.html(f"<style>{CSS}</style>")


@st.cache_resource(show_spinner="Loading the catalogue, indexes and models…")
def warm() -> dict:
    df = table()
    from rag import index
    from rag.retrieve import rerank
    if not (config.BM25_PATH.exists() and config.CHROMA_DIR.exists()): from rag import clean; index.build(clean.load_clean())

    index.collection()
    index.bm25()
    index.embed_query("warm up")
    rerank("warm up", [df.index[0]])
    return {"products": len(df), "brands": df.brand.nunique()}


info = warm()
ss = st.session_state
ss.setdefault("turns", [])
ss.setdefault("selected", None)
ss.setdefault("pending", None)
ss.setdefault("speak", False)
ss.setdefault("tau", float(config.RERANK_THRESHOLD))
ss.setdefault("keep", int(config.RERANK_KEEP))

STARTERS = {
    "Look up": "What's the rating of Kay Beauty Waterproof 24 Hour Kajal?",
    "Compare": "Compare Maybelline Fit Me foundation and Lakme 9to5 primer",
    "Rank": "Cheapest SPF 50 sunscreen",
    "Count": "How many Biotique shampoos do you have?",
    "Partly answerable": "What are the ingredients in Lakme 9to5 primer?",
    "Off-topic": "Who won the cricket world cup?",
}


def queue(q: str) -> None:
    ss.pending = q


def select(i: int) -> None:
    ss.selected = i


def clear() -> None:
    ss.turns, ss.selected = [], None


PROVIDER = {"openai": "OpenAI", "anthropic": "Anthropic"}.get(config.LLM_PROVIDER, config.LLM_PROVIDER)

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    ok, why = llm.available()
    gen = (
        f'<div><span class="dot on"></span><span>Answers by <b>{config.CHAT_MODEL}</b> via {PROVIDER}<br>'
        f'<span class="muted">questions read by {config.ANALYZER_MODEL}</span></span></div>'
        if ok
        else f'<div><span class="dot warn"></span><span>Answer writing paused<br><span class="muted">{render.escape(why[:120])}. '
        "Questions still work, showing the retrieved products.</span></span></div>"
    )
    if config.has_openai() and ok:
        voice = '<div><span class="dot on"></span><span>Voice by OpenAI<br><span class="muted">record with the mic in the message box</span></span></div>'
    elif config.has_openai():
        voice = ('<div><span class="dot warn"></span><span>Voice partly available<br><span class="muted">read-aloud uses the browser voice; '
                 "recorded questions need OpenAI credits</span></span></div>")
    else:
        voice = '<div><span class="dot"></span><span>Voice off<br><span class="muted">add OPENAI_API_KEY to enable</span></span></div>'
    st.html(
        f"""
        <div class="wordmark">Glossary<b>.</b></div>
        <div class="sub">embellish console: the storefront assistant, with its workings on show</div>
        <div class="status">
          {gen}
          <div><span class="dot on"></span><span>{info["products"]:,} products from {info["brands"]} brands<br>
            <span class="muted">Nykaa snapshot, {config.SNAPSHOT_DATE}</span></span></div>
          {voice}
        </div>
        """
    )
    st.html("<h4>Try a question</h4>")
    with st.container(key="tries"):
        for label, q in STARTERS.items():
            st.button(f"{label}: {q}", key=f"try-{label}", on_click=queue, args=(q,))
    st.html("<h4>Tuning</h4>")
    ss.tau = st.slider(
        "Confidence threshold",
        min_value=-8.0, max_value=4.0, step=0.5, value=ss.tau,
        help="If the best reranker score is below this, embellish refuses instead of answering. "
        "Set to −2.0 from the evaluation sweep.",
    )
    ss.keep = st.slider("Products read per search", min_value=3, max_value=12, value=ss.keep)
    ss.speak = st.toggle("Read answers aloud", value=ss.speak)
    st.button("Clear conversation", on_click=clear, use_container_width=True)
    st.html(
        f'<p class="muted" style="margin-top:14px">Shopper view: <a href="{render.STORE}" target="_blank" '
        f'style="color:#f0a23b">the Glossary storefront</a></p>'
    )

# live tuning applies to this session's next question
config.RERANK_THRESHOLD = ss.tau
config.RERANK_KEEP = ss.keep

# ------------------------------------------------------------------ input
prompt = st.chat_input("Ask about a product, price or shade, or record a question", accept_audio=True, key="ask")
question = None
if ss.pending:
    question, ss.pending = ss.pending, None
elif prompt:
    question = (prompt.text or "").strip()
    if not question and prompt.audio is not None:
        try:
            question = llm.transcribe(prompt.audio.getvalue(), prompt.audio.name or "question.wav")
        except Exception as e:  # quota, network
            st.toast(f"Couldn't transcribe that recording: {str(e)[:120]}", icon="🎙️")
            question = None

if question:
    ss.turns.append({"q": question, "events": {}, "answer": "", "status": "streaming"})
    ss.selected = len(ss.turns) - 1

# ------------------------------------------------------------------ masthead
st.html(
    '<div class="masthead">' + orb_html() + "<div>"
    '<h1>embellish</h1>'
    f"<p>Ask what a shopper would ask. On the left, the answer as they'd see it. On the right, how it was made: "
    f"what was searched, which of the {info['products']:,} products were read, and whether every fact checks out.</p>"
    "</div></div>",
    unsafe_allow_javascript=True,
)
orb_signal = st.empty()

left, right = st.columns([1.12, 1], gap="large")

with left:
    st.html('<div class="pane-title"><h2>Conversation</h2><span>answers cite every product</span></div>')
    convo = st.container(key="convo")
with right:
    sel = ss.selected if ss.selected is not None and ss.selected < len(ss.turns) else None
    caption = f"for “{render.escape(ss.turns[sel]['q'][:48])}”" if sel is not None else "how every answer is made"
    st.html(f'<div class="pane-title"><h2>The workings</h2><span>{caption}</span></div>')
    work = st.container(key="workings")

with convo:
    if not ss.turns:
        st.html(
            '<div class="hello"><h3>What are you looking for today?</h3>'
            "<p>Pick a question to see each kind of answer, including the ones embellish should refuse.</p></div>"
        )
        with st.container(key="starters"):
            items = list(STARTERS.items())
            for row in range(0, len(items), 2):
                cols = st.columns(2)
                for col, (label, q) in zip(cols, items[row : row + 2]):
                    col.button(f"**{label}**  \n{q}", key=f"start-{label}", on_click=queue, args=(q,), use_container_width=True)
    live_box = None
    for i, t in enumerate(ss.turns):
        st.html(render.user_msg(t["q"]))
        if t["status"] == "streaming" and i == len(ss.turns) - 1:
            live_box = st.empty()
            live_box.html(render.bot_msg(t, selected=True))
        else:
            st.html(render.bot_msg(t, selected=i == sel))
            if i != sel:
                st.button("Show the workings", key=f"inspect{i}", on_click=select, args=(i,))
            fin = t["events"].get("final", {})
            if fin.get("latency_ms") is not None and i == sel:
                st.html(f'<div class="meta">Answered in {fin["latency_ms"] / 1000:.1f} s</div>')

with work:
    work_box = st.empty()
    if sel is None:
        work_box.html(render.how_it_works(info["products"], config.CHAT_MODEL, config.ANALYZER_MODEL, ss.tau))
    else:
        work_box.html(render.workings(ss.turns[sel]))


# Keep the conversation pinned to the newest message. One observer per page: it scrolls the pane
# whenever its content changes or an image finishes loading, stops if the reader scrolls up, and
# re-pins when a new question arrives. (No "<" before a letter or digit: Streamlit's sanitizer
# would drop the script.)
SCROLL_CONVO = """<script>
if (!window.__convoPin) {
  window.__convoPin = true;
  let users = 0, pinned = true;
  const pane = () => document.querySelector('.st-key-convo');
  const tick = () => {
    const c = pane(); if (!c) return;
    const n = c.querySelectorAll('.msg-user').length;
    if (n !== users) { users = n; pinned = true; }
    if (pinned) c.scrollTop = c.scrollHeight;
  };
  new MutationObserver(tick).observe(document.body, { childList: true, subtree: true });
  document.addEventListener('load', (e) => { if (e.target.tagName === 'IMG') tick(); }, true);
  document.addEventListener('scroll', (e) => {
    const c = e.target;
    if (c && c.classList && c.classList.contains('st-key-convo')) pinned = (80 > c.scrollHeight - c.clientHeight - c.scrollTop);
  }, true);
  tick();
}
</script>"""
scroller = st.empty()
scroller.html(SCROLL_CONVO, unsafe_allow_javascript=True)

# ------------------------------------------------------------------ run the pipeline for a new question
def speak(text: str) -> None:
    plain = re.sub(r"\s?\[P:\d+\]", "", text)
    plain = re.sub(r"₹\s?([\d,]+)", lambda m: f"{m.group(1).replace(',', '')} rupees", plain).replace("*", "")
    if config.has_openai():
        try:
            st.audio(llm.speech(plain), format="audio/mp3", autoplay=True)
            return
        except Exception:
            pass  # out of credits or offline: use the browser's voice
    st.html(
        "<script>(() => { const u = new SpeechSynthesisUtterance(" + json.dumps(plain).replace("<", "\\u003c") + ");"
        "const v = speechSynthesis.getVoices().find(v => v.lang === 'en-IN'); if (v) u.voice = v;"
        "window.__embellishOrb='speaking'; u.onend = () => { window.__embellishOrb='idle'; };"
        "speechSynthesis.cancel(); speechSynthesis.speak(u); })();</script>",
        unsafe_allow_javascript=True,
    )


if live_box is not None:
    turn = ss.turns[-1]
    history = [
        m
        for t in ss.turns[:-1]
        for m in ({"role": "user", "content": t["q"]}, {"role": "assistant", "content": t["answer"]})
        if m["content"]
    ]
    orb_signal.html(orb_mode("thinking"), unsafe_allow_javascript=True)
    for ev in pipeline.run(turn["q"], history):
        if ev["type"] == "token":
            turn["answer"] += ev["text"]
        else:
            turn["events"][ev["type"]] = ev
            if ev["type"] == "final":
                turn["answer"] = ev["answer"]
                turn["status"] = ev["status"]
        live_box.html(render.bot_msg(turn, selected=True))
        if ev["type"] != "token" or len(turn["answer"]) % 6 == 0:
            work_box.html(render.workings(turn))
    work_box.html(render.workings(turn))
    orb_signal.html(orb_mode("idle"), unsafe_allow_javascript=True)
    if ss.speak and turn["status"] in ("answered", "retrieval_only", "fallback", "out_of_scope", "smalltalk"):
        with left:
            speak(turn["answer"] if turn["status"] != "retrieval_only" else "Here are the closest matches from the catalogue.")
