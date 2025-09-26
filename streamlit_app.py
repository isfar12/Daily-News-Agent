import streamlit as st
from datetime import datetime
from main_agent import process_chat_query
st.set_page_config(
    page_title="🤖 Multi-User News Agent",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

def initialize_session_state():
    """Initialize Streamlit session state variables"""
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'thread_id' not in st.session_state:
        st.session_state.thread_id = None
    if 'session_started' not in st.session_state:
        st.session_state.session_started = False

def create_sidebar():
    """Create sidebar for user session management"""
    with st.sidebar:
        st.header("👤 User Session")
        
        # Session type selection
        session_type = st.radio(
            "Choose session type:",
            ["New User", "Existing Session"],
            help="Select how you want to start your chat session"
        )
        
        if session_type == "New User":
            username = st.text_input(
                "Enter your name:",
                placeholder="e.g., John, Alice, Bob",
                help="This will be used to create your unique session"
            )
            
            if st.button("🚀 Start New Session"):
                if username:
                    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                    st.session_state.thread_id = f"user-{username.lower()}-{timestamp}"
                    st.session_state.current_user = username
                    st.session_state.session_started = True
                    st.session_state.messages = []
                    st.success(f"✅ New session created for {username}")
                    st.rerun()
                else:
                    st.error("Please enter your name")
                    
        elif session_type == "Existing Session":
            thread_id = st.text_input(
                "Enter your Thread ID:",
                placeholder="e.g., user-john-20250925-143022",
                help="Use your existing thread ID to continue previous conversations"
            )
            
            username = st.text_input(
                "Enter your name (optional):",
                placeholder="For display purposes"
            )
            
            if st.button("🔄 Continue Session"):
                if thread_id:
                    st.session_state.thread_id = thread_id
                    st.session_state.current_user = username or "User"
                    st.session_state.session_started = True
                    st.session_state.messages = []
                    st.success(f"✅ Continuing session: {thread_id}")
                    st.rerun()
                else:
                    st.error("Please enter your thread ID")

        
        # Display current session info
        if st.session_state.session_started:
            st.divider()
            st.subheader("📊 Current Session")
            st.info(f"**User:** {st.session_state.current_user}")
            st.info(f"**Thread ID:** {st.session_state.thread_id}")
            
            if st.button("🔄 New Session"):
                st.session_state.clear()
                st.rerun()
        
        # Chat management
        if st.session_state.session_started and st.session_state.messages:
            st.divider()
            st.subheader("💬 Chat Management")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Clear Chat"):
                    st.session_state.messages = []
                    st.success("Chat cleared!")
                    st.rerun()
            
            with col2:
                if st.button("📥 Export Chat"):
                    chat_export = ""
                    for msg in st.session_state.messages:
                        role = "You" if msg["role"] == "user" else "Assistant"
                        chat_export += f"{role}: {msg['content']}\n\n"
                    
                    st.download_button(
                        label="💾 Download Chat History",
                        data=chat_export,
                        file_name=f"chat_history_{st.session_state.current_user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )
    

def display_chat_messages():
    """Display chat messages in the main area"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def get_bot_response(user_input: str) -> str:
    """Get response from the news agent"""
    try:
        # Show progress for news requests
        if any(keyword in user_input.lower() for keyword in ['news', 'article', 'headlines', 'latest']):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("🔍 Processing your request...")
            progress_bar.progress(25)
            
            status_text.text("📰 Fetching news data...")
            progress_bar.progress(50)
            
            # Process without redirecting stdout to avoid context issues
            result = process_chat_query(user_input, thread_id=st.session_state.thread_id)
            
            status_text.text("🤖 Generating response...")
            progress_bar.progress(75)
            
            progress_bar.progress(100)
            status_text.text("✅ Response ready!")
            
            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()
        else:
            # For non-news requests, process normally
            result = process_chat_query(user_input, thread_id=st.session_state.thread_id)
        
        # Extract the actual response from the result
        if result and "messages" in result:
            last_message = result["messages"][-1]
            if hasattr(last_message, 'content'):
                response = last_message.content
                return response
            else:
                return str(last_message)
        
        return "I received your message but couldn't generate a proper response."
        
    except Exception as e:
        st.error(f"Error processing request: {str(e)}")
        return f"❌ Sorry, I encountered an error: {str(e)}\n\nPlease try again or check if all services are running properly."

def main_chat_interface():
    """Main chat interface"""
    if not st.session_state.session_started:
        st.title("News Agent")
        st.markdown("""
        Hi! I'm your **Daily News Agent**! 🚀
        
        **Please create or select a user session from the sidebar to get started.**
        """)
        
        return
    
    # Main chat interface for active sessions
    st.title(f"Chat with News Agent - {st.session_state.current_user}")
    
    # Display chat messages
    display_chat_messages()
    
    # Chat input
    if prompt := st.chat_input(f"Type your message here, {st.session_state.current_user}..."):
        # Add user message to session state
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get and display bot response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                response = get_bot_response(prompt)
            st.markdown(response)
            
        # Add assistant response to session state
        st.session_state.messages.append({"role": "assistant", "content": response})


def main():
    """Main Streamlit app function"""
    initialize_session_state()
    
    # Create sidebar
    create_sidebar()
    
    # Main chat interface
    main_chat_interface()

    
if __name__ == "__main__":
    main()