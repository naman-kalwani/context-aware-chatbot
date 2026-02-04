import streamlit as st
import asyncio
from main import chat

# Page config
st.set_page_config(
    page_title="Context-Aware Chatbot",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.8rem;
        font-weight: 700;
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 1.5rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        letter-spacing: -0.5px;
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
        font-style: italic;
        opacity: 0.8;
    }
    
    .project-title {
        font-size: 2rem;
        font-weight: 800;
        color: #667eea;
        text-align: center;
        margin-bottom: 2rem;
        letter-spacing: 0.5px;
    }
    
    .stChatMessage {
        margin: 1rem 0;
        border-radius: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    .stChatInputContainer {
        padding-top: 1.5rem;
        border-top: 1px solid #000000;
        margin-top: 1rem;
    }
    
    .stChatInput {
        border-radius: 25px !important;
        border: 2px solid #667eea !important;
        padding: 1rem 1.5rem !important;
        font-size: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = "P101"

# Sidebar with project name
with st.sidebar:
    st.markdown("""
    <div class="project-title">
        🧠 Context-Aware<br>Chatbot
    </div>
    """, unsafe_allow_html=True)
    
    # User ID input
    user_id = st.text_input("👤 User ID", value=st.session_state.user_id, key="user_id_input")
    st.session_state.user_id = user_id

# Main header
st.markdown('<h1 class="main-header">🧠 Context-Aware AI Assistant</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Intelligent conversations powered by advanced memory systems</p>', unsafe_allow_html=True)

# Chat interface
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Get assistant response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response_placeholder = st.empty()
            full_response = ""
            
            async def get_response():
                response_text = ""
                async for token in chat(prompt, st.session_state.user_id):
                    response_text += token
                    response_placeholder.markdown(response_text + "▌")
                response_placeholder.markdown(response_text)
                return response_text
            
            # Run async function
            full_response = asyncio.run(get_response())
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})
