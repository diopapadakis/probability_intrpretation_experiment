"""
Probability-word Interpretation + “Wavelength” Game
Data → Google Sheet   ·   Streamlit ≤≥ any version
"""

from __future__ import annotations
import datetime as _dt, random, uuid, importlib

import pandas as pd
import streamlit as st

# ── Streamlit-connection polyfill ───────────────────────────────────────
if importlib.util.find_spec("streamlit.runtime.connections"):
    from streamlit.runtime.connections import connect as _st_connect      # ≥ 1.30
elif hasattr(st, "experimental_connection"):
    _st_connect = st.experimental_connection                               # 1.25 – 1.29
else:  # ← Streamlit < 1.25 — tell the maintainer exactly what to do
    st.error(
        "⚠️  This app needs Streamlit ≥ 1.25.\n"
        "Add `streamlit>=1.30` to requirements.txt or upgrade the image."
    )
    st.stop()

# ── Config ──────────────────────────────────────────────────────────────
SENTENCES = [
    # … 15 sentences exactly as before …
]
NUM_Q     = len(SENTENCES)
QIDS      = list(range(1, NUM_Q + 1))

NARROW_R, WIDE_R     = 3, 6
NARROW_PTS, WIDE_PTS = 20, 10
PTS2RMB              = 0.7
BASE_FEE             = 10   # RMB
RAND_ORDER           = True

# ── Google-Sheets helpers ───────────────────────────────────────────────
def _append_row_to_gsheet(row_df: pd.DataFrame) -> None:
    conn = _st_connect("gsheets", type="gspread")
    conn.append(
        row_df,
        worksheet=st.secrets["connections"]["gsheets"]["worksheet"],
        include_index=False,
    )

def _save(responses: dict[str, str | int]) -> None:
    cols = (
        ["participant_id", "timestamp", "wechat_id"]
        + [f"q{q}_stage1" for q in QIDS]
        + [f"q{q}_pred"   for q in QIDS]
        + [f"q{q}_band"   for q in QIDS]
        + [f"q{q}_low"    for q in QIDS]
        + [f"q{q}_high"   for q in QIDS]
    )
    _append_row_to_gsheet(pd.DataFrame([{c: responses.get(c, "") for c in cols}]))

# ── Cookie migration (numeric → named stage) ────────────────────────────
_old2new = {0: "INTRO", 1: "STAGE1", 2: "STAGE2", 3: "THANKS"}
if isinstance(st.session_state.get("stage"), int):
    st.session_state.stage = _old2new.get(st.session_state.stage, "INTRO")

# ── First-time session init ─────────────────────────────────────────────
def _init() -> None:
    st.session_state.stage = "INTRO"
    st.session_state.pid   = str(uuid.uuid4())
    st.session_state.data  = {
        "participant_id": st.session_state.pid,
        "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    }
    qlist = list(zip(QIDS, SENTENCES))
    if RAND_ORDER:
        random.shuffle(qlist)
    st.session_state.qlist = qlist
    st.session_state.def1  = {q: random.randrange(0, 101) for q in QIDS}
    st.session_state.def2  = {q: random.randrange(0, 101) for q in QIDS}

if "stage" not in st.session_state:
    _init()

# ── UI screens ──────────────────────────────────────────────────────────
def _intro() -> None:
    st.markdown("""
    ### Welcome
    Duration ≈ 20–30 min | Payment = 10 RMB + bonus  
    Enter your **WeChat ID** and click *Begin*.
    """)
    st.text_input("WeChat ID:", key="wechat_id")
    if st.button("Begin Stage 1 →"):
        st.session_state.stage = "STAGE1"

def _stage1() -> None:
    st.header("Stage 1 – Your own interpretation (0–100)")
    for qid, sent in st.session_state.qlist:
        key = f"q{qid}_stage1"
        st.session_state.data[key] = st.slider(
            sent, 0, 100, st.session_state.def1[qid], key=key
        )
    if st.button("Continue to Stage 2 →"):
        st.session_state.stage = "STAGE2"
        st.session_state._scroll     = False   # reset for auto-scroll

def _stage2() -> None:
    if not st.session_state.get("_scroll"):
        st.components.v1.html("<script>window.scrollTo(0,0);</script>", height=0)
        st.session_state._scroll = True

    st.header("Stage 2 – Predict the group median")
    st.write(
        f"**Narrow** ±{NARROW_R} → {NARROW_PTS*PTS2RMB:.0f} RMB &nbsp;&nbsp;|&nbsp;&nbsp;"
        f"**Wide** ±{WIDE_R} → {WIDE_PTS*PTS2RMB:.0f} RMB"
    )

    for qid, sent in st.session_state.qlist:
        st.subheader(f"Q{qid}. {sent}")

        pk, bk = f"q{qid}_pred", f"q{qid}_band"
        pred = st.slider("Predict the median (0–100)",
                         0, 100, st.session_state.def2[qid], key=pk)
        st.session_state.data[pk] = pred

        choice = st.radio(
            "Choose band width",
            (
                f"Narrow (±{NARROW_R}) — {NARROW_PTS*PTS2RMB:.0f} RMB",
                f"Wide   (±{WIDE_R}) — {WIDE_PTS*PTS2RMB:.0f} RMB",
            ),
            key=bk,
        )
        band = "narrow" if choice.startswith("Narrow") else "wide"
        st.session_state.data[bk] = band

        half = NARROW_R if band == "narrow" else WIDE_R
        low, high = max(0, pred - half), min(100, pred + half)
        st.session_state.data[f"q{qid}_low"]  = low
        st.session_state.data[f"q{qid}_high"] = high

        st.slider("Selected interval", 0, 100, (low, high),
                  disabled=True, key=f"view_{qid}")

    if st.button("Submit all responses"):
        st.session_state.data["wechat_id"] = st.session_state.get("wechat_id", "")
        _save(st.session_state.data)
        st.session_state.stage = "THANKS"

def _thanks() -> None:
    st.success(f"Thank you!  You will receive {BASE_FEE} RMB + bonus.")

# ── Router ───────────────────────────────────────────────────────────────
_router = {"INTRO": _intro, "STAGE1": _stage1, "STAGE2": _stage2, "THANKS": _thanks}
st.session_state.stage = _router.get(st.session_state.stage, _intro).__name__.upper()
_router[st.session_state.stage]()
