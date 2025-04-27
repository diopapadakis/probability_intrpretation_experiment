"""
Probability-Word Interpretation  ·  Stage router 0-1-2-3
Data saved to Google Sheets via Streamlit ≥ 1.25 (st.experimental_connection)
---------------------------------------------------------------------------
1  requirements.txt must include at least:
       streamlit>=1.25     gspread     pandas
2  .streamlit/secrets.toml needs the credentials block shown earlier.
"""

from __future__ import annotations
import datetime as dt, random, uuid, sys, importlib
import pandas as pd
import streamlit as st

# ─────────────────────────── config constants ────────────────────────────
SENTENCES = [
    # … 15 sentences exactly as before …
]
NUM_Q        = len(SENTENCES)
QIDS         = list(range(1, NUM_Q + 1))
NARROW_R, WIDE_R = 3, 6
NARROW_PTS, WIDE_PTS = 20, 10
PTS2RMB      = 0.7
BASE_FEE_RMB = 10
RAND_ORDER   = True

# ─────────────────────────── gsheets helpers ─────────────────────────────
def _append_row(row: pd.DataFrame) -> None:
    conn = st.experimental_connection("gsheets", type="gspread")
    conn.append(
        row,
        worksheet=st.secrets["connections"]["gsheets"]["worksheet"],
        include_index=False,
    )

def _save(resp: dict[str, str | int]) -> None:
    cols = (
        ["participant_id", "timestamp", "wechat_id"]
        + [f"q{q}_stage1" for q in QIDS]
        + [f"q{q}_pred"   for q in QIDS]
        + [f"q{q}_band"   for q in QIDS]
        + [f"q{q}_low"    for q in QIDS]
        + [f"q{q}_high"   for q in QIDS]
    )
    _append_row(pd.DataFrame([{c: resp.get(c, "") for c in cols}]))

# ─────────────────────────── session init ───────────────────────────────
if "stage" not in st.session_state:
    st.session_state.stage  = 0          # 0-1-2-3 scheme
    st.session_state.pid    = str(uuid.uuid4())
    st.session_state.data   = {
        "participant_id": st.session_state.pid,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }
    qlist = list(zip(QIDS, SENTENCES))
    if RAND_ORDER:
        random.shuffle(qlist)
    st.session_state.qlist  = qlist
    st.session_state.def1   = {q: random.randrange(0, 101) for q in QIDS}
    st.session_state.def2   = {q: random.randrange(0, 101) for q in QIDS}
    st.session_state._scroll = False

# ─────────────────────────── stages / screens ───────────────────────────
def run_instructions() -> None:
    st.markdown("""
    ### Welcome  
    Duration ≈ 20 min | Payment = 10 RMB + bonus  
    Please enter your **WeChat ID** (leave blank for cash) and click *Begin*.
    """)
    st.text_input("WeChat ID:", key="wechat_id")
    if st.button("Begin Stage 1 →"):
        st.session_state.stage = 1

def run_stage1() -> None:
    st.header("Stage 1 – Your own interpretation (0-100)")
    for qid, sent in st.session_state.qlist:
        key = f"q{qid}_stage1"
        st.session_state.data[key] = st.slider(
            sent, 0, 100, st.session_state.def1[qid], key=key
        )
    if st.button("Continue to Stage 2 →"):
        st.session_state.stage = 2
        st.session_state._scroll = False

def run_stage2() -> None:
    if not st.session_state._scroll:
        st.components.v1.html("<script>window.scrollTo(0,0);</script>", height=0)
        st.session_state._scroll = True

    st.header("Stage 2 – Predict the group median")
    st.write(
        f"**Narrow** ±{NARROW_R} → {NARROW_PTS*PTS2RMB:.0f} RMB  |  "
        f"**Wide** ±{WIDE_R} → {WIDE_PTS*PTS2RMB:.0f} RMB"
    )

    for qid, sent in st.session_state.qlist:
        st.subheader(f"Q{qid}. {sent}")

        pk, bk = f"q{qid}_pred", f"q{qid}_band"
        pred = st.slider(
            "Predict the median (0-100)",
            0, 100, st.session_state.def2[qid], key=pk
        )
        st.session_state.data[pk] = pred

        choice = st.radio(
            "Choose band width",
            (
                f"Narrow (±{NARROW_R}) — {NARROW_PTS*PTS2RMB:.0f} RMB",
                f"Wide   (±{WIDE_R}) — {WIDE_PTS*PTS2RMB:.0f} RMB",
            ),
            key=bk
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
        st.session_state.stage = 3

def run_final() -> None:
    st.success(f"Thank you!  You will receive {BASE_FEE_RMB} RMB + bonus.")

# ───────────────────────── router (0-1-2-3) ─────────────────────────────
if st.session_state.stage == 0:
    run_instructions()
elif st.session_state.stage == 1:
    run_stage1()
elif st.session_state.stage == 2:
    run_stage2()
else:
    run_final()
