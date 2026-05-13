import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
import pandas as pd
import os
from dotenv import load_dotenv

# Load local environment variables (API Key)
load_dotenv()

# Configure Streamlit Page
st.set_page_config(page_title="AI Wealth Advisor", page_icon="📈", layout="wide")
st.title("🏦 AI Wealth Advisor & Portfolio Manager")

# Load the system prompt
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
    uploaded_history = st.file_uploader("Upload Previous Report (HTML/Text)", type=['html', 'txt', 'md'])
    
    if uploaded_history is not None:
        st.session_state.previous_report = uploaded_history.read().decode("utf-8")
        st.success("Historical report loaded for comparison.")

# --- MAIN CHAT INTERFACE ---
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        # If the history contains HTML, show a placeholder instead of the code wall
        if "<!DOCTYPE html>" in message.parts[0].text or "<html" in message.parts[0].text:
            st.info("📄 HTML Report Generated in previous turn.")
        else:
            st.markdown(message.parts[0].text)

if prompt := st.chat_input("Ask your wealth advisor a question..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Inject portfolio and historical data
    context = ""
    if st.session_state.portfolio_data is not None:
        context += f"\n\n[System Context: Current portfolio data:\n{st.session_state.portfolio_data.to_string()}]\n"
    
    if st.session_state.previous_report is not None:
        context += f"\n\n[System Context: Previous Advisory Report for Comparison:\n{st.session_state.previous_report}]\n"
        behavior_override = "\n\nCRITICAL INSTRUCTION: A previous report has been provided. You MUST do a comparative analysis."
    else:
        behavior_override = "\n\nCRITICAL INSTRUCTION: No previous report was provided. Treat this as the Initial Baseline Review."
    
    full_prompt = prompt + context + behavior_override

    # Get response from Gemini
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        response = st.session_state.chat_session.send_message(full_prompt, stream=True)
        
        full_response = ""
        for chunk in response:
            full_response += chunk.text
            # Only stream text to the UI if it doesn't look like an HTML file is starting
            if "<!DOCTYPE" not in full_response and "<html" not in full_response:
                message_placeholder.markdown(full_response + "▌")
        
        # FINAL RENDER LOGIC
        if "<!DOCTYPE html>" in full_response or "<html" in full_response:
            message_placeholder.empty() # Clear the code wall
            st.success("✅ Institutional Report Generated Successfully")
            
            # Provide a native download button for the HTML file
            st.download_button(
                label="📥 Download Wealth Advisory Report (.html)",
                data=full_response,
                file_name="wealth_advisory_report.html",
                mime="text/html"
            )
            
            # Render the HTML directly inside a safe iframe in the app
            with st.expander("🔍 Preview Report", expanded=True):
                components.html(full_response, height=800, scrolling=True)
        else:
            message_placeholder.markdown(full_response)
