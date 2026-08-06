import streamlit as st
import requests

# 1. Page Configuration & Styling
st.set_page_config(page_title="Autonomous AI Data Analyst", page_icon="📊", layout="wide")

st.title("📊 Autonomous AI Data Analyst")
st.markdown("""
Welcome! This assistant is powered by the **Model Context Protocol (MCP)** architecture framework. 
It can dynamically execute standard SQL analytics on your local database or search the live web using DuckDuckGo to synthesize insights.
""")
st.write("---")

# 2. Initialize Persistent Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# 3. Render Historical Chat Log
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 4. Accept Live User Input
if user_prompt := st.chat_input("Ask me about company metrics, financial data, or related industry web trends..."):
    
    # Display user input instantly in the UI
    with st.chat_message("user"):
        st.markdown(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # Trigger the Agentic Backend Bridge
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        response_placeholder.markdown("*Thinking... Agent routing active tools...*")
        
        try:
            # Send payload to your local FastAPI server running on port 8000
            backend_url = "http://127.0.0.1:8000/chat"
            payload = {"prompt": user_prompt}
            
            reply = requests.post(backend_url, json=payload, timeout=60)
            
            if reply.status_code == 200:
                agent_response = reply.json().get("response", "Error: Empty response payload received.")
                response_placeholder.markdown(agent_response)
                st.session_state.messages.append({"role": "assistant", "content": agent_response})
            else:
                response_placeholder.markdown(f"❌ Backend Server Error: Status code {reply.status_code}")
                
        except requests.exceptions.ConnectionError:
            response_placeholder.markdown("❌ Connection Error: Could not reach the FastAPI backend server. Is it running on port 8000?")
        except Exception as e:
            response_placeholder.markdown(f"❌ Verification Exception: {str(e)}")