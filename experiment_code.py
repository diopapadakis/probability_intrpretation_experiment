# experiment_code.py

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import datetime
import random
import uuid
import gspread
from google.oauth2.service_account import Credentials

# ── Guard: make sure your secrets are present ─────────────────────────────
if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
    st.error("Missing Google Sheets credentials in secrets.toml under [connections.gsheets].")
    st.stop()

# ── CONFIGURATION ────────────────────────────────────────────────────────
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
    "If someone tells you there is a highly suspicious chance of an event happening, what probability would you interpret that as?"
]
NUM_Q      = len(SENTENCES)
QIDS       = list(range(1, NUM_Q + 1))
NARROW_R   = 3
WIDE_R     = 6
NARROW_PTS = 20
WIDE_PTS   = 10
PTS2RMB    = 0.7
BASE_FEE   = 10  # RMB
RAND_ORDER = True

# ── GOOGLE SHEETS SETUP ──────────────────────────────────────────────────
def _get_gsheet_client():
    cfg = dict(st.secrets["connections"]["gsheets"])
    ss_id   = cfg.pop("spreadsheet_id")
    ws_name = cfg.pop("worksheet")
    # fix newlines if stored as "\n"
    if "private_key" in cfg:
        cfg["private_key"] = cfg["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(
        cfg,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds), ss_id, ws_name

def _save_responses(data: dict[str, str | int]):
    cols = (
        ["participant_id", "timestamp", "wechat_id"]
        + [f"q{q}_stage1" for q in QIDS]
        + [f"q{q}_pred"   for q in QIDS]
        + [f"q{q}_band"   for q in QIDS]
        + [f"q{q}_low"    for q in QIDS]
        + [f"q{q}_high"   for q in QIDS]
    )
    row = [data.get(c, "") for c in cols]
    client, ss_id, ws = _get_gsheet_client()
    sheet = client.open_by_key(ss_id)
    sheet.worksheet(ws).append_row(row, value_input_option="USER_ENTERED")

# ── SESSION-STATE INITIALIZATION ────────────────────────────────────────
def _init_state():
    st.session_state.stage = 0
    st.session_state.pid   = str(uuid.uuid4())
    st.session_state.data  = {
        "participant_id": st.session_state.pid,
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
                              .isoformat(timespec="seconds")
    }
    qlist = list(zip(QIDS, SENTENCES))
    if RAND_ORDER:
        random.shuffle(qlist)
    st.session_state.qlist       = qlist
    st.session_state.stage1_def  = {q: random.randint(0,100) for q in QIDS}
    st.session_state.stage2_def  = {q: random.randint(0,100) for q in QIDS}

if "stage" not in st.session_state:
    _init_state()

# ── CALLBACKS FOR SINGLE-CLICK BUTTONS ─────────────────────────────────
def begin_stage1():
    st.session_state.stage = 1

def continue_to_stage2():
    st.session_state.stage = 2
    st.session_state._scroll_to_top = False

def submit_all():
    st.session_state.data["wechat_id"] = st.session_state.get("wechat_id","")
    _save_responses(st.session_state.data)
    st.session_state.stage = 3

# ── UI / ROUTER ────────────────────────────────────────────────────────
if st.session_state.stage == 0:
    # Instructions
    st.markdown("""
        ### Welcome to this study in experimental economics  
        **NYU Shanghai · Behavioral & Experimental Economics Lab**  

        Duration: 20–30 min  
        Payment: 10 RMB show-up fee + bonus from Stage 2  
    """)
    st.text_input("WeChat ID (for payment):", key="wechat_id")
    st.button("Begin Stage 1 →", on_click=begin_stage1)

elif st.session_state.stage == 1:
    # Stage 1
    st.header("Stage 1 – Your own interpretation")
    for qid, sentence in st.session_state.qlist:
        st.write(sentence)  # no numbering
        key = f"q{qid}_stage1"
        val = st.slider("", 0, 100, value=st.session_state.stage1_def[qid], key=key)
        st.session_state.data[key] = val

    st.button("Continue to Stage 2 →", on_click=continue_to_stage2)

elif st.session_state.stage == 2:
    # Stage 2 (auto-scroll + no numbering)
    if not st.session_state.get("_scroll_to_top", False):
        components.html("<script>window.scrollTo(0,0);</script>", height=0)
        st.session_state._scroll_to_top = True

    st.header("Stage 2 – Predict the group median")
    st.write(
        f"**Narrow** ±{NARROW_R} → {NARROW_PTS*PTS2RMB:.0f} RMB   |   "
        f"**Wide** ±{WIDE_R} → {WIDE_PTS*PTS2RMB:.0f} RMB"
    )

    for qid, sentence in st.session_state.qlist:
        st.write(sentence)
        # prediction slider
        pk = f"q{qid}_pred"
        pred = st.slider("Median (0–100):", 0, 100,
                         value=st.session_state.stage2_def[qid],
                         key=pk)
        st.session_state.data[pk] = pred

        # band choice
        bk = f"q{qid}_band"
        choice = st.radio(
            "Band width:",
            (f"Narrow ±{NARROW_R}", f"Wide ±{WIDE_R}"),
            key=bk
        )
        band = "narrow" if choice.startswith("Narrow") else "wide"
        st.session_state.data[bk] = band

        # compute & preview interval
        half = NARROW_R if band=="narrow" else WIDE_R
        low, high = max(0, pred-half), min(100, pred+half)
        st.session_state.data[f"q{qid}_low"]  = low
        st.session_state.data[f"q{qid}_high"] = high
        st.slider("Selected interval:", 0, 100, value=(low,high), disabled=True,
                  key=f"view_{qid}")

    st.button("Submit all responses", on_click=submit_all)

else:
    # Thank You
    st.success(
        f"Thank you! You will receive **{BASE_FEE} RMB** + bonus from five random Stage 2 rounds."
    )
