import streamlit as st
import time
from search_query import search_index
from sql_helper import generate_sql_query

# Page Config
st.set_page_config(
    page_title="TEQTANK AI Search",
    page_icon="🤖",
    layout="centered"
)

# Custom CSS for a cleaner look
st.markdown("""
<style>
    .stChatMessage {
        background-color: #000000; 
        color: #ffffff;
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .stChatMessage[data-testid="stChatMessageUser"] {
        background-color: #000000;
        color: #ffffff;
    }
    .source-box {
        background-color: #ffffff;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
        margin-top: 5px;
        font-size: 0.9em;
    }
    .source-header {
        font-weight: bold;
        color: #333;
    }
    .source-score {
        color: #666;
        font-size: 0.8em;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar for Mode Selection
st.sidebar.title("Configuration")
mode = st.sidebar.radio("Select Mode", ["Knowledge Base Search", "SQL Query Generator"])

if mode == "Knowledge Base Search":
    # Title
    st.title("🤖 TEQTANK AI Search")
    st.markdown("Ask questions about your indexed documents.")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "results" in message:
                for result in message["results"]:
                    with st.expander(f"📄 Source: {result['source']} (Score: {result['score']:.4f})"):
                        st.markdown(f"**Content Preview:**\n\n{result['content']}")

    # React to user input
    if prompt := st.chat_input("What would you like to know?"):
        # Display user message in chat message container
        st.chat_message("user").markdown(prompt)
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Searching knowledge base...")
            
            # Perform Search
            try:
                results = search_index(prompt)
                
                if results:
                    response_text = f"I found **{len(results)}** relevant documents for your query."
                    message_placeholder.markdown(response_text)
                    
                    # Display results
                    for result in results:
                        with st.expander(f"📄 Source: {result['source']} (Score: {result['score']:.4f})"):
                            st.markdown(f"**Content Preview:**\n\n{result['content']}")
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response_text,
                        "results": results
                    })
                else:
                    response_text = "I couldn't find any relevant documents in the index."
                    message_placeholder.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    
            except Exception as e:
                error_text = f"An error occurred during search: {e}"
                message_placeholder.error(error_text)
                st.session_state.messages.append({"role": "assistant", "content": error_text})

elif mode == "SQL Query Generator":
    st.title("💾 Text-to-SQL Generator")
    st.markdown("Convert natural language questions into T-SQL queries based on your schema.")
    
    # Initialize SQL chat history
    if "sql_messages" not in st.session_state:
        st.session_state.sql_messages = []

    # Display chat history
    for message in st.session_state.sql_messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                st.code(message["content"], language="sql")
            else:
                st.markdown(message["content"])

    if prompt := st.chat_input("Describe the data you need..."):
        # User message
        st.chat_message("user").markdown(prompt)
        st.session_state.sql_messages.append({"role": "user", "content": prompt})
        
        # Assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("Generating SQL...")
            
            try:
                sql_query = generate_sql_query(prompt)
                message_placeholder.code(sql_query, language="sql")
                st.session_state.sql_messages.append({"role": "assistant", "content": sql_query})
            except Exception as e:
                message_placeholder.error(f"Error: {e}")
