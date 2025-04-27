"""
Streamlit app · Probability-Word Interpretation + “Wavelength” Game
=================================================================

• Session data are stored in a **Google Sheet** (no more ephemeral CSV).  
• Works on *any* Streamlit version ≥ 1.20 (uses the stable `runtime.connections.connect`).  
• Includes migration for visitors who still have the *old numeric* stage in their
  browser cookie, a disabled-slider band preview, and auto-scroll-to-top when Stage 2 loads.
"""

from __future__ import annotations

import datetime as _dt
import random
import uuid

import pandas as pd
import streamlit as st
from streamlit.runtime.connections import connect as _connect   # ← stable alias

# ─────────────────────────── MIGRATE OLD COOKIE ──────────────────────────
_old2new = {0: "INTRO", 1: "STAGE1", 2: "STAGE2", 3: "THANKS"}
if isinstance(st.session_state.get("stage"), int):
    st.session_state.stage = _old2new.get(st.session_state.stage, "INTRO")

# ─────────────────────────────── CONFIG ──────────────────────────────────
SENTENCES = [
    "If someone tells you that there is an even chance of something, what probability would you interpret that as?",
    "If someone tells you that something is certain, what probability would you interpret that as?",
    "If someone tells you that an event is impossible, what probability would you interpret that as?",
    "If someone tells you there is a pretty good chance of something happening, what probability would you interpret that as?",
    "If someone tells you that an event is highly probable, what probability would you interpret that as?",
    "If someone tells you that an event happens infrequently, how likely would you think it is to happen?",
    "If someone tells you that an event happens frequently, how likely would you think it is to happen?",
    "If someone tells you that there is a fighting chance of something happening, what probability would you interpret that as?",
    "If someone tells you an event is very likely, what probability would you interpret that as?",
    "If someone tells you an event is very unlikely, what probability would you interpret that as?",
    "If someone tells you there is a fair chance of an event happening, what probability would you interpret that as?",
    "If someone tells you an event is likely, what probability would you interpret that as?",
    "If someone tells you an event is unlikely, what probability would you interpret that as?",
    "If someone tells you an event is consistent with expectations, how likely would you think it is to happen?",
    "If someone tells you there is a highly suspicious chance of an event happening, what probability would you interpret that as?",
]
NUM_Q       = len(SENTENCES)
QIDS        = list(range(1, NUM_Q + 1))

NARROW_R, WIDE_R = 3, 6
NARROW_PTS, WIDE_PTS = 20, 10
PTS2RMB     = 0.7
BASE_FEE    = 10        # RMB
RAND_ORDER  = True

# ──────────────────────────── G-SHEETS I/O ───────────────────────────────
def _append_row_to_gsheet(row: pd.DataFrame) -> None:
    conn = _connect("gsheets", type="gspread")
    conn.append(
        row,
        worksheet=st.secrets["connections"]["gsheets"]["worksheet"],
        include_index=False,
    )

def _save_responses(resp: dict[str, str | int]) -> None:
    cols = (
        ["participant_id", "timestamp", "wechat_id"]
        + [f"q{q}_stage1" for q in QIDS]
        + [f"q{q}_pred"   for q in QIDS]
        + [f"q{q}_band"   for q in QIDS]
        + [f"q{q}_low"    for q in QIDS]
        + [f"q{q}_high"   for q in QIDS]
    )
    _append_row_to_gsheet(pd.DataFrame([{c: resp.get(c, "") for c in cols}]))

# ──────────────────────────── STATE INIT ─────────────────────────────────
def _init_state() -> None:
    st.session_state.stage  = "INTRO"
    st.session_state.pid    = str(uuid.uuid4())
    st.session_state.data   = {
        "participant_id": st.session_state.pid,
        "timestamp": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    }

    qlist = list(zip(QIDS, SENTENCES))
    if RAND_ORDER:
        random.shuffle(qlist)
    st.session_state.qlist = qlist

    st.session_state.def1 = {q: random.randrange(0, 101) for q in QIDS}
    st.session_state.def2 = {q: random.randrange(0, 101) for q in QIDS}

if "stage" not in st.session_state:
    _init_state()

# ──────────────────────────── UI SCREENS ─────────────────────────────────
def _intro() -> None:
    st.markdown(
        """
        ### Welcome to this study in experimental economics
        **NYU Shanghai · Behavioral & Experimental Economics Lab**

        *Duration* ≈ 20–30 min.  
        *Payment*  = 10 RMB show-up fee + bonus from Stage 2.

        Enter your *WeChat ID* (leave blank for cash) and click **Begin**.
        """
    )
    st.text_input("WeChat ID:", key="wechat_id")
    if st.button("Begin Stage 1 →"):
        st.session_state.stage = "STAGE1"

def _stage1() -> None:
    st.header("Stage 1 – Your own interpretation (0–100)")
    for qid, sentence in st.session_state.qlist:
        key = f"q{qid}_stage1"
        val = st.slider(sentence, 0, 100, value=st.session_state.def1[qid], key=key)
        st.session_state.data[key] = val
    if st.button("Continue to Stage 2 →"):
        st.session_state.stage = "STAGE2"
        st.session_state._scroll_done = False   # reset for auto-scroll

def _stage2() -> None:
    # auto-scroll once at entry
    if not st.session_state.get("_scroll_done"):
        st.components.v1.html("<script>window.scrollTo(0,0);</script>", height=0)
        st.session_state._scroll_done = True

    st.header("Stage 2 – Predict the group median")
    st.write(
        f"**Narrow** ±{NARROW_R}: {NARROW_PTS*PTS2RMB:.0f} RMB   |  "
        f"**Wide** ±{WIDE_R}: {WIDE_PTS*PTS2RMB:.0f} RMB"
    )

    for qid, sentence in st.session_state.qlist:
        st.subheader(f"Q{qid}. {sentence}")

        pred_key = f"q{qid}_pred"
        band_key = f"q{qid}_band"

        pred = st.slider(
            "Predict the median (0–100)",
            0, 100, value=st.session_state.def2[qid], key=pred_key
        )
        st.session_state.data[pred_key] = pred

        choice = st.radio(
            "Choose band width",
            (
                f"Narrow (±{NARROW_R}) — {NARROW_PTS*PTS2RMB:.0f} RMB",
                f"Wide   (±{WIDE_R}) — {WIDE_PTS*PTS2RMB:.0f} RMB",
            ),
            key=band_key,
        )
        band = "narrow" if choice.startswith("Narrow") else "wide"
        st.session_state.data[band_key] = band

        half = NARROW_R if band == "narrow" else WIDE_R
        low, high = max(0, pred - half), min(100, pred + half)
        st.session_state.data[f"q{qid}_low"]  = low
        st.session_state.data[f"q{qid}_high"] = high

        # visual preview of the chosen interval
        st.slider(
            "Selected interval", 0, 100, value=(low, high),
            disabled=True, key=f"view_{qid}"
        )

    if st.button("Submit all responses"):
        st.session_state.data["wechat_id"] = st.session_state.get("wechat_id", "")
        _save_responses(st.session_state.data)
        st.session_state.stage = "THANKS"

def _thanks() -> None:
    st.success(
        f"Thank you for participating!\n\n"
        f"You will receive {BASE_FEE} RMB + bonus from five random Stage-2 rounds."
    )

# ──────────────────────────── ROUTER ─────────────────────────────────────
_router = {
    "INTRO": _intro,
    "STAGE1": _stage1,
    "STAGE2": _stage2,
    "THANKS": _thanks,
}

if st.session_state.stage not in _router:
    st.session_state.stage = "INTRO"

_router[st.session_state.stage]()
