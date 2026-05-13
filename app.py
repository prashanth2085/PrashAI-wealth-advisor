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
        return "You are an expert financial advisor. (Please add system_prompt.md)"

SYSTEM_PROMPT = load_system_prompt()

# Initialize Gemini Model
# We use gemini-1.5-pro or flash as it supports system instructions natively
genai.configure(api_key=os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    system_instruction=SYSTEM_PROMPT
)

# Initialize Session State for Chat History
if "chat_session" not in st.session_state:
    st.session_state.chat_session = model.start_chat(history=[])
if "portfolio_data" not in st.session_state:
    st.session_state.portfolio_data = None

# --- SIDEBAR: Data Ingestion ---
with st.sidebar:
    st.header("📊 Portfolio Data")
    uploaded_file = st.file_uploader("Upload Zerodha Holdings (CSV)", type=['csv'])
    
    if uploaded_file is not None:
        try:
            # Basic parsing - adjust skiprows based on exact Zerodha CSV format
            df = pd.read_csv(uploaded_file, skiprows=14) 
            st.session_state.portfolio_data = df
            st.success("Portfolio loaded successfully.")
            
            # Display quick metrics
            st.metric("Total Positions", len(df))
        except Exception as e:
            st.error(f"Error parsing CSV: {e}")

# --- MAIN CHAT INTERFACE ---
# Display chat history
for message in st.session_state.chat_session.history:
    role = "assistant" if message.role == "model" else "user"
    with st.chat_message(role):
        st.markdown(message.parts[0].text)

# Input box for user query
if prompt := st.chat_input("Ask your wealth advisor a question..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Inject portfolio data into the context if available
    context = ""
    if st.session_state.portfolio_data is not None:
        context = f"\n\n[System Context: The user's current portfolio data is as follows:\n{st.session_state.portfolio_data.to_string()}]\n"
    
    full_prompt = prompt + context

    # Get response from Gemini
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        # Stream the response for a natural chat feel
        response = st.session_state.chat_session.send_message(full_prompt, stream=True)
        
        full_response = ""
        for chunk in response:
            full_response += chunk.text
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
