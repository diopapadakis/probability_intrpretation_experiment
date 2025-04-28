"""
Streamlit app · Probability-Word Interpretation + “Wavelength” Game
------------------------------------------------------------------
• Data are appended to a Google Sheet (gspread).  
• Numeric routing 0-1-2-3.  
• Header row written once so every column (wechat_id, q1_stage1, …) stays aligned.  
• Question numbers hidden from participants.  
• Stage-2 page always opens scrolled to the top.  
• Buttons react on first click (unique keys).  
• Still migrates any old string-based stage.
"""

import streamlit as st
import pandas as pd
import datetime
import random
import uuid
import gspread
from google.oauth2.service_account import Credentials

# ── migrate old cookie values ───────────────────────────────────────────
_old2num = {"INTRO": 0, "STAGE1": 1, "STAGE2": 2, "THANKS": 3}
if isinstance(st.session_state.get("stage"), str):
    st.session_state.stage = _old2num.get(st.session_state.stage, 0)

# ── CONFIG ──────────────────────────────────────────────────────────────
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
NARROW_R    = 3
WIDE_R      = 6
NARROW_PTS  = 20
WIDE_PTS    = 10
PTS2RMB     = 0.7
BASE_FEE    = 10
RAND_ORDER  = True

# ── Google-Sheets helpers ───────────────────────────────────────────────
def _get_gsheet_client():
    cfg = st.secrets["connections"]["gsheets"]
    info = dict(cfg)                    # mutable copy
    ss_id   = info.pop("spreadsheet_id")
    ws_name = info.pop("worksheet")
    if "private_key" in info:           # convert \n to real newlines
        info["private_key"] = info["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(
        info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds), ss_id, ws_name

def _ensure_header(ws, cols):
    first = ws.row_values(1)
    if not first or first != cols:
        if first:
            ws.delete_rows(1)           # remove wrong header
        ws.insert_row(cols, index=1, value_input_option="RAW")

def _save_responses(data: dict[str, str | int]) -> None:
    cols = (
        ["participant_id", "timestamp", "wechat_id"]
        + [f"q{q}_stage1" for q in QIDS]
        + [f"q{q}_pred"   for q in QIDS]
        + [f"q{q}_band"   for q in QIDS]
        + [f"q{q}_low"    for q in QIDS]
        + [f"q{q}_high"   for q in QIDS]
    )
    row = [data.get(c, "") for c in cols]

    client, ss_id, ws_name = _get_gsheet_client()
    ws = client.open_by_key(ss_id).worksheet(ws_name)
    _ensure_header(ws, cols)
    ws.append_row(row, value_input_option="USER_ENTERED")

# ── Session-state init ──────────────────────────────────────────────────
def _init_state():
    st.session_state.stage = 0
    st.session_state.pid   = str(uuid.uuid4())
    st.session_state.data  = {
        "participant_id": st.session_state.pid,
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
                                 .isoformat(timespec="seconds"),
    }
    qlist = list(zip(QIDS, SENTENCES))
    if RAND_ORDER:
        random.shuffle(qlist)
    st.session_state.qlist = qlist
    st.session_state.def1  = {q: random.randrange(0, 101) for q in QIDS}
    st.session_state.def2  = {q: random.randrange(0, 101) for q in QIDS}

if "stage" not in st.session_state:
    _init_state()

# ── UI screens ──────────────────────────────────────────────────────────
def run_instructions():
    st.markdown("""
    ### Welcome to this study in experimental economics  
    **NYU Shanghai · Behavioral & Experimental Economics Lab**

    Duration: 20–30 min — Payment: 10 RMB show-up + bonus from Stage 2.

    Enter your WeChat ID (leave blank for cash) and click **Begin**.
    """)
    st.text_input("WeChat ID:", key="wechat_id")
    if st.button("Begin Stage 1 →", key="go_stage1"):
        st.session_state.stage = 1

def run_stage1():
    st.header("Stage 1 – Your own interpretation (0-100)")
    for qid, sentence in st.session_state.qlist:
        key = f"q{qid}_stage1"
        val = st.slider(sentence, 0, 100, value=st.session_state.def1[qid], key=key)
        st.session_state.data[key] = val
    if st.button("Continue to Stage 2 →", key="go_stage2"):
        st.session_state.stage = 2
        st.session_state._entered_stage2 = None     # reset scroll flag

def run_stage2():
    if st.session_state.get("_entered_stage2") is None:
        st.components.v1.html("<script>window.scrollTo(0,0);</script>", height=0)
        st.session_state._entered_stage2 = True

    st.header("Stage 2 – Predict the group median")
    st.write(
        f"**Narrow** ±{NARROW_R}: {NARROW_PTS*PTS2RMB:.0f} RMB | "
        f"**Wide** ±{WIDE_R}: {WIDE_PTS*PTS2RMB:.0f} RMB"
    )

    for qid, sentence in st.session_state.qlist:
        st.subheader(sentence)                              # no “Qn.” prefix

        pred_key = f"q{qid}_pred"
        band_key = f"q{qid}_band"

        pred = st.slider(
            "Predict the median (0-100)",
            0, 100, value=st.session_state.def2[qid], key=pred_key
        )
        st.session_state.data[pred_key] = pred

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
        low, high = max(0, pred - half), min(100, pred + half)
        st.session_state.data[f"q{qid}_low"]  = low
        st.session_state.data[f"q{qid}_high"] = high

        st.slider(
            "Selected interval", 0, 100, value=(low, high),
            disabled=True, key=f"view_{qid}"
        )

    if st.button("Submit all responses", key="submit_final"):
        st.session_state.data["wechat_id"] = st.session_state.get("wechat_id", "")
        _save_responses(st.session_state.data)
        st.session_state.stage = 3

def run_final():
    st.success(
        f"Thank you for participating!\n\n"
        f"You will receive {BASE_FEE} RMB + bonus from five random Stage 2 rounds."
    )

# ── Numeric router 0-1-2-3 ──────────────────────────────────────────────
if st.session_state.stage == 0:
    run_instructions()
elif st.session_state.stage == 1:
    run_stage1()
elif st.session_state.stage == 2:
    run_stage2()
else:
    run_final()
