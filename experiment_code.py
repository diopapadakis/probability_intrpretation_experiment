"""
Streamlit app: Probability‐Word Interpretation + “Wavelength” game
-----------------------------------------------------------------

► Data are *not* written to the container’s file-system (which is
  ephemeral on Streamlit Cloud).  
► Instead each submission is appended to a Google Sheet via
  `st.experimental_connection("gsheets", type="gspread")`.

That’s all the setup – deploy the app and every participant row will
instantly appear in the sheet.
"""

from __future__ import annotations

import datetime as _dt
import os
import random
import uuid

import pandas as pd
import streamlit as st

# ──────────────────────────────── CONFIG ────────────────────────────────
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
NUM_Q = len(SENTENCES)
QIDS = list(range(1, NUM_Q + 1))

NARROW_RANGE, WIDE_RANGE = 3, 6
BASE_FEE_RMB = 10
NARROW_PTS, WIDE_PTS = 20, 10
PTS_TO_RMB = 0.7

RANDOMIZE_ORDER = True  # change to False during pilot tests

# ──────────────────────────── GOOGLE-SHEET IO ────────────────────────────
def _append_row_to_gsheet(row_df: pd.DataFrame) -> None:
    """Append *one* DataFrame row to the Google Sheet defined in secrets."""
    conn = st.experimental_connection("gsheets", type="gspread")
    # `conn.append` takes a DF and adds it after the current last row
    conn.append(row_df, worksheet=st.secrets["connections"]["gsheets"]["worksheet"], include_index=False)


def _save_responses(responses: dict[str, int | str]) -> None:
    cols = (
        ["participant_id", "timestamp", "wechat_id"]
        + [f"q{qid}_stage1" for qid in QIDS]
        + [f"q{qid}_pred" for qid in QIDS]
        + [f"q{qid}_band" for qid in QIDS]
        + [f"q{qid}_low" for qid in QIDS]
        + [f"q{qid}_high" for qid in QIDS]
    )
    row = pd.DataFrame([{c: responses.get(c, "") for c in cols}])
    _append_row_to_gsheet(row)


# ───────────────────────── SESSION-STATE HELPERS ────────────────────────
def _init_state() -> None:
    st.session_state.stage = "INTRO"
    st.session_state.pid = str(uuid.uuid4())
    st.session_state.responses = {
        "participant_id": st.session_state.pid,
        "timestamp": _dt.datetime.utcnow().isoformat(timespec="seconds"),
    }

    qlist = list(zip(QIDS, SENTENCES))
    if RANDOMIZE_ORDER:
        random.shuffle(qlist)
    st.session_state.qlist = qlist

    st.session_state.stage1_defaults = {qid: random.randrange(0, 101) for qid in QIDS}
    st.session_state.stage2_defaults = {qid: random.randrange(0, 101) for qid in QIDS}


if "stage" not in st.session_state:
    _init_state()

# ──────────────────────────── PAGE ROUTER ───────────────────────────────
def _intro_screen() -> None:
    st.markdown(
        """
        ### Welcome to this study in experimental economics

        **NYU Shanghai — Behavioral & Experimental Economics Lab**

        This session takes **20–30 minutes**.  
        Your payment = **10 RMB show-up fee** + bonus from Stage 2.

        **Please:**
        1. Read quietly; no talking or phone use.  
        2. Raise your hand if you have questions.

        Enter your *WeChat ID* (leave blank if you’ll collect cash in person)
        and click **Begin Stage 1**.
        """
    )
    st.text_input("WeChat ID:", key="wechat_id")
    st.button("Begin Stage 1 →", on_click=lambda: st.session_state.update({"stage": "STAGE1"}))


def _stage1() -> None:
    st.header("Stage 1 – Your own interpretation")
    st.write("For each sentence choose the probability you think it implies (0–100).")

    for qid, sentence in st.session_state.qlist:
        key = f"q{qid}_stage1"
        val = st.slider(
            sentence,
            0,
            100,
            value=st.session_state.stage1_defaults[qid],
            key=key,
        )
        st.session_state.responses[key] = val

    if st.button("Continue to Stage 2 →"):
        st.session_state.stage = "STAGE2"


def _stage2() -> None:
    st.header("Stage 2 – Predict the group median")
    st.write(
        f"For each sentence, guess the **median** answer from Stage 1 and pick an interval.\n"
        f"• *Narrow band* ±{NARROW_RANGE}: {NARROW_PTS*PTS_TO_RMB:.0f} RMB if the median falls inside.\n"
        f"• *Wide band*   ±{WIDE_RANGE}: {WIDE_PTS  *PTS_TO_RMB:.0f} RMB."
    )

    for qid, sentence in st.session_state.qlist:
        pred_key = f"q{qid}_pred"
        band_key = f"q{qid}_band"

        st.subheader(f"Q{qid}. {sentence}")

        pred = st.slider(
            "Your prediction of the median (0–100)",
            0,
            100,
            value=st.session_state.stage2_defaults[qid],
            key=pred_key,
        )
        st.session_state.responses[pred_key] = pred

        band_choice = st.radio(
            "Choose band width",
            (
                f"Narrow (±{NARROW_RANGE}) — {NARROW_PTS*PTS_TO_RMB:.0f} RMB",
                f"Wide   (±{WIDE_RANGE}) — {WIDE_PTS*PTS_TO_RMB:.0f} RMB",
            ),
            index=0,
            key=band_key,
        )
        band = "narrow" if band_choice.startswith("Narrow") else "wide"
        st.session_state.responses[band_key] = band

        half = NARROW_RANGE if band == "narrow" else WIDE_RANGE
        low, high = max(0, pred - half), min(100, pred + half)
        st.session_state.responses[f"q{qid}_low"] = low
        st.session_state.responses[f"q{qid}_high"] = high

        st.markdown(f"**Interval:** `{low} – {high}`")

    if st.button("Submit all responses"):
        st.session_state.responses["wechat_id"] = st.session_state.get("wechat_id", "")
        _save_responses(st.session_state.responses)
        st.session_state.stage = "THANKS"


def _thanks() -> None:
    st.success(
        f"Thank you for participating!\n\n"
        f"You will receive {BASE_FEE_RMB} RMB + bonus from five random Stage-2 rounds.\n"
        f"Payments are processed within 14 days."
    )


_router = {
    "INTRO": _intro_screen,
    "STAGE1": _stage1,
    "STAGE2": _stage2,
    "THANKS": _thanks,
}
_router[st.session_state.stage]()

