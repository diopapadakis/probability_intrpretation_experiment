"""
Streamlit app · Probability-Word Interpretation + “Wavelength” Game
------------------------------------------------------------------
• Data appended to a local CSV (“data/responses.csv”) with a guaranteed header.
• Four numeric stages: 0=intro, 1=stage1, 2=stage2, 3=thanks.
• Stage-2 auto-scrolls to top exactly once.
• Buttons respond on first click via on_click callbacks.
• Question numbers hidden from participants.
"""

import streamlit as st
import pandas as pd
import datetime
import random
import uuid
import os

# ───────────────────────────── CONFIG ────────────────────────────────────
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
NUM_Q        = len(SENTENCES)
QIDS         = list(range(1, NUM_Q + 1))
NARROW_R     = 3
WIDE_R       = 6
NARROW_PTS   = 20
WIDE_PTS     = 10
PTS2RMB      = 0.7
BASE_FEE_RMB = 10
RAND_ORDER   = True

DATA_DIR     = "data"
CSV_NAME     = "responses.csv"

# ─────────────────── LOCAL CSV HELPERS ──────────────────────────────────
def _ensure_header(cols: list[str]):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, CSV_NAME)
    if not os.path.exists(path):
        pd.DataFrame(columns=cols).to_csv(path, index=False)

def _append_to_csv(data: dict[str, str|int], cols: list[str]):
    path = os.path.join(DATA_DIR, CSV_NAME)
    _ensure_header(cols)
    row = {c: data.get(c, "") for c in cols}
    pd.DataFrame([row]).to_csv(path, mode="a", header=False, index=False)

# ───────────────── SESSION-STATE INITIALIZATION ─────────────────────────
if "initialized" not in st.session_state:
    st.session_state.initialized       = True
    st.session_state.stage             = 0
    st.session_state.pid               = str(uuid.uuid4())
    st.session_state.data              = {
        "participant_id": st.session_state.pid,
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
                             .isoformat(timespec="seconds"),
    }
    # build & shuffle question list
    qlist = list(zip(QIDS, SENTENCES))
    if RAND_ORDER:
        random.shuffle(qlist)
    st.session_state.qlist = qlist

    # random defaults for sliders
    st.session_state.def1 = {q: random.randint(0, 100) for q in QIDS}
    st.session_state.def2 = {q: random.randint(0, 100) for q in QIDS}

    # flag for auto-scroll in Stage 2
    st.session_state.first_scroll = True

# ───────────────── BUTTON CALLBACKS ─────────────────────────────────────
def go_to_stage1():
    st.session_state.stage = 1

def go_to_stage2():
    st.session_state.stage = 2
    st.session_state.first_scroll = True

def submit_all():
    # record WeChat ID
    st.session_state.data["wechat_id"] = st.session_state.get("wechat_id", "")
    # define columns
    cols = (
        ["participant_id", "timestamp", "wechat_id"]
        + [f"q{q}_stage1" for q in QIDS]
        + [f"q{q}_pred"   for q in QIDS]
        + [f"q{q}_band"   for q in QIDS]
        + [f"q{q}_low"    for q in QIDS]
        + [f"q{q}_high"   for q in QIDS]
    )
    _append_to_csv(st.session_state.data, cols)
    st.session_state.stage = 3

# ───────────────────────── UI SCREENS ───────────────────────────────────
def screen_intro():
    st.markdown("""
    ### Probability-Word Interpretation Study  
    **NYU Shanghai · Behavioral & Experimental Economics Lab**

    Duration ≈ 20–30 min | Payment = 10 RMB + bonus from Stage 2

    Enter your WeChat ID (leave blank for cash) then click **Begin**.
    """)
    st.text_input("WeChat ID", key="wechat_id")
    st.button("Begin Stage 1 →", key="btn_intro", on_click=go_to_stage1)

def screen_stage1():
    st.header("Stage 1 – Your own interpretation (0–100)")
    for qid, sentence in st.session_state.qlist:
        key = f"q{qid}_stage1"
        st.session_state.data[key] = st.slider(
            sentence, 0, 100, value=st.session_state.def1[qid], key=key
        )
    st.button("Continue to Stage 2 →", key="btn_s1", on_click=go_to_stage2)

def screen_stage2():
    # auto-scroll once
    if st.session_state.first_scroll:
        st.components.v1.html("<script>window.scrollTo(0,0);</script>", height=0)
        st.session_state.first_scroll = False

    st.header("Stage 2 – Predict the group median")
    st.write(
        f"**Narrow** ±{NARROW_R}: {NARROW_PTS*PTS2RMB:.0f} RMB | "
        f"**Wide** ±{WIDE_R}: {WIDE_PTS*PTS2RMB:.0f} RMB"
    )

    for qid, sentence in st.session_state.qlist:
        st.subheader(sentence)  # no "Qn."
        pred_key = f"q{qid}_pred"
        band_key = f"q{qid}_band"

        st.session_state.data[pred_key] = st.slider(
            "Predict the median (0–100)",
            0, 100,
            value=st.session_state.def2[qid],
            key=pred_key
        )

        choice = st.radio(
            "Choose band width",
            (
                f"Narrow (±{NARROW_R}) — {NARROW_PTS*PTS2RMB:.0f} RMB",
                f"Wide   (±{WIDE_R}) — {WIDE_PTS*PTS2RMB:.0f} RMB",
            ),
            key=band_key
        )
        band = "narrow" if choice.startswith("Narrow") else "wide"
        st.session_state.data[band_key] = band

        half = NARROW_R if band == "narrow" else WIDE_R
        low, high = max(0, st.session_state.data[pred_key] - half), min(100, st.session_state.data[pred_key] + half)
        st.session_state.data[f"q{qid}_low"]  = low
        st.session_state.data[f"q{qid}_high"] = high

        st.slider(
            "Selected interval",
            0, 100,
            (low, high),
            disabled=True,
            key=f"view_{qid}"
        )

    st.button("Submit all responses", key="btn_submit", on_click=submit_all)

def screen_thanks():
    st.success(
        f"Thank you for participating!\n\n"
        f"You will receive **{BASE_FEE_RMB} RMB** + bonus from five random Stage 2 rounds."
    )

# ─────────────────────────── ROUTER ─────────────────────────────────────
{
    0: screen_intro,
    1: screen_stage1,
    2: screen_stage2
}.get(st.session_state.stage, screen_thanks)()
