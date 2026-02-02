import streamlit as st
from snowflake.snowpark import Session
from snowflake.snowpark.functions import ai_complete
import json

@st.cache_resource
def get_session(): return Session.builder.configs(st.secrets["connections"]["snowflake"]).create()

def call_llm(p): return json.loads(s.range(1).select(ai_complete("claude-3-5-sonnet", p)).collect()[0][0])

s = get_session()
ss = st.session_state

if "ms" not in ss: ss["ms"] = []

st.title("A Simple AI Chatbot")
st.caption("A simple chatbot built with Streamlit and Snowflake Cortex")

st.info("""
**How this works:** This chatbot demonstrates the core pattern for building conversational AI apps:
1. Store messages in `st.session_state` so they persist across reruns
2. Display the conversation history using `st.chat_message()`
3. Capture user input with `st.chat_input()`
4. Pass the full conversation to the LLM so it has context
""")

with st.expander("How the history loop works", expanded=False):
    st.markdown("""
    ```python
    for m in ss["ms"]:
        st.chat_message(m["role"]).write(m["content"])
    ```
    This loop runs on **every rerun**, rebuilding the chat display from the messages 
    stored in session state. New messages are displayed inline (below), then added 
    to history for this loop to find on the *next* rerun.
    """)

for m in ss["ms"]:
    st.chat_message(m["role"]).write(m["content"])

with st.expander("How input handling works", expanded=False):
    st.markdown("""
    ```python
    if prompt := st.chat_input("Type here..."):
        # Display user message immediately
        st.chat_message("user").write(prompt)
        ss["ms"].append({"role": "user", "content": prompt})
        
        # Build conversation history string
        p = "\\n\\n".join([f'{m["role"]}: {m["content"]}' for m in ss["ms"]]) + "\\n\\nassistant:"
        
        # Call LLM and display response
        r = call_llm(p)
        st.chat_message("assistant").write(r)
        ss["ms"].append({"role": "assistant", "content": r})
    ```
    The walrus operator (`:=`) assigns and checks the input in one line. We display 
    messages **inline** for immediate feedback, then append to history for persistence.
    """)

if i := st.chat_input("Type a message..."):
    st.chat_message("user").write(i)
    ss["ms"].append({"role": "user", "content": i})
    
    p = "\n\n".join([f'{m["role"]}: {m["content"]}' for m in ss["ms"]]) + "\n\nassistant:"
    
    with st.spinner("Thinking..."): r = call_llm(p)
    
    st.chat_message("assistant").write(r)
    ss["ms"].append({"role": "assistant", "content": r})

with st.sidebar:
    st.header("Debug View")
    st.caption("See what's happening behind the scenes")
    
    with st.expander("View session state", expanded=True):
        st.write(f"**Message count:** {len(ss['ms'])}")
        if ss["ms"]:
            st.json(ss["ms"])
        else:
            st.write("*No messages yet*")
    
    with st.expander("View prompt sent to LLM"):
        if ss["ms"]:
            prompt_preview = "\n\n".join([f'{m["role"]}: {m["content"]}' for m in ss["ms"]]) + "\n\nassistant:"
            st.code(prompt_preview, language=None)
        else:
            st.write("*Send a message to see the prompt*")
