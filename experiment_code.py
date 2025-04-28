# experiment_code.py  – consent + instructions version
import streamlit as st
import streamlit.components.v1 as components
import datetime, random, uuid, textwrap
import gspread
from google.oauth2.service_account import Credentials

# ── Guard for credentials ────────────────────────────────────────────────
if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
    st.error("Missing Google Sheets credentials in secrets.toml under [connections.gsheets].")
    st.stop()

# ── Experimental configuration ──────────────────────────────────────────
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
BASE_FEE   = 10
RAND_ORDER = True

# ── Google-Sheets helpers ────────────────────────────────────────────────
HEADER = (
    ["participant_id", "timestamp", "wechat_id",
     "consent_confidentiality", "consent_future_use"]
    + [f"q{q}_stage1" for q in QIDS]
    + [f"q{q}_pred"   for q in QIDS]
    + [f"q{q}_band"   for q in QIDS]
    + [f"q{q}_low"    for q in QIDS]
    + [f"q{q}_high"   for q in QIDS]
)

def _gsheet():
    cfg = dict(st.secrets["connections"]["gsheets"])
    ss_id, ws_name = cfg.pop("spreadsheet_id"), cfg.pop("worksheet")
    if "private_key" in cfg:
        cfg["private_key"] = cfg["private_key"].replace("\\n", "\n")
    client = gspread.authorize(
        Credentials.from_service_account_info(
            cfg,
            scopes=["https://www.googleapis.com/auth/spreadsheets",
                    "https://www.googleapis.com/auth/drive"]))
    return client.open_by_key(ss_id).worksheet(ws_name)

def _ensure_header(ws):
    if ws.row_values(1) != HEADER:
        if ws.row_values(1):
            ws.insert_row(HEADER, 1)
        else:
            ws.update("A1", [HEADER])

def _save_responses(data: dict):
    ws = _gsheet()
    _ensure_header(ws)
    ws.append_row([data.get(c, "") for c in HEADER],
                  value_input_option="USER_ENTERED",
                  table_range="A1")

# ── Session-state initialisation ────────────────────────────────────────
def _init_state():
    st.session_state.stage = -1              # -1 = consent
    st.session_state.pid   = str(uuid.uuid4())
    st.session_state.data  = {
        "participant_id": st.session_state.pid,
        "timestamp": datetime.datetime.utcnow().isoformat(timespec="seconds")
    }
    qlist = list(zip(QIDS, SENTENCES))
    if RAND_ORDER:
        random.shuffle(qlist)
    st.session_state.qlist       = qlist
    st.session_state.stage1_def  = {q: random.randint(0,100) for q in QIDS}
    st.session_state.stage2_def  = {q: random.randint(0,100) for q in QIDS}

if "stage" not in st.session_state:
    _init_state()

# ── Consent page callbacks ──────────────────────────────────────────────
def consent_continue():
    if not st.session_state.get("consent_conf"):
        st.warning("You must check the confidentiality box to proceed.")
        return
    fut = st.session_state.get("consent_future", "")
    if fut == "":
        st.warning("Please choose one option about future data use.")
        return
    st.session_state.data["consent_confidentiality"] = True
    st.session_state.data["consent_future_use"]      = fut
    st.session_state.stage = 0                      # show instructions next

def begin_stage1():
    st.session_state.data["wechat_id"] = st.session_state.get("wechat_id", "")
    st.session_state.stage = 1

def continue_to_stage2():
    st.session_state.stage = 2
    st.session_state._scroll_to_top = False

def submit_all():
    st.session_state.data["wechat_id"] = st.session_state.get("wechat_id", "")
    _save_responses(st.session_state.data)
    st.session_state.stage = 3

# ── Instruction markdown (converted from LaTeX) ─────────────────────────
INSTR_MD = textwrap.dedent("""\
### Welcome

Welcome to this study in experimental economics, conducted by the **Shanghai Behavioral & Experimental Economics Lab** at **NYU Shanghai**.  
The session will last **20–30 minutes**.

---

#### Rules
* Please read quietly.  
* No talking; electronic devices off.  
* Raise your hand for questions.

---

### Payment

* **Completion fee:** 10 RMB  
* **Bonus:** Earn additional money in Stage 2 depending on your performance (details below).  
* You will sign a receipt and receive payment within 14 days (via WeChat transfer or in-person).

---

### Session Structure

| Stage | What you do |
|-------|-------------|
| **1 – Interpretation** | For each of 15 sentences, move a 0–100 slider to show the probability you associate with the sentence. |
| **2 – “Wavelength Game”** | For the same sentences, guess the **median** of other participants’ answers, then choose a band: <br>  • **Narrow ±3** → 20 points (14 RMB) if correct <br>  • **Wide ±6** → 10 points (7 RMB) if correct |

Only **5 of the 15 rounds** in Stage 2 are randomly selected for payment.

---

#### Example Earnings

If 3 narrow guesses and 2 wide guesses are correct:  
`(3×20)+(2×10)=80 points → 80×0.7 RMB = 56 RMB`  
Add the 10 RMB fee → **66 RMB total**.

---

### Comprehension Check

1. **Stage 2 success** means your interval must contain:  
   ☐ Your Stage-1 answer ☑ The **median** of others’ answers ☐ The experimenter’s answer  

2. Your total payment equals:  
   ☐ 10 RMB + points from *all* rounds ☑ 10 RMB + points from **5 random rounds** ☐ 20 points per correct narrow band

When you are ready, enter your WeChat ID below and click **“Begin Stage 1”**.
""")

# ── UI routing ──────────────────────────────────────────────────────────
if st.session_state.stage == -1:
    st.header("Research Informed Consent Form")
    st.markdown("**Study Title:** Probability Interpretation Study  \n"
                "**Investigators:** Maya Wong · Mona Hong · Eli Khaytser · Jiayu Xu  \n"
                "Please read the information below and indicate your choices before proceeding.")

    st.markdown("**Confidentiality**  
    Your participation is confidential, but study staff will keep the data.  \n"
                "☑ I understand that my participation will remain confidential but my information will be kept in the study.",
                unsafe_allow_html=True)
    st.checkbox("I understand and agree", key="consent_conf")

    st.markdown("**Future Use of Data**")
    fut_choice = st.radio(
        "Choose one option:",
        [
            "Do **not** use my data for future research or sharing (no_share)",
            "You may use **de-identified** data for future research (deidentified)",
            "You may use my **identifiable** data for future research (identifiable)"
        ],
        key="future_use_display")
    fut_map = {
        "Do **not** use my data for future research or sharing (no_share)": "no_share",
        "You may use **de-identified** data for future research (deidentified)": "deidentified",
        "You may use my **identifiable** data for future research (identifiable)": "identifiable"
    }
    st.session_state["consent_future"] = fut_map.get(fut_choice, "")

    st.button("I Agree →", on_click=consent_continue)

elif st.session_state.stage == 0:
    st.markdown(INSTR_MD)
    st.text_input("WeChat ID (for payment):", key="wechat_id")
    st.button("Begin Stage 1 →", on_click=begin_stage1)

elif st.session_state.stage == 1:
    st.header("Stage 1 – Your Interpretation")
    for qid, sentence in st.session_state.qlist:
        st.write(sentence)
        key = f"q{qid}_stage1"
        st.session_state.data[key] = st.slider(
            "", 0, 100, value=st.session_state.stage1_def[qid], key=key)
    st.button("Continue to Stage 2 →", on_click=continue_to_stage2)

elif st.session_state.stage == 2:
    if not st.session_state.get("_scroll_to_top", False):
        components.html("<script>window.scrollTo(0,0);</script>", height=0)
        st.session_state._scroll_to_top = True

    st.header("Stage 2 – Predict the Group Median")
    st.write(f"**Narrow** ±{NARROW_R} → {NARROW_PTS*PTS2RMB:.0f} RMB   |   "
             f"**Wide** ±{WIDE_R} → {WIDE_PTS*PTS2RMB:.0f} RMB")

    for qid, sentence in st.session_state.qlist:
        st.write(sentence)
        pk = f"q{qid}_pred"
        pred = st.slider("Median (0–100):", 0, 100,
                         value=st.session_state.stage2_def[qid], key=pk)
        st.session_state.data[pk] = pred

        bk = f"q{qid}_band"
        choice = st.radio("Band width:",
                          (f"Narrow ±{NARROW_R}", f"Wide ±{WIDE_R}"),
                          key=bk)
        band = "narrow" if choice.startswith("Narrow") else "wide"
        st.session_state.data[bk] = band

        half = NARROW_R if band == "narrow" else WIDE_R
        low, high = max(0, pred-half), min(100, pred+half)
        st.session_state.data[f"q{qid}_low"]  = low
        st.session_state.data[f"q{qid}_high"] = high
        st.slider("Selected interval:", 0, 100, value=(low, high),
                  disabled=True, key=f"view_{qid}")

    st.button("Submit all responses", on_click=submit_all)

else:
    st.success(f"Thank you! You will receive **{BASE_FEE} RMB** + bonus from five random Stage 2 rounds.")
