import streamlit as st
import google.generativeai as genai
import pandas as pd
import os
from dotenv import load_dotenv

# Load local environment variables (API Key)
load_dotenv()

# Configure Streamlit Page
st.set_page_config(page_title="AI Wealth Advisor", page_icon="📈", layout="wide")
st.title("🏦 AI Wealth Advisor & Portfolio Manager")

# Load the system prompt from the markdown file
@st.cache_data
def load_system_prompt():
    try:
        with open("system_prompt.md", "r") as file:
            return file.read()
    except FileNotFoundError:
        return "You are an expert financial advisor."

SYSTEM_PROMPT = load_system_prompt()

# Initialize Gemini Model
genai.configure(api_key=os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=SYSTEM_PROMPT
)

# Initialize Session State
if "chat_session" not in st.session_state:
    st.session_state.chat_session = model.start_chat(history=[])
if "portfolio_data" not in st.session_state:
    st.session_state.portfolio_data = None
if "previous_report" not in st.session_state:
    st.session_state.previous_report = None

# --- SIDEBAR: Data Ingestion ---
with st.sidebar:
    st.header("📊 Portfolio Data")
    uploaded_csv = st.file_uploader("Upload Current Zerodha Holdings (CSV)", type=['csv'])
    
    if uploaded_csv is not None:
        try:
            df = pd.read_csv(uploaded_csv, skiprows=14) 
            st.session_state.portfolio_data = df
            st.success("Current Portfolio loaded.")
            st.metric("Total Positions", len(df))
        except Exception as e:
            st.error(f"Error parsing CSV: {e}")

    st.header("🕰️ Historical Context")
    uploaded_history = st.file_uploader("Upload Previous Report (Text/Markdown)", type=['txt', 'md'])
    
    if uploaded_history is not None:
        st.session_state.previous_report = uploaded_history.read().decode("utf-8")
        st.success("Historical report loaded for comparison.")
    else:
        st.session_state.previous_report = None

# --- MAIN CHAT INTERFACE ---
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

if prompt := st.chat_input("Ask your wealth advisor a question..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Inject portfolio and historical data into the context
    context = ""
    if st.session_state.portfolio_data is not None:
        context += f"\n\n[System Context: Current portfolio data:\n{st.session_state.portfolio_data.to_string()}]\n"
    
    # Dynamic Override based on whether history is provided
    if st.session_state.previous_report is not None:
        context += f"\n\n[System Context: Previous Advisory Report for Comparison:\n{st.session_state.previous_report}]\n"
        behavior_override = "\n\nCRITICAL OVERRIDE: Respond ONLY in clean Markdown. A previous report has been provided. You MUST do a comparative analysis, check compliance on past recommendations, and track progression."
    else:
        behavior_override = "\n\nCRITICAL OVERRIDE: Respond ONLY in clean Markdown. No previous report was provided. Do not ask for one. Treat this as the Initial Baseline Review."
    
    full_prompt = prompt + context + behavior_override

    # Get response from Gemini
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        response = st.session_state.chat_session.send_message(full_prompt, stream=True)
        
        full_response = ""
        for chunk in response:
            full_response += chunk.text
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
