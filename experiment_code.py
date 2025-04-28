"""
Streamlit app · Probability-Word Interpretation + “Wavelength” Game
------------------------------------------------------------------
• Data are appended to:
    1) A local CSV (“data/responses.csv”) with a guaranteed header.
    2) (Optionally) A Google Sheet via gspread if secrets are provided.
• Four numeric stages: 0–intro, 1–stage1, 2–stage2, 3–thanks.
• Stage-2 auto-scrolls to top exactly once.
• Buttons respond on first click via on_click callbacks.
• Question numbers are hidden from participants.
"""

import streamlit as st
import pandas as pd
import datetime
import random
import uuid
import os

# ───────────────────────── CONFIG ─────────────────────────────────────────
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

# ────────────────── LOCAL CSV HELPER ─────────────────────────────────────
CSV_PATH = "data/responses.csv"

def _ensure_local_csv_header(cols):
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if not os.path.exists(CSV_PATH):
        pd.DataFrame(columns=cols).to_csv(CSV_PATH, index=False)

def _append_to_local_csv(data, cols):
    _ensure_local_csv_header(cols)
    row = {c: data.get(c, "") for c in cols}
    pd.DataFrame([row]).to_csv(CSV_PATH, mode="a", header=False, index=False)

# ──────────────────── OPTIONAL G-SHEETS HELPER ───────────────────────────
# Requires `gspread` and `google-auth` in requirements and `[connections.gsheets]` in secrets.toml
def _append_to_gsheet(data, cols):
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        cfg = st.secrets["connections"]["gsheets"]
        info = {k: v.replace("\\n","\n") if k=="private_key" else v for k,v in cfg.items()}
        ss_id = info.pop("spreadsheet_id"); ws_name = info.pop("worksheet")
        creds = Credentials.from_service_account_info(info, scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ])
        client = gspread.authorize(creds)
        ws = client.open_by_key(ss_id).worksheet(ws_name)
        # ensure header row correct
        if ws.row_count==0 or ws.row_values(1)!=cols:
            if ws.row_count: ws.delete_rows(1)
            ws.insert_row(cols, index=1)
        # append
        row = [data.get(c,"") for c in cols]
        ws.append_row(row, value_input_option="USER_ENTERED")
    except Exception as e:
        st.warning(f"⚠️ Could not write to Google Sheet: {e}")

# ─────────────────── SESSION-STATE INIT ─────────────────────────────────
if "stage" not in st.session_state:
    st.session_state.stage = 0
    st.session_state.pid   = str(uuid.uuid4())
    st.session_state.data  = {
        "participant_id": st.session_state.pid,
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
                                 .isoformat(timespec="seconds")
    }
    qlist = list(zip(QIDS, SENTENCES))
    if RAND_ORDER: random.shuffle(qlist)
    st.session_state.qlist = qlist
    st.session_state.def1  = {q: random.randint(0,100) for q in QIDS}
    st.session_state.def2  = {q: random.randint(0,100) for q in QIDS}

# ─────────────────── BUTTON HELPER ────────────────────────────────────────
def _set_stage(s: int):
    st.session_state.stage = s

# ─────────────────── UI SCREENS ─────────────────────────────────────────
def screen_intro():
    st.markdown("""
        ### Probability-Word Interpretation Study  
        **NYU Shanghai · Behavioral & Experimental Economics Lab**

        Duration ≈ 20–30 min | Payment = 10 RMB + bonus from Stage 2  
        Enter your WeChat ID (blank for cash) then click **Begin**.
    """)
    st.text_input("WeChat ID", key="wechat_id")
    st.button("Begin Stage 1 →", key="btn_intro", on_click=_set_stage, args=(1,))

def screen_stage1():
    st.header("Stage 1 – Your own interpretation (0–100)")
    for qid, sentence in st.session_state.qlist:
        key = f"q{qid}_stage1"
        st.session_state.data[key] = st.slider(
            sentence, 0, 100, value=st.session_state.def1[qid], key=key
        )
    st.button("Continue to Stage 2 →", key="btn_s1", on_click=_set_stage, args=(2,))

def screen_stage2():
    # auto-scroll once
    if st.session_state.pop("_first_scroll", True):
        st.components.v1.html("<script>window.scrollTo(0,0);</script>", height=0)

    st.header("Stage 2 – Predict the group median")
    st.write(
        f"**Narrow** ±{NARROW_R}: {NARROW_PTS*PTS2RMB:.0f} RMB | "
        f"**Wide** ±{WIDE_R}: {WIDE_PTS*PTS2RMB:.0f} RMB"
    )

    for qid, sentence in st.session_state.qlist:
        st.subheader(sentence)  # no Qn.
        pred_key = f"q{qid}_pred"
        band_key = f"q{qid}_band"

        pred = st.slider("Predict the median (0–100)",
                         0, 100, value=st.session_state.def2[qid], key=pred_key)
        st.session_state.data[pred_key] = pred

        choice = st.radio(
            "Choose band width",
            (f"Narrow (±{NARROW_R}) — {NARROW_PTS*PTS2RMB:.0f} RMB",
             f"Wide   (±{WIDE_R}) — {WIDE_PTS*PTS2RMB:.0f} RMB"),
            key=band_key
        )
        band = "narrow" if choice.startswith("Narrow") else "wide"
        st.session_state.data[band_key] = band

        half = NARROW_R if band=="narrow" else WIDE_R
        low, high = max(0, pred-half), min(100, pred+half)
        st.session_state.data[f"q{qid}_low"]  = low
        st.session_state.data[f"q{qid}_high"] = high

        st.slider("Selected interval", 0, 100, (low, high),
                  disabled=True, key=f"view_{qid}")

    if st.button("Submit all responses", key="btn_submit"):
        st.session_state.data["wechat_id"] = st.session_state.get("wechat_id","")
        cols = (
            ["participant_id","timestamp","wechat_id"] +
            [f"q{q}_stage1" for q in QIDS] +
            [f"q{q}_pred"   for q in QIDS] +
            [f"q{q}_band"   for q in QIDS] +
            [f"q{q}_low"    for q in QIDS] +
            [f"q{q}_high"   for q in QIDS]
        )
        # append locally
        _append_to_local_csv(st.session_state.data, cols)
        # append to sheet if configured
        _append_to_gsheet(st.session_state.data, cols)
        _set_stage(3)

def screen_thanks():
    st.success(
        f"Thank you for participating!\n\n"
        f"You will receive **{BASE_FEE_RMB} RMB** + bonus from five random Stage 2 rounds."
    )

# ─────────────────── Router ─────────────────────────────────────────────
{
    0: screen_intro,
    1: screen_stage1,
    2: screen_stage2
}.get(st.session_state.stage, screen_thanks)()
