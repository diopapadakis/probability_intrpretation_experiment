import streamlit as st
import pandas as pd
import uuid
import datetime
import os
import random

# ========== Configuration ==========
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
NUM_QUESTIONS = 15
QIDS = list(range(1, NUM_QUESTIONS + 1))
NARROW_RANGE = 3
WIDE_RANGE = 6

# Payment parameters
BASE_FEE_RMB = 10
NARROW_BAND_POINTS = 20
WIDE_BAND_POINTS = 10
POINT_TO_RMB = 0.7

DATA_DIR = "data"
RANDOMIZE_ORDER = True   # Set False for fixed order

os.makedirs(DATA_DIR, exist_ok=True)

# ========== Helpers ==========
def save_responses(responses: dict):
    """Save and reorder CSV columns by universal question ID."""
    df = pd.DataFrame([responses])
    cols = ["participant_id", "timestamp", "wechat_id"]
    cols += [f"q{qid}_stage1" for qid in QIDS]
    cols += [f"q{qid}_pred" for qid in QIDS]
    cols += [f"q{qid}_bend" for qid in QIDS]
    cols += [f"q{qid}_low" for qid in QIDS]
    cols += [f"q{qid}_high" for qid in QIDS]
    df = df[cols]
    path = os.path.join(DATA_DIR, "responses.csv")
    df.to_csv(path, mode="a", index=False, header=not os.path.exists(path))


def start_stage1():
    st.session_state.responses["wechat_id"] = st.session_state.wechat_id
    st.session_state.stage = 1


def go_to_stage2():
    st.session_state.stage = 2


def go_to_final():
    save_responses(st.session_state.responses)
    st.session_state.stage = 3

# ========== Initialize Session State ==========
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.stage = 0
    st.session_state.participant_id = str(uuid.uuid4())
    st.session_state.responses = {
        "participant_id": st.session_state.participant_id,
        "timestamp": datetime.datetime.now().isoformat()
    }
    st.session_state.sliders_visible = False

    # Build a list of (qid, sentence) and shuffle it per user
    st.session_state.question_list = [(qid, SENTENCES[qid - 1]) for qid in QIDS]
    if RANDOMIZE_ORDER:
        random.shuffle(st.session_state.question_list)

    # Pick a random default for each question, separately for each stage
    st.session_state.stage1_defaults = {qid: random.randint(0, 100) for qid in QIDS}
    st.session_state.stage2_defaults = {qid: random.randint(0, 100) for qid in QIDS}

# ========== Stage 0: Instructions & WeChat ID ==========
def run_instructions():
    st.markdown("""
**Welcome to this study in experimental economics, conducted by the Shanghai Behavioral and Experimental Economics Lab.**

This investigation examines how people interpret probabilistic information in decision-making contexts. The study is funded by **NYU Shanghai** through resources dedicated to research. The session will take approximately **20–30 minutes**. Please read these instructions carefully, as your payment depends on your decisions during the experiment.

Please read these instructions quietly to yourself. Refrain from talking or communicating with other participants during the session. Electronic devices must be turned off and stored away. If you have questions, raise your hand and wait for an experimenter to approach you – do not speak aloud.

**Payment**
- You will receive a **10 RMB completion fee** for participating.
- Through careful decision-making, you can earn additional rewards based on your performance.
- All payments require a signed receipt and will be processed within 14 days after the conclusion of the study.

**Session Structure**
The experiment consists of two stages, each with 15 questions. Total payment = 10 RMB + (points × 0.7 RMB) from 5 randomly selected Stage 2 rounds.

Once everyone is ready, please enter your WeChat ID for remote payment or leave blank for in-person collection.
    """, unsafe_allow_html=True)

    st.text_input("WeChat ID (for payment):", key="wechat_id")
    st.button("Begin Stage 1 →", on_click=start_stage1)

# ========== Stage 1: Personal Estimates ==========
def run_stage1():
    st.header("Stage 1: Interpreting probability words")
    st.write(f"You will see {NUM_QUESTIONS} sentences. Move each slider (0–100) to indicate your numerical interpretation.")

    if not st.session_state.sliders_visible:
        st.button("Start Questions", on_click=lambda: st.session_state.update({"sliders_visible": True}))
        return

    for qid, sentence in st.session_state.question_list:
        key = f"q{qid}_stage1"
        st.write(sentence)
        val = st.slider(
            label="",
            min_value=0,
            max_value=100,
            value=st.session_state.stage1_defaults[qid],
            key=key
        )
        st.session_state.responses[key] = val

    st.button("Next: Wavelength Game →", on_click=go_to_stage2)

# ========== Stage 2: The Wavelength Game ==========
def run_stage2():
    st.header("Stage 2: The Wavelength Game")
    st.write(f"For each of the {NUM_QUESTIONS} sentences, guess the median from Stage 1 and select an interval.")

    for qid, sentence in st.session_state.question_list:
        st.write(sentence)

        pred_key = f"q{qid}_pred"
        bend_key = f"q{qid}_bend"

        pred = st.slider(
            "Your prediction of the median (0–100):",
            min_value=0,
            max_value=100,
            value=st.session_state.stage2_defaults[qid],
            key=pred_key
        )
        st.session_state.responses[pred_key] = pred

        bend = st.radio(
            "Choose band width:",
            [f"Narrow (±{NARROW_RANGE}, reward {NARROW_BAND_POINTS * POINT_TO_RMB:.0f} RMB)",
             f"Wide   (±{WIDE_RANGE}, reward {WIDE_BAND_POINTS * POINT_TO_RMB:.0f} RMB)"],
            key=bend_key
        )
        band_type = "narrow" if "Narrow" in bend else "wide"
        st.session_state.responses[bend_key] = band_type

        size = NARROW_RANGE if band_type == "narrow" else WIDE_RANGE
        low, high = max(0, pred - size), min(100, pred + size)

        st.write(f"Interval: **[{low}, {high}]** (±{size})")
        st.slider(
            label="",
            min_value=0,
            max_value=100,
            value=(low, high),
            disabled=True,
            key=f"q{qid}_interval"
        )
        st.session_state.responses[f"q{qid}_low"] = low
        st.session_state.responses[f"q{qid}_high"] = high

    st.button("Submit Responses", on_click=go_to_final)

# ========== Stage 3: Thank You ==========
def run_final():
    st.header("Thank you for participating!")
    st.write(
        f"You will receive a base fee of {BASE_FEE_RMB} RMB plus any additional earnings from 5 randomly selected Stage 2 rounds."
    )

# ========== Router ==========
if st.session_state.stage == 0:
    run_instructions()
elif st.session_state.stage == 1:
    run_stage1()
elif st.session_state.stage == 2:
    run_stage2()
else:
    run_final()
