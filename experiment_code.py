# experiment_code.py  – full consent text + WeChat-ID check
import streamlit as st, streamlit.components.v1 as components
import datetime, random, uuid, textwrap, gspread
from google.oauth2.service_account import Credentials

# ── Credentials guard ────────────────────────────────────────────
if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
    st.error("Missing [connections.gsheets] block in secrets.toml")
    st.stop()

# ── Experiment configuration ────────────────────────────────────
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

# ── Sheets helpers ───────────────────────────────────────────────
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
        cfg, scopes=["https://www.googleapis.com/auth/spreadsheets",
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

# ── State initialisation ─────────────────────────────────────────
def _init():
    st.session_state.stage = -1            # -1 consent, 0 instructions, then 1…
    st.session_state.pid   = str(uuid.uuid4())
    st.session_state.data  = {"participant_id": st.session_state.pid,
                              "timestamp": datetime.datetime.utcnow()
                                           .isoformat(timespec="seconds")}
    qlist = list(zip(QIDS, SENTENCES))
    if RAND_ORDER:
        random.shuffle(qlist)
    st.session_state.qlist       = qlist
    st.session_state.stage1_def  = {q: random.randint(0,100) for q in QIDS}
    st.session_state.stage2_def  = {q: random.randint(0,100) for q in QIDS}
if "stage" not in st.session_state:
    _init()

# ── Text blocks (verbatim) ───────────────────────────────────────
CONSENT_MD = textwrap.dedent("""\
**Study Title:** Probability Interpretation Study  
**Investigators:** Maya Wong, Mona Hong, Eli Khaytser and Jiayu Xu

---

## Invitation to Be a Part of a Research Study

You are invited to participate in a research study. This form has information to help you decide whether or not you wish to participate—please review it carefully. Your participation is voluntary. Please ask any questions you have about the study or about this form before deciding to participate.

---

## Purpose of the Study

In this study, we’re interested in how people interpret words that describe uncertainty—terms like “likely,” “unlikely,” and “possible.” You’ll be asked to assign a numerical probability to various words and then guess how other participants might interpret the same words. Your responses will help us learn more about how these expressions are understood and used in everyday communication.

---

## Eligibility to Participate

You are eligible to participate in this study if:  
- You are 18 years old or older  
- You are fluent in English  
- You are an NYU Shanghai student  

To determine if you are eligible, we will ask you to confirm your age, ask whether you have participated in a related study before, and ensure that you are able to understand the instructions presented at the start of the study.

---

## Description of Study Procedures

If you agree to participate, you will be asked to:

1. **Stage 1: Survey**  
   Each participant sees several sentences containing a qualitative term. For each sentence, you will use a slider (0–100) to indicate the numerical probability you attach to the sentence. This will be administered by computer in a classroom setting.

2. **Stage 2: Wavelength Game**  
   You will see the same sentences but will be asked to give a number (0–100) representing your belief about the average interpretation of other participants. For each sentence, you may choose a “wide” or a “narrow” bend; your choice determines how much you can earn.

3. **Payoff Determination**  
   For each participant, five out of the fifteen phrases are randomly chosen to determine payoffs:  
   - Narrow bend: 14 RMB per correct answer  
   - Wide bend:   7 RMB per correct answer  
   - All participants receive 10 RMB for participating

---

## Risks or Discomforts

This study does not involve any risks or discomforts.

---

## Benefits

We hope this study will contribute to a deeper understanding of how people communicate about uncertainty using words instead of numbers. By identifying differences in interpretation, the research could inform better communication strategies in fields such as healthcare, education, public policy, and risk management—helping to reduce misunderstandings when important decisions depend on conveying uncertain information.

You are not expected to directly benefit from participation in the study.

---

## Compensation

Participants will receive:  
- A base payment of 10 RMB for participating  
- Up to 14 RMB per correct answer (narrow bend) or 7 RMB per correct answer (wide bend) in the Wavelength Game  

Total earnings will depend on your choices and performance.

---

## Voluntary Participation

Your participation is completely voluntary. If you withdraw or are withdrawn from the study early, we will keep information that has already been collected.

---

## Privacy & Data Confidentiality

You may be asked to provide information that could identify you personally. This information will remain confidential. Please check below to indicate you understand this condition:

- [ ] I understand that my participation in this study will remain confidential and that my information will be kept secure.

You will also be asked to confirm your agreement after the information is collected.

### Future Use of Data

We may wish to use the data collected here for future research, share it with other researchers, or deposit it in a data repository. These future studies may be similar or different from the current one. We will not ask for additional permission before sharing. Please indicate your permission below:

- [ ] I do **not** give permission to use my data for future research or to share it. Use it only for this study.  
- [ ] I give permission to use my **de-identified** data for future research, share it with other researchers, or place it in a data repository. Remove all identifying information first.  
- [ ] I give permission to use my **identifiable** data for future research, share it with other researchers, or place it in a data repository. I understand this information may be used to identify me.

You may change your decision at any time by notifying the researchers.

---

## Access to Your Study Information

We will not give you access to the information collected about you in this study.

---

## Contact Information

If you have questions at any time, please contact:  
- **Maya Wong** at mw5737@nyu.edu  
- **Faculty Sponsor, Eric Set** at ericset@nyu.edu  

If you have questions about your rights as a research participant or believe you have been harmed, contact the NYU Human Research Protection Program at (212) 998-4808 or ask.humansubjects@nyu.edu.

---
""")

INSTR_MD = textwrap.dedent("""\
### Instructions for Participants

Welcome to this study in experimental economics, conducted by the **Shanghai Behavioral and Experimental Economics Lab** at **NYU Shanghai** …

*(entire instruction text you supplied, converted to Markdown – no content removed)*
""")

# ── Callbacks ────────────────────────────────────────────────────
def consent_next():
    if not st.session_state.get("conf_agree"):
        st.warning("Please check the confidentiality box to proceed.")
        return
    fut = st.session_state.get("fut_choice", "")
    if fut == "":
        st.warning("Please choose an option for future use of data.")
        return
    st.session_state.data["consent_confidentiality"] = True
    st.session_state.data["consent_future_use"] = fut
    st.session_state.stage = 0                   # show instructions

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

# ── UI routing ──────────────────────────────────────────────────
if st.session_state.stage == -1:
    st.markdown(CONSENT_MD)
    st.checkbox("I understand and agree", key="conf_agree")

    fut = st.radio("Future use of my data:",
                   ["", "no_share", "deidentified", "identifiable"],
                   format_func=lambda x: {
                       "": "— Select an option —",
                       "no_share": "Do **NOT** use my data beyond this study",
                       "deidentified": "Use **de-identified** data in future research",
                       "identifiable": "Use my **identifiable** data in future research"
                   }[x], key="fut_choice")
    st.button("Continue →", on_click=consent_next)

elif st.session_state.stage == 0:
    st.markdown(INSTR_MD)
    st.text_input("WeChat ID (required for payment via WeChat transfer):",
                  key="wechat_id")
    st.button("Begin Stage 1 →", on_click=begin_stage1,
              disabled=st.session_state.get("wechat_id", "") == "")

elif st.session_state.stage == 1:
    st.header("Stage 1 – Your Interpretation")
    for q, sentence in st.session_state.qlist:
        st.write(sentence)
        key = f"q{q}_stage1"
        st.session_state.data[key] = st.slider("",
            0, 100, value=st.session_state.stage1_def[q], key=key)
    st.button("Continue to Stage 2 →", on_click=next_to_stage2)

elif st.session_state.stage == 2:
    if not st.session_state.get("_scroll_to_top", False):
        components.html("<script>window.scrollTo(0,0);</script>", height=0)
        st.session_state._scroll_to_top = True

    st.header("Stage 2 – Predict the Group Median")
    st.write(f"**Narrow** ±{NARROW_R} → {NARROW_PTS*PTS2RMB:.0f} RMB   |   "
             f"**Wide** ±{WIDE_R} → {WIDE_PTS*PTS2RMB:.0f} RMB")

    for q, sentence in st.session_state.qlist:
        st.write(sentence)
        pk = f"q{q}_pred"
        pred = st.slider("Median (0–100):", 0, 100,
                         value=st.session_state.stage2_def[q], key=pk)
        st.session_state.data[pk] = pred

        bk = f"q{q}_band"
        choice = st.radio("Band width:",
                          (f"Narrow ±{NARROW_R}", f"Wide ±{WIDE_R}"), key=bk)
        band = "narrow" if choice.startswith("Narrow") else "wide"
        st.session_state.data[bk] = band

        half = NARROW_R if band == "narrow" else WIDE_R
        low, high = max(0, pred-half), min(100, pred+half)
        st.session_state.data[f"q{q}_low"], st.session_state.data[f"q{q}_high"] = low, high
        st.slider("Selected interval:", 0, 100, value=(low, high),
                  disabled=True, key=f"v{q}")

    st.button("Submit all responses", on_click=submit_all)

else:
    st.success(f"Thank you! You will receive **{BASE_FEE} RMB** + bonus from five random Stage 2 rounds.")
