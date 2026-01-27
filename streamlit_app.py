import streamlit as st
import time

text = "Unfortunately, this isn't actually an AI response - it's just a generator I created in the app. Sorry to fool you, but for this example I just wanted to show how everything works without making API calls to my Snowflake account."

def make_stream():
    for chunk in text:
        yield chunk
        time.sleep(0.01) 

# App title
st.title("My First Cortex AI App")

# Annotated input section
st.subheader("1. Enter Your Prompt")
st.caption("This text input is created with `st.text_input()` — it captures what you type and stores it in a variable.")
p = st.text_input("Enter your prompt:", placeholder="Ask me anything...")

# Annotated button section
st.subheader("2. Generate a Response")
st.caption("This button is created with `st.button()` — remember, if you click it it will first check there's a prompt in the box above before sending it the the LLM.")
if st.button("Generate Response"):
    if not p:
        st.warning("Please enter a prompt first!")
        st.stop()

    # Annotated response section
    st.subheader("3. AI Response")
    st.caption("The response streams in using `st.write_stream()` with `complete(..., stream=True)` — watch it appear word by word!")
    st.write_stream(make_stream())
