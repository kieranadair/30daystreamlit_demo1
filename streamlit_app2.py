# Imports
import streamlit as st
from snowflake.snowpark import Session
from snowflake.cortex import complete
from time import time

# Cached Functions
@st.cache_resource
def get_session():
    return Session.builder.configs(st.secrets["connections"]["snowflake"]).create()

@st.cache_data(show_spinner="Communing with the AI gods...")
def call_cortex_llm(prompt):
    return complete(session=s, model=m, prompt=prompt)

# Setup
s = get_session()
m = "claude-3-5-sonnet"
PROMPT_TEMPLATE = """Write a joke about {topic}, it should be roughly {number} words long."""

# App Title
st.title("Joke Generator with Caching")

# User Inputs
st.subheader("1. Configure Your Joke")
st.caption("These inputs are wrapped in `st.form()` — the app won't rerun until you click Submit. The dropdown uses `st.selectbox()` and the slider uses `st.slider()`.")

with st.form("prompt_form"):
    topic = st.selectbox("Sport:", ["Cricket", "Basketball", "AFL"])
    number = st.slider("Approximate word count:", 50, 300, 150)
    submitted = st.form_submit_button("Generate Joke")

if submitted:
    st.subheader("2. Generated Joke")
    st.caption("The response is cached with `@st.cache_data` — try submitting the same inputs twice and watch the query time drop to near zero!")
    
    prompt = PROMPT_TEMPLATE.format(topic=topic, number=number)
    
    response_sent = time()
    response = call_cortex_llm(prompt)
    query_time = time() - response_sent
    
    with st.container(border=True):
        st.write(response)
        st.success(f"Response time: {query_time:.2f} seconds")
    
    st.subheader("3. Behind the Scenes")
    st.caption("This `st.expander()` shows the final prompt after `.format()` substituted your inputs into the template.")
    with st.expander("View Generated Prompt"):
        st.code(prompt)
