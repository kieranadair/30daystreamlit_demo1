import streamlit as st
from time import time
import json
from snowflake.snowpark.functions import ai_complete
from snowflake.snowpark import Session
import pandas as pd

# --- Config ---
models = {
    "claude-3-5-sonnet": {"input": 1.50, "output": 7.50},
    "llama3.1-70b": {"input": 0.36, "output": 0.36},
    "llama3.1-8b": {"input": 0.11, "output": 0.11},
    "mistral-large2": {"input": 1.00, "output": 3.00},
    "mistral-7b": {"input": 0.08, "output": 0.10},
    "mixtral-8x7b": {"input": 0.23, "output": 0.35},
}

# --- Helper Functions ---
def call_llm_metrics(m, p):
    """Call LLM and return response with metrics."""
    l = time()
    r = json.loads(s.range(1).select(ai_complete(model=m, prompt=p)).collect()[0][0])
    l = time() - l
    input_t = int(len(p.split()) * (4/3))
    output_t = int(len(r.split()) * (4/3))
    input_cost = (input_t / 1_000_000) * models[m]["input"]
    output_cost = (output_t / 1_000_000) * models[m]["output"]
    return {
        "model": m, "response": r, "latency": l,
        "input_tokens": input_t, "output_tokens": output_t,
        "total_cost_per_10k": (input_cost + output_cost) * 10_000
    }

def get_winners(rs):
    """Calculate min/max for each metric. Returns dict of model names."""
    return {
        "fastest": min(rs, key=lambda x: x["latency"])["model"],
        "slowest": max(rs, key=lambda x: x["latency"])["model"],
        "cheapest": min(rs, key=lambda x: x["total_cost_per_10k"])["model"],
        "priciest": max(rs, key=lambda x: x["total_cost_per_10k"])["model"],
        "longest": max(rs, key=lambda x: x["output_tokens"])["model"],
    }

def get_badges(r, w):
    """Build badge list for a result based on winners dict."""
    badges = []
    if r["model"] == w["fastest"]: badges.append("🚀 Fastest")
    if r["model"] == w["slowest"]: badges.append("🐢 Slowest")
    if r["model"] == w["cheapest"]: badges.append("💰 Cheapest")
    if r["model"] == w["priciest"]: badges.append("💸 Priciest")
    if r["model"] == w["longest"]: badges.append("📝 Most Detailed")
    return badges

def render_charts(df):
    """Render three comparison bar charts."""
    c1, c2, c3 = st.columns(3)
    c1.caption("Latency (seconds)"); c1.bar_chart(df["latency"])
    c2.caption("Cost per 10k (credits)"); c2.bar_chart(df["total_cost_per_10k"])
    c3.caption("Output Tokens"); c3.bar_chart(df["output_tokens"])

def render_card(r, w):
    """Render a single model result card."""
    with st.container(border=True):
        badges = get_badges(r, w)
        if badges: st.write(" • ".join(badges))
        st.subheader(r["model"])
        st.write(f"**Latency:** {r['latency']:.2f}s")
        st.write(f"**Input tokens:** {r['input_tokens']}")
        st.write(f"**Output tokens:** {r['output_tokens']}")
        st.write(f"**Cost per 10k queries:** {r['total_cost_per_10k']:.2f} credits")
        st.chat_message("assistant").write(r["response"])

# --- Main App ---
s = Session.builder.configs(st.secrets["connections"]["snowflake"]).create()

st.title(":material/compare: Comparing Model Performance")
st.write("Write a prompt in the input box below, and you can see how a set of different LLMs compare when responding to it. The purpose of this app is to find the best model for your specific task.")

p = st.chat_input(placeholder="Write a prompt to test")
if not p: st.stop()  # Early exit if no prompt

# Run models with status
st.chat_message("user").write(p)

with st.status("Running models...", expanded=True) as status:
    rs = []
    for m in [*models]:
        st.write(f"🔄 Testing {m}...")
        rs.append(call_llm_metrics(m, p))
    st.write("📊 Generating report...")
    status.update(label="Complete!", state="complete", expanded=False)

# Generate report
w = get_winners(rs)
df = pd.DataFrame(rs).set_index("model")

render_charts(df)
st.divider()

for i in range(0, len(rs), 2):
    c1, c2 = st.columns(2)
    for col, r in zip([c1, c2], rs[i:i+2]):
        with col: render_card(r, w)
