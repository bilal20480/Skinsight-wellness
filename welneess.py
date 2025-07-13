# Skin Wellness Planner — Praise Style

import streamlit as st
import google.generativeai as genai
import base64
import os
import re
from io import BytesIO
from xhtml2pdf import pisa
import markdown2

# --- Background Image Loader ---
def get_base64_image():
    for ext in ["webp", "jpg", "jpeg", "png"]:
        path = f"well.{ext}"
        if os.path.exists(path):
            with open(path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode()
    return None

bg_img = get_base64_image()

# --- Page Setup ---
st.set_page_config(page_title="Skin Wellness Planner", layout="centered")

if bg_img:
    st.markdown(f"""
        <style>
        .stApp {{
            background-image: url("data:image;base64,{bg_img}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}
        .block-container {{
            background-color: rgba(255, 255, 255, 0.7);
            padding: 2rem 3rem;
            border-radius: 18px;
            margin-top: 2rem;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: #333333;
            font-family: 'Segoe UI', sans-serif;
        }}
        </style>
    """, unsafe_allow_html=True)

# --- App Title ---
st.title("🧴 Skin Wellness Planner")

# --- API Key (hardcoded for local use only) ---
api_key=st.secrets["bilal_api"]

# Configure Gemini API key
genai.configure(api_key=api_key)

# --- State Init ---
if "step" not in st.session_state:
    st.session_state.step = 0
if "name" not in st.session_state:
    st.session_state.name = ""
if "answers" not in st.session_state:
    st.session_state.answers = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "planner_generated" not in st.session_state:
    st.session_state.planner_generated = False

# --- Replay chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Chat functions ---
def chat_bot(message):
    with st.chat_message("assistant"):
        st.markdown(message)
    st.session_state.messages.append({"role": "assistant", "content": message})

def user_message(message):
    with st.chat_message("user"):
        st.markdown(message)
    st.session_state.messages.append({"role": "user", "content": message})

# --- Skin Questions ---
questions = [
    "What is your skin type (e.g., oily, dry, combination, sensitive, normal)?",
    "Do you have any specific concerns (acne, dark spots, eczema, etc.)?",
    "What’s your current skincare routine like?",
    "How often do you drink water daily?",
    "Do you use sunscreen regularly?",
    "Any allergies to skincare products?",
]

# --- First Greeting ---
if st.session_state.step == 0:
    chat_bot("👋 Hey there! I'm your skin wellness buddy. Let's create a soothing plan for your skin.")
    chat_bot("First, what’s your name?")
    st.session_state.step = 1

# --- User Input Field ---
user_input = st.chat_input("Type your answer...")

# --- Main Logic ---
if user_input:
    user_message(user_input)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Step 1: Get Name
    if st.session_state.step == 1:
        name_match = re.search(r"[A-Z][a-z]+", user_input)
        st.session_state.name = name_match.group(0) if name_match else "You"
        chat_bot(f"Nice to meet you, {st.session_state.name}! Let's talk about your skin.")
        chat_bot(questions[0])
        st.session_state.step = 2

    # Step 2 onward: Ask each question and give feedback
    elif st.session_state.step - 2 < len(questions):
        q_index = st.session_state.step - 2
        answer = user_input
        st.session_state.answers.append(answer)

        feedback_prompt = (
            f"You are a kind skin wellness assistant helping someone named {st.session_state.name}.\n"
            f"Q: {questions[q_index]}\nA: {answer}\n"
            f"Give a short, encouraging response (1 sentence)."
        )
        feedback = model.generate_content(feedback_prompt)
        chat_bot(feedback.text.strip())

        next_index = q_index + 1
        if next_index < len(questions):
            chat_bot(questions[next_index])
        st.session_state.step += 1

    # Final Step: Generate planner
    if not st.session_state.planner_generated and st.session_state.step >= len(questions) + 2:
        st.session_state.planner_generated = True

        planner_prompt = (
            f"Create a personalized 7-day skin wellness plan for {st.session_state.name}.\n\n"
        )
        for i, ans in enumerate(st.session_state.answers):
            planner_prompt += f"Q: {questions[i]}\nA: {ans}\n\n"
        planner_prompt += (
            "Make a weekly plan for skin wellness from Monday to Sunday. Use a table with Morning, Afternoon, Evening, Night.\n"
            "Include routines like gentle cleansing, hydration, sunscreen, relaxation, diet reminders, mindfulness.\n"
            "Avoid product names. After the table, write a 3-line emotional encouragement message."
        )

        chat_bot("💆 Generating your custom skin wellness plan...")
        result = model.generate_content(planner_prompt)
        final_plan = result.text.strip()
        # Fix broken markdown tables if needed
        if final_plan.startswith("") and final_plan.endswith(""):
            final_plan = final_plan.strip("```").strip()

        # Display properly rendered Markdown
        chat_bot("")  # empty to separate from loading message
        with st.chat_message("assistant"):
            st.markdown(final_plan, unsafe_allow_html=True)

        chat_bot(final_plan)

        def convert_md_to_pdf(md_text):
            html = f"<html><body>{markdown2.markdown(md_text)}</body></html>"
            output = BytesIO()
            pisa.CreatePDF(html, dest=output)
            output.seek(0)
            return output

        st.download_button(
            label="📄 Download Skin Plan as PDF",
            data=convert_md_to_pdf(final_plan),
            file_name=f"{st.session_state.name}_Skin_Plan.pdf",
            mime="application/pdf"
        )
