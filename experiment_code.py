#Issues now: WeChat ID is not actually recorded (it is blank on the google sheets file).
#You have to scroll up in parts 2 and 4 (instructions and second set of questions)
#TO DO: ask for confirmation before proceeding.
#TO DO: check if they moved the slider or not.
import streamlit as st, streamlit.components.v1 as components
import datetime, random, uuid, textwrap, gspread
from google.oauth2.service_account import Credentials

# ── Credentials guard ────────────────────────────────────────────
if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
    st.error("Missing [connections.gsheets] block in secrets.toml")
    st.stop()

# ── Experiment configuration ────────────────────────────────────
SENTENCES =[
    "Certain",
    "Definitely happen",
    "Expected",
    "Highly probable",
    "Very likely",
    "A pretty good chance",
    "Likely",
    "A fair chance",
    "Frequently",
    "An even chance",
    "Could happen",
    "Might happen",
    "Uncertain",
    "Infrequently",
    "Unlikely",
    "Very unlikely",
    "A remote chance",
    "Improbable",
    "Impossible",
    "Never happen"
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
     "consent_confidentiality", "consent_future_use",
     "comp_q1", "comp_q2"]                     # comprehension answers
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
    st.session_state.want_stage2_confirm  = False   # ask before leaving Stage 1
    st.session_state.want_submit_confirm  = False   # ask before final submit
    st.session_state.stage = -1            # -1 consent, 0 instructions+check, 1…
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
    st.session_state["wechat_id"] = ""
if "stage" not in st.session_state:
    _init()

# ── Text blocks (verbatim) ───────────────────────────────────────
CONSENT_MD = textwrap.dedent("""\
# Research Informed Consent Form

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
## Access to Your Study Information

We will not give you access to the information collected about you in this study.

---

## Contact Information

If you have questions at any time, please contact:  
- **Maya Wong** at mw5737@nyu.edu  
- **Faculty Sponsor, Eric Set** at ericset@nyu.edu  
---
""")

INSTR_MD = textwrap.dedent("""\
# Instructions for Participants

Welcome to this study in experimental economics, conducted by the **Shanghai Behavioral and Experimental Economics Lab**. This investigation examines how people interpret probabilistic information in decision-making contexts. The study is funded by **NYU Shanghai** through resources dedicated to research. The session will take approximately **20–30 minutes**. Please read these instructions carefully, as your payment depends on your decisions during the experiment.

Please read these instructions quietly to yourself. Refrain from talking or communicating with other participants during the session. Electronic devices must be turned off and stored away. If you have questions, raise your hand and wait for an experimenter to approach you—do not speak aloud.

---

## Payment

You will receive a **10 RMB completion fee** for participating. Through careful decision-making, you can earn additional rewards based on your performance. All payments require a signed receipt and will be processed within 14 days after the conclusion of the study. Details on payment are below.

---

## Session Structure

The experiment consists of a series of individual decisions presented in two stages. These stages and their relation to your total payment are detailed below.

### Stage 1: Interpreting Probability Words

You will see a series of sentences, each containing a single qualitative probability term (for example, “likely,” “unlikely,” or “very few people”). For each sentence:

- A slider labeled **0–100** will appear below the sentence.  
- Move the slider to indicate the numerical probability (in percent) that you associate with that sentence.  
- Once you are happy with your answer, click **Next** to submit and proceed.

You will answer 15 such questions.

### Stage 2: The Wavelength Game

In this stage, you will guess how others in Stage 1 interpreted each term and choose one of two interval widths (“bands”):

1. We display the same sentence again.  
2. Use the slider to indicate your **best guess** of the median answer given by all participants in Stage 1.  
3. Choose one of two interval widths:  
   - **Narrow band** (±3 points):  
     - If the true median lies inside your interval, you earn **14 RMB**.  
     - If it lies outside, you earn **0 RMB**.  
   - **Wide band** (±6 points):  
     - If the true median lies inside your interval, you earn **7 RMB**.  
     - If it lies outside, you earn **0 RMB**.  
4. Click **Next** to proceed.

You will play the Wavelength Game on the same 15 sentences from Stage 1.

---

## Earnings and Payment

- **Completion Fee:** 10 RMB  
- **Stage 2 Payoff:**  
  - **5 rounds** will be randomly selected for payment.  
  - For each selected round:  
    - If your chosen interval contains the true median of at least 11 other participants, you earn points (see below).  
- **Point Rewards:**  
  - Narrow band: 20 points per correct response  
  - Wide band:   10 points per correct response  
- **Exchange Rate:** 1 point = 0.7 RMB  
- **Total Payment:** Base fee + (Total points from selected rounds × 0.7 RMB)

### Example Calculation

- Suppose you succeed in 3 rounds with narrow bands and 2 with wide bands:  
  - Points earned: (3 × 20) + (2 × 10) = 80 points  
  - Converted to RMB: 80 × 0.7 = 56 RMB  
  - Base fee: 10 RMB  
  - **Total:** 66 RMB  

---

## Payment Procedure

- **Receipt Requirement:** All payments require signing a receipt.  
- **Payment Methods:**  
  - **WeChat Transfer** (preferred): Provide your WeChat ID for remote payment.  
  - **In-Person Collection:** If no WeChat ID is provided, you must return to the lab to receive payment and sign the receipt.  
- **Payment Timeline:** All payments will be processed within **[X] days** after the experiment concludes.

---

## Important Reminders

- Aim for accuracy in both stages—precision and calibration matter!  
- There are no “right” or “wrong” answers in Stage 1; we want your personal interpretations.  
- In Stage 2, a wider band lowers your reward but increases your chance of earning it.  
- If you have any questions, raise your hand at any time.

Once everyone is ready, we will begin **Stage 1**.

---  
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
    if not st.session_state.get("wechat_id", "").strip():
        st.warning("Please enter your WeChat ID to proceed.")
        return
    st.session_state.data["consent_confidentiality"] = True
    st.session_state.data["consent_future_use"] = fut
    st.session_state.data["wechat_id"] = st.session_state.get("wechat_id", "")
    st.session_state.stage = 0                   # show instructions + comprehension

def begin_stage1():
    # require comprehension answers
    if st.session_state.get("comp_q1") == "" or st.session_state.get("comp_q2") == "":
        st.warning("Please answer both comprehension questions to continue.")
        return
    st.session_state.data["comp_q1"] = st.session_state["comp_q1"]
    st.session_state.data["comp_q2"] = st.session_state["comp_q2"]
    st.session_state.stage = 1

def next_to_stage2():
    st.session_state.stage = 2
    st.session_state._scroll_to_top = False

def submit_all():
    _save(st.session_state.data)
    st.session_state.stage = 3

# ── UI routing ──────────────────────────────────────────────────
if st.session_state.stage == -1:
    st.markdown(CONSENT_MD)
    st.checkbox("I understand that my participation in this study will remain confidential but my information is going to be kept in the study", key="conf_agree")

    fut = st.radio(
        "We may wish to use information about you collected for this study for future research, share it with other researchers, or place it in a data repository. These studies may be similar to this study or completely different. We will not ask for your additional permission before sharing this information. Please indicate below your permissions regarding this use of your information:",
        ["no_share", "deidentified", "identifiable"],
        format_func=lambda x: {
            "no_share": "I do not give permission to use my data for future research or to share it with other researchers. Use it only for this research study.",
            "deidentified": "I give permission to use my de-identified data for future research, share it with other researchers, or place it in a data repository. Remove all information that could identify me before sharing or using the data.",
            "identifiable": "I give permission to use my identifiable data for future research, share it with other researchers, or place it in a data repository. I understand that this information may be used to identify me personally."
        }[x],
        key="fut_choice")

    st.text_input(
        "WeChat ID (required for payment via WeChat transfer):",
        key="wechat_id")
    st.button("Continue →", on_click=consent_next)

elif st.session_state.stage == 0:
    components.html("<script>window.scrollTo(0,0);</script>", height=0)
    st.markdown(INSTR_MD)
    st.markdown("### Comprehension Check")
    st.radio(
        "1 · To earn points for an item in Stage 2, your chosen interval must contain…",
        ["your Stage 1 answer", "the **median** of other participants’ answers", "the experimenter’s suggested answer"],
        key="comp_q1")
    st.radio(
        "2 · Your total payment equals…",
        ["10 RMB + (Total Points × 0.7 RMB) from all rounds",
         "10 RMB + (Total Points × 0.7 RMB) from **5 randomly selected** rounds",
         "20 points per correct narrow band answer"],
        key="comp_q2")

    st.button("Begin Stage 1 →", on_click=begin_stage1)

elif st.session_state.stage == 1:
    components.html("<script>window.scrollTo(0,0);</script>", height=0)
    st.header("Stage 1 – Your Interpretation\n Assign a probability (0-100%) to each phrase:")
    for q, sentence in st.session_state.qlist:
        st.write(sentence)
        key = f"q{q}_stage1"
        st.session_state.data[key] = st.slider("",
            0, 100, value=st.session_state.stage1_def[q], key=key)
        # 2-step confirmation: first set a flag …
    if st.button("Continue to Stage 2 →"):
        st.session_state.want_stage2_confirm = True

    # … then, if flag is on, show a modal
    if st.session_state.want_stage2_confirm:
        with st.dialog("Confirm and proceed to Stage 2"):
            st.markdown(
                "You will **not** be able to return to Stage 1 once you continue. "
                "Are you sure you want to proceed?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, proceed"):
                    st.session_state.stage = 2      # advance
                    st.session_state.want_stage2_confirm = False
            with col2:
                if st.button("No, stay here"):
                    st.session_state.want_stage2_confirm = False


elif st.session_state.stage == 2:
    components.html("<script>window.scrollTo(0,0);</script>", height=0)

    st.header("Stage 2 – Predict the Group Median\n For each statement, try to guess the median answer of other particiants:")
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
