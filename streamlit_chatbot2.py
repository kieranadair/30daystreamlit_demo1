import streamlit as st
from snowflake.snowpark import Session
from snowflake.snowpark.functions import ai_complete
import json

# ─── Config ───
M = "claude-3-5-sonnet"

PERSONAS = {
    "Pirate": "You are a helpful pirate assistant named Captain Starlight. You speak with pirate slang, use nautical metaphors, and end sentences with 'Arrr!' when appropriate.",
    "Teacher": "You are Professor Ada, a patient and encouraging teacher. You explain concepts clearly, use examples, and always check for understanding.",
    "Comedian": "You are Chuckles McGee, a witty comedian assistant. You love puns, jokes, and humor, but you're still genuinely helpful.",
    "Robot": "You are UNIT-7, a helpful robot assistant. You speak in a precise, logical manner.",
}

# ─── Functions ───
@st.cache_resource
def get_session(): return Session.builder.configs(st.secrets["connections"]["snowflake"]).create()

def call_llm(p): return json.loads(s.range(1).select(ai_complete(M, p)).collect()[0][0])

def change_persona():
    if "ms" in ss: del ss["ms"]

# ─── Setup ───
s = get_session()
ss = st.session_state

# ─── Sidebar ───
with st.sidebar: st.selectbox("Choose your assistant:", options=[*PERSONAS], key="persona", on_change=change_persona)

# ─── Initialisation ───
if "ms" not in ss:
    ss["ms"] = [
        {"role": "system", "content": PERSONAS[ss["persona"]},
        {"role": "assistant", "content": "Hello! How can I help you today?"}
    ]

# ─── Display ───
st.title("Persona Chatbot")
st.info(f"Currently chatting with: **{ss['persona']}**")

with st.expander("View system prompt"): st.write(PERSONAS[ss["persona"]])

for m in ss["ms"]:
    if m["role"] != "system": st.chat_message(m["role"]).write(m["content"])

# ─── Input ───
if i:= st.chat_input("Type here..."):
    st.chat_message("user").write(i)
    ss["ms"].append({"role": "user", "content": i})
    
    p = "\n\n".join([f'{m["role"]}: {m["content"]}' for m in ss["ms"]]) + "\n\nassistant:"
    with st.spinner("Thinking"): r = call_llm(p)
    st.chat_message("assistant").write(r)
    ss["ms"].append({"role": "assistant", "content": r})
