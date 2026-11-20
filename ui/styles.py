"""Glossary tokens applied to Streamlit. Same palette and type as the storefront."""

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,400..900;1,6..96,400..900&family=Schibsted+Grotesk:wght@400..800&display=swap');

:root {
  --powder:#fbf4f6; --blush:#f6dfe7; --petal:#fdeaf0; --kohl:#1e1424; --kohl-soft:#3a2a40;
  --mauve:#8c6a80; --rani:#e2185b; --rani-deep:#b40f47; --marigold:#f0a23b; --line:#ead3dc; --ok:#1f7a4d;
}

/* ---------- chrome ---------- */
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"], footer, #MainMenu { display:none !important; }
.stApp { background: var(--powder); }
[data-testid="stMainBlockContainer"] { padding: 22px 40px 16px; max-width: 1480px; }
@media (max-width: 900px) { [data-testid="stMainBlockContainer"] { padding: 20px 16px 120px; } }
.display, .stApp h1, .stApp h2, .stApp h3 {
  font-family: 'Bodoni Moda', Didot, serif !important; font-optical-sizing: auto; font-variation-settings: "opsz" 96;
  letter-spacing: -0.015em; font-weight: 400 !important;
}

/* ---------- sidebar: the kohl panel ---------- */
[data-testid="stSidebar"] { border-right: none; }
[data-testid="stSidebarContent"] { padding-top: 6px; }
[data-testid="stSidebar"] .wordmark { font-family:'Bodoni Moda',serif; font-size:40px; line-height:1; color:#fff; letter-spacing:-0.03em; }
[data-testid="stSidebar"] .wordmark b { color: var(--rani); font-weight:400; }
[data-testid="stSidebar"] .sub { color:#cdb6c3; font-size:13px; margin-top:6px; }
[data-testid="stSidebar"] .status { margin-top:18px; display:grid; gap:10px; }
[data-testid="stSidebar"] .status div { display:flex; gap:10px; align-items:flex-start; font-size:13px; color:#e8d7df; line-height:1.4; }
[data-testid="stSidebar"] .dot { width:8px; height:8px; border-radius:50%; margin-top:5px; flex-shrink:0; background:#6b5a73; }
[data-testid="stSidebar"] .dot.on { background:#5fd39a; box-shadow:0 0 10px 2px rgba(95,211,154,.45); }
[data-testid="stSidebar"] .dot.warn { background: var(--marigold); box-shadow:0 0 10px 2px rgba(240,162,59,.45); }
[data-testid="stSidebar"] .dot.off { background:#ff7a9c; }
[data-testid="stSidebar"] .muted { color:#a58d9b; font-size:12px; }
[data-testid="stSidebar"] h4 { font-family:'Schibsted Grotesk',sans-serif !important; font-size:13px; font-weight:600 !important; color:#fff; margin:22px 0 8px; letter-spacing:0; }
.st-key-tries button {
  width:100%; justify-content:flex-start; text-align:left; background:transparent; color:#f1e3ea;
  border:1px solid #3d2c45; border-radius:14px; padding:8px 12px; min-height:0; font-size:13px; line-height:1.35;
}
.st-key-tries button:hover { border-color: var(--marigold); color:#fff; background:#2c1f33; }
.st-key-tries button p { font-size:13px; }
.st-key-tries [data-testid="stVerticalBlock"] { gap:6px; }

/* ---------- masthead ---------- */
.masthead { display:flex; align-items:center; gap:20px; margin: 0 0 14px; }
.masthead h1 { font-size: clamp(40px, 4.2vw, 60px) !important; line-height:.95 !important; margin:0 !important; padding:0 !important; color: var(--kohl); }
.masthead p { margin:8px 0 0; max-width: 78ch; color: var(--kohl-soft); font-size: 15px; line-height:1.5; }
.orb-wrap { width: 84px; height: 84px; flex-shrink:0; position:relative; }
.orb-wrap canvas { width:100%; height:100%; display:block; }
.orb-wrap .halo { position:absolute; inset:-10px; border-radius:50%; border:1px solid rgba(30,20,36,.08); }

/* ---------- panes ---------- */
.pane-title { display:flex; align-items:baseline; justify-content:space-between; gap: 16px; margin: 0 0 10px; }
.pane-title h2 { font-size: 30px !important; margin:0 !important; padding:0 !important; color: var(--kohl); white-space: nowrap; }
.pane-title span { font-size: 13px; color: var(--mauve); min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.st-key-convo, .st-key-workings { background: #fffafb; border: 1px solid var(--line) !important; border-radius: 26px;
  /* fit the viewport: Streamlit pins chat pages to the bottom, so overflow would hide the masthead */
  height: max(340px, calc(100dvh - 392px)) !important; max-height: max(340px, calc(100dvh - 392px)) !important;
  flex: 0 0 auto !important; overflow-y: auto !important; flex-wrap: nowrap !important; overscroll-behavior: contain; padding: 14px 18px !important;
  scrollbar-width: thin; scrollbar-color: var(--line) transparent; }
[data-testid="stHtml"] { width: 100%; }


/* ---------- messages ---------- */
.msg-user { display:flex; justify-content:flex-end; margin: 8px 0 4px; }
.msg-user p { margin:0; max-width: 80%; background: var(--kohl); color:#fff; padding: 10px 16px; border-radius: 20px 20px 6px 20px; font-size: 15px; line-height:1.4; }
.msg-bot { display:flex; gap:12px; margin: 14px 0 2px; }
.msg-bot .av { width:30px; height:30px; border-radius:50%; flex-shrink:0; margin-top:2px;
  background: radial-gradient(circle at 34% 30%, #fff2f6 0%, #fdc2d6 18%, #e2185b 52%, #3c0e2e 92%); }
.msg-bot.selected .av { box-shadow: 0 0 0 3px var(--powder), 0 0 0 5px var(--marigold); }
.msg-bot .body { flex:1; min-width:0; font-size: 15px; line-height: 1.6; color: var(--kohl); }
.msg-bot .body p { margin: 4px 0 6px; }
.msg-bot .body ul { margin: 6px 0; padding: 0; list-style: none; }
.msg-bot .body li { position: relative; padding-left: 16px; margin: 5px 0; }
.msg-bot .body li::before { content:""; position:absolute; left:2px; top:.62em; width:6px; height:6px; border-radius:50%; background: var(--rani); opacity:.75; }
.msg-bot .name { font-family:'Bodoni Moda',serif; font-size: 17px; line-height:1; color: var(--kohl); margin-bottom: 4px; }
.cite { display:inline-flex; align-items:center; gap:4px; vertical-align: baseline; transform: translateY(2px);
  border:1px solid var(--line); background:#fff; border-radius:999px; padding: 1px 7px 1px 2px; margin: 0 2px;
  font-size: 11px; font-weight: 600; color: var(--rani) !important; text-decoration:none !important; }
.cite:hover { border-color: var(--rani); }
.cite img { width:16px; height:16px; border-radius:50%; object-fit:cover; background: var(--petal); }
.note { display:flex; gap:8px; background: var(--petal); border-radius: 14px; padding: 9px 12px; font-size: 13px; color: var(--kohl-soft); margin: 4px 0 8px; }
.refusal { border: 1.5px dashed rgba(226,24,91,.5); background: #fff; border-radius: 18px; padding: 12px 14px; }
.refusal b { display:block; font-size: 15px; margin-bottom: 2px; }
.refusal span { font-size: 14px; color: var(--kohl-soft); }
.caret::after { content:""; display:inline-block; width:7px; height:1em; margin-left:2px; vertical-align:-2px; background:var(--rani); border-radius:2px; animation: blink .9s steps(1) infinite; }
@keyframes blink { 50% { opacity: 0; } }
.cards { display:flex; gap:10px; overflow-x:auto; padding: 8px 2px 4px; scrollbar-width: thin; }
.card { flex: 0 0 210px; display:flex; gap:10px; background:#fff; border:1px solid var(--line); border-radius: 16px; padding: 8px; text-decoration:none !important; color: var(--kohl) !important; }
.card:hover { border-color: var(--rani); }
.card img { width: 58px; height: 58px; object-fit: contain; border-radius: 12px; background: var(--petal); flex-shrink:0; }
.card .t { font-size: 12px; line-height: 1.3; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.card .p { font-size: 13px; font-weight: 600; margin-top: 4px; }
.card .p s { color: var(--mauve); font-weight: 400; margin-left: 4px; font-size: 11.5px; }
.card .p em { color: var(--rani); font-style: normal; margin-left: 4px; font-size: 11.5px; }
.meta { font-size: 12px; color: var(--mauve); margin: 6px 0 0 42px; }

/* inspect buttons under each answer */
[class*="st-key-inspect"] button { background: transparent; border: none; color: var(--mauve); font-size: 12.5px; padding: 0 0 0 42px; min-height: 0; }
[class*="st-key-inspect"] button:hover { color: var(--rani); background: transparent; }
[class*="st-key-inspect"] button p { font-size: 12.5px; }

/* ---------- empty state ---------- */
.hello h3 { font-size: 34px !important; margin: 10px 0 6px !important; color: var(--kohl); }
.hello p { color: var(--kohl-soft); font-size: 15px; max-width: 46ch; margin: 0 0 14px; }
.st-key-starters [data-testid="stHorizontalBlock"] { gap: 10px; }
.st-key-starters button {
  width: 100%; min-height: 86px; border-radius: 18px; background:#fff; border: 1px solid var(--line);
  justify-content: flex-start; align-items: flex-start; text-align:left; padding: 12px 14px;
}
.st-key-starters button > div, .st-key-starters button [data-testid="stMarkdownContainer"] { width: 100%; text-align: left; justify-content: flex-start; }
.st-key-starters button:hover { border-color: var(--rani); background: #fff; color: var(--kohl); }
.st-key-starters button p { font-size: 14px; line-height: 1.35; }

/* ---------- workings ---------- */
.rail { display:grid; grid-template-columns: repeat(5, 1fr); gap: 0; margin: 4px 0 18px; position: relative; }
.rail .st { position:relative; padding-top: 22px; text-align:left; }
.rail .st::before { content:""; position:absolute; top: 7px; left: 0; right: 0; height: 2px; background: var(--line); }
.rail .st:first-child::before { left: 7px; }
.rail .st:last-child::before { right: calc(100% - 8px); }
.rail .st.done::before, .rail .st.active::before { background: var(--rani); }
.rail .st i { position:absolute; top: 0; left: 0; width: 16px; height: 16px; border-radius: 50%; background: #fff; border: 2px solid var(--line); }
.rail .st.done i { background: var(--rani); border-color: var(--rani); }
.rail .st.active i { background: var(--marigold); border-color: var(--marigold); box-shadow: 0 0 0 5px rgba(240,162,59,.25); animation: pulse 1.1s ease-in-out infinite; }
.rail .st.skip i { background: var(--powder); border-style: dashed; }
.rail .st.fail i { background: #fff; border-color: var(--rani-deep); }
.rail .st b { display:block; font-size: 13px; font-weight: 600; color: var(--kohl); }
.rail .st span { display:block; font-size: 11.5px; color: var(--mauve); margin-top: 1px; padding-right: 8px; }
@keyframes pulse { 50% { box-shadow: 0 0 0 9px rgba(240,162,59,.08); } }
.sec { margin: 0 0 18px; }
.sec h4 { font-family: 'Schibsted Grotesk', sans-serif !important; font-size: 13.5px; font-weight: 600 !important; margin: 0 0 8px; color: var(--kohl); letter-spacing: 0; }
.chips { display:flex; flex-wrap: wrap; gap: 6px; }
.chip { font-size: 12px; padding: 3px 9px; border-radius: 999px; background: #fff; border: 1px solid var(--line); color: var(--kohl-soft); }
.chip.k { background: var(--kohl); color: #fff; border-color: var(--kohl); }
.chip.warn { background: #fff6ea; border-color: #f6cf98; color: #8a4b00; }
.sq { background: #fff; border: 1px solid var(--line); border-radius: 14px; padding: 9px 11px; margin-bottom: 8px; }
.sq q { display:block; font-size: 13.5px; color: var(--kohl); margin-bottom: 6px; quotes: "“" "”"; }
.agg { display:flex; align-items: baseline; gap: 10px; background: var(--kohl); color: #fff; border-radius: 16px; padding: 12px 14px; margin-bottom: 8px; }
.agg strong { font-family: 'Bodoni Moda', serif; font-size: 34px; font-weight: 400; line-height: 1; }
.agg span { font-size: 13px; color: #e5d3dc; }
.rec { display:grid; grid-template-columns: 40px 1fr auto; gap: 10px; align-items: center; padding: 7px 8px; border-radius: 12px; border: 1px solid transparent; }
.rec:nth-child(odd) { background: rgba(253,234,240,.45); }
.rec.cited { border-color: rgba(226,24,91,.35); background: #fff; }
.rec img { width: 40px; height: 40px; border-radius: 10px; object-fit: contain; background: #fff; }
.rec .t { font-size: 12.5px; line-height: 1.3; color: var(--kohl); overflow:hidden; display:-webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.rec .m { font-size: 11.5px; color: var(--mauve); margin-top: 2px; display:flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.rec .bar { width: 64px; height: 5px; border-radius: 3px; background: var(--line); position: relative; overflow: hidden; display:inline-block; }
.rec .bar i { position:absolute; inset: 0 auto 0 0; border-radius: 3px; background: var(--rani); }
.rec .bar.neg i { background: var(--mauve); opacity: .5; }
.rec .tag { font-size: 10.5px; padding: 1px 6px; border-radius: 6px; background: var(--petal); color: var(--rani-deep); }
.rec .by { font-size: 10.5px; color: var(--mauve); text-align: right; white-space: nowrap; }
.verdict { display:flex; gap: 10px; align-items: flex-start; padding: 11px 13px; border-radius: 14px; font-size: 13.5px; line-height: 1.45; }
.verdict.ok { background: #eaf7f0; color: #14532d; }
.verdict.bad { background: #fff1f4; color: var(--rani-deep); }
.verdict.neutral { background: var(--petal); color: var(--kohl-soft); }
.verdict .ic { font-size: 16px; line-height: 1.2; }
.how { counter-reset: s; display:grid; gap: 10px; }
.how li { list-style: none; display:grid; grid-template-columns: 28px 1fr; gap: 10px; align-items: start; }
.how li::before { counter-increment: s; content: counter(s); width: 26px; height: 26px; border-radius: 50%; display:grid; place-items:center;
  background: var(--kohl); color: #fff; font-size: 12px; font-weight: 600; }
.how li b { display:block; font-size: 14px; color: var(--kohl); }
.how li span { font-size: 13px; color: var(--kohl-soft); line-height: 1.45; }
.how { padding: 0; margin: 4px 0 0; }

/* ---------- composer ---------- */
[data-testid="stBottomBlockContainer"] { background: linear-gradient(to top, var(--powder) 70%, rgba(251,244,246,0)); padding-bottom: 22px; max-width: 1480px; }
[data-testid="stChatInput"] { border-radius: 26px !important; border: 1px solid rgba(30,20,36,.18) !important; background: #fff !important;
  box-shadow: 0 14px 40px -20px rgba(60,14,46,.45); }
[data-testid="stChatInput"]:focus-within { border-color: var(--kohl-soft) !important; }
[data-testid="stChatInput"] > div, [data-testid="stChatInput"] textarea { background: #fff !important; }
[data-testid="stChatInputTextArea"] { font-size: 15.5px !important; }
[data-testid="stChatInputSubmitButton"] { background: var(--kohl) !important; border-radius: 50% !important; color: #fff !important; }

@media (prefers-reduced-motion: reduce) {
  .rail .st.active i, .caret::after { animation: none; }
}
"""
