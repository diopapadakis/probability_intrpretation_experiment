# experiment_code.py  – full consent text + instructions + WeChat-ID check
import streamlit as st
import streamlit.components.v1 as components
import datetime, random, uuid, textwrap, gspread
from google.oauth2.service_account import Credentials

# ─────────────────── Credentials guard ──────────────────────────────────
if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
    st.error("Missing [connections.gsheets] block in secrets.toml")
    st.stop()

# ───────────────── Experiment configuration ─────────────────────────────
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

# ────────────────── Google-Sheets helpers ───────────────────────────────
HEADER = (
    ["participant_id", "timestamp", "wechat_id",
     "consent_confidentiality", "consent_future_use"]
    + [f"q{q}_stage1" for q in QIDS]
    + [f"q{q}_pred"   for q in QIDS]
    + [f"q{q}_band"   for q in QIDS]
    + [f"q{q}_low"    for q in QIDS]
    + [f"q{q}_high"   for q in QIDS]
)

def _ws():
    cfg = dict(st.secrets["connections"]["gsheets"])
    ss_id, ws_name = cfg.pop("spreadsheet_id"), cfg.pop("worksheet")
    cfg["private_key"] = cfg["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(
        cfg,
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds).open_by_key(ss_id).worksheet(ws_name)

def _ensure_header(ws):
    if ws.row_values(1) != HEADER:
        if ws.row_values(1):
            ws.insert_row(HEADER, 1)
        else:
            ws.update("A1", [HEADER])

def _save(data: dict):
    ws = _ws()
    _ensure_header(ws)
    ws.append_row([data.get(c, "") for c in HEADER],
                  value_input_option="USER_ENTERED", table_range="A1")

# ──────────────── Session-state initialisation ──────────────────────────
def _init():
    st.session_state.stage = -1                  # -1 consent, 0 instr., 1 …
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
    _init()

# ───────────────────────  Text blocks  ──────────────────────────────────
CONSENT_MD = textwrap.dedent("""\
### RESEARCH INFORMED CONSENT FORM
**Study Title:** Probability Interpretation Study  
**Investigators:** Maya Wong, Mona Hong, Eli Khaytser and Jiayu Xu  

---

#### Invitation to Be a Part of a Research Study  
You are invited to participate in a research study. This form has information
to help you decide whether or not you wish to participate—please review it
carefully. Your participation is **voluntary**. Please ask any questions you
have before deciding.

---

#### Purpose of the Study  
The purpose of this study is to explore how people use and understand words
that express quantitative uncertainty, such as “likely” or “unlikely.”
Specifically, we want to measure individual differences in interpretation,
whether people realize others may interpret the same words differently, and
whether such mismatches predict systematic miscommunication.

---

#### Eligibility to Participate  
* 18 years of age or older  
* Fluent in English  
* NYU Shanghai student  

We will confirm these points before the study begins.

---

#### Description of Study Procedures  
1. **Stage 1 – Survey**: You will see sentences with qualitative probability
   terms and use a slider (0–100) to assign a numerical probability.  
2. **Stage 2 – Wavelength Game**: You will guess the *median* interpretation
   of other participants for the same sentences and choose a **narrow** or
   **wide** band around your guess:  
   • Narrow ±3 → 14 RMB if correct • Wide ±6 → 7 RMB if correct  
3. Five of the 15 sentences are randomly selected for payment. All
   participants receive a 10 RMB show-up fee.

---

#### Risks or Discomforts  
There are no anticipated risks or discomforts.

---

#### Benefits  
While you may not benefit directly, the study may improve communication
strategies in fields where conveying uncertainty is crucial.

---

#### Compensation  
* 10 RMB completion fee  
* Up to 14 RMB (narrow) or 7 RMB (wide) per correct answer in Stage 2  
Total earnings depend on your choices and performance.

---

#### Voluntary Participation  
Participation is voluntary. You may withdraw at any time; data collected
to that point will be retained.

---

#### Privacy & Data Confidentiality  
Your data will be kept confidential by the research team.

---

""")  # end CONSENT_MD

INSTR_MD = textwrap.dedent("""\
### Instructions for Participants

Welcome to this study in experimental economics, conducted by the
**Shanghai Behavioral and Experimental Economics Lab** at **NYU Shanghai**.
The session lasts **20–30 minutes**.

---

#### Rules  
* Read quietly, no talking.  
* Electronic devices off and stored.  
* Raise your hand for questions.

---

### Payment  
* **Completion fee:** 10 RMB  
* **Bonus:** Earn more in Stage 2 based on performance.  
* Payment via WeChat transfer (preferred) or in-person within 14 days.

---

### Session Structure  

| Stage | What you do |
|-------|-------------|
| **1 – Interpretation** | For each of **15** sentences, use a 0–100 slider to state the probability you associate with the sentence. |
| **2 – Wavelength Game** | For the same sentences, guess the **median** of others’ answers, then pick a band:<br>• **Narrow ±3** → 20 points (14 RMB) if correct<br>• **Wide ±6** → 10 points (7 RMB) if correct |

Only **5** rounds are randomly chosen for payment.

---

#### Example Earnings  
If you get 3 narrow and 2 wide hits:  
`(3×20)+(2×10)=80 points → 80×0.7 RMB = 56 RMB`  
Plus 10 RMB fee → **66 RMB total**.

---

### Comprehension Check  

1. To earn points in Stage 2, your interval must contain:  
   ☐ your Stage-1 answer ☑ **the median of other participants’ answers** ☐ the experimenter’s answer  

2. Your payment equals:  
   ☐ 10 RMB + (points from *all* rounds)  
   ☑ **10 RMB + (points from 5 random rounds)**  
   ☐ 20 points per correct narrow band

Once you understand the rules, enter your WeChat ID below to begin Stage 1.
""")

# ──────────────────────  Callbacks  ─────────────────────────────────────
def consent_next():
    if not st.session_state.get("conf_agree", False):
        st.warning("Please tick the confidentiality box to proceed.")
        return
    fut = st.session_state.get("fut_choice", "")
    if fut == "":
        st.warning("Please choose an option for future use of data.")
        return
    st.session_state.data["consent_confidentiality"] = True
    st.session_state.data["consent_future_use"] = fut
    st.session_state.stage = 0                    # show instructions next

def begin_stage1():
    st.session_state.data["wechat_id"] = st.session_state["wechat_id"]
    st.session_state.stage = 1

def next_to_stage2():
    st.session_state.stage = 2
    st.session_state._scroll_to_top = False

def submit_all():
    st.session_state.data["wechat_id"] = st.session_state["wechat_id"]
    _save(st.session_state.data)
    st.session_state.stage = 3

# ───────────────────────────  UI flow  ──────────────────────────────────
if st.session_state.stage == -1:
    st.markdown(CONSENT_MD)

    # integrated confidentiality checkbox
    st.checkbox(
        "I understand that my participation will remain confidential and that my information will be kept secure.",
        key="conf_agree"
    )

    st.markdown("**Future use of data – choose one option:**")
    fut = st.radio(
        label="",
        options=["no_share", "deidentified", "identifiable"],
        format_func=lambda v: {
            "no_share":     "Use my data **only** for this study",
            "deidentified": "You may share **de-identified** data",
            "identifiable": "You may share **identifiable** data"
        }[v],
        key="fut_choice"
    )

    st.button("Continue →", on_click=consent_next)

elif st.session_state.stage == 0:
    st.markdown(INSTR_MD)
    st.text_input("WeChat ID (required for payment):", key="wechat_id")
    st.button("Begin Stage 1 →", on_click=begin_stage1,
              disabled=st.session_state.get("wechat_id", "") == "")

elif st.session_state.stage == 1:
    st.header("Stage 1 – Your Interpretation")
    for qid, sentence in st.session_state.qlist:
        st.write(sentence)
        key = f"q{qid}_stage1"
        st.session_state.data[key] = st.slider(
            "", 0, 100, value=st.session_state.stage1_def[qid], key=key
        )
    st.button("Continue to Stage 2 →", on_click=next_to_stage2)

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
        band_choice = st.radio(
            "Band width:", (f"Narrow ±{NARROW_R}", f"Wide ±{WIDE_R}"), key=bk
        )
        band = "narrow" if band_choice.startswith("Narrow") else "wide"
        st.session_state.data[bk] = band

        half = NARROW_R if band == "narrow" else WIDE_R
        low, high = max(0, pred - half), min(100, pred + half)
        st.session_state.data[f"q{qid}_low"]  = low
        st.session_state.data[f"q{qid}_high"] = high
        st.slider("Selected interval:", 0, 100, value=(low, high),
                  disabled=True, key=f"view_{qid}")

    st.button("Submit all responses", on_click=submit_all)

else:
    st.success(f"Thank you! You will receive **{BASE_FEE} RMB** plus any bonus from Stage 2.")
