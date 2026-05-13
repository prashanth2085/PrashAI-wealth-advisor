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

# Load the base system prompt
@st.cache_data
def load_system_prompt():
    try:
        with open("system_prompt.md", "r") as file:
            return file.read()
    except FileNotFoundError:
        return "You are an expert financial advisor."

BASE_SYSTEM_PROMPT = load_system_prompt()

# Initialize Session States for Data & Memory
if "portfolio_data" not in st.session_state:
    st.session_state.portfolio_data = None
if "previous_report" not in st.session_state:
    st.session_state.previous_report = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- SIDEBAR: Data Ingestion & Controls ---
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
        
    st.divider()
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()

# --- BUILD THE AI'S BRAIN (SYSTEM PROMPT) ---
# We inject the data here so it doesn't snowball in the chat history
dynamic_system_prompt = BASE_SYSTEM_PROMPT
if st.session_state.portfolio_data is not None:
    dynamic_system_prompt += f"\n\n[System Context: Current Portfolio Data:\n{st.session_state.portfolio_data.to_string()}]\n"
if st.session_state.previous_report is not None:
    dynamic_system_prompt += f"\n\n[System Context: Previous Advisory Report:\n{st.session_state.previous_report}]\n"
    dynamic_system_prompt += "\nCRITICAL INSTRUCTION: A previous report was provided. You MUST do a comparative analysis."
else:
    dynamic_system_prompt += "\nCRITICAL INSTRUCTION: No previous report provided. Treat this as the Initial Baseline Review."

# Initialize Gemini Model with Dynamic Memory
genai.configure(api_key=os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=dynamic_system_prompt
)

# Initialize Chat Session
chat_session = model.start_chat(history=st.session_state.chat_history)

# --- MAIN CHAT INTERFACE ---
for message in st.session_state.chat_history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        msg_text = message.parts[0].text if hasattr(message.parts[0], 'text') else str(message.parts[0])
        if "<!DOCTYPE html>" in msg_text or "<html" in msg_text:
            st.info("📄 HTML Report Generated in previous turn.")
        else:
            st.markdown(msg_text)

if prompt := st.chat_input("Ask your wealth advisor a question..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        try:
            # We now ONLY send the user's text. The data is safely in the system prompt.
            response = chat_session.send_message(prompt, stream=True)
            
            full_response = ""
            for chunk in response:
                full_response += chunk.text
                if "<!DOCTYPE" not in full_response and "<html" not in full_response:
                    message_placeholder.markdown(full_response + "▌")
            
            # FINAL RENDER LOGIC
            if "<!DOCTYPE html>" in full_response or "<html" in full_response:
                message_placeholder.empty()
                st.success("✅ Institutional Report Generated Successfully")
                
                clean_html = full_response
                start_tag = "<!DOCTYPE html>" if "<!DOCTYPE html>" in clean_html else "<html"
                if start_tag in clean_html:
                    clean_html = clean_html[clean_html.find(start_tag):]
                    if clean_html.endswith("```"):
                        clean_html = clean_html[:-3]
                    elif "\n```" in clean_html:
                        clean_html = clean_html.split("\n```")[0]
                
                st.download_button(
                    label="📥 Download Wealth Advisory Report (.html)",
                    data=clean_html,
                    file_name="wealth_advisory_report.html",
                    mime="text/html"
                )
                
                with st.expander("🔍 Preview Report", expanded=True):
                    components.html(clean_html, height=800, scrolling=True)
            else:
                message_placeholder.markdown(full_response)
            
            # Save history to session state
            st.session_state.chat_history = chat_session.history
            
        except Exception as e:
            st.error(f"API Error: {e}")
            st.warning("You hit a rate limit or token quota. Please click 'Clear Chat History' in the sidebar to reset your session.")
