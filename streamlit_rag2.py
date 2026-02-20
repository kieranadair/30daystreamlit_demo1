# ─── 1. IMPORTS ───
import streamlit as st, json
from snowflake.snowpark import Session
from snowflake.snowpark.functions import ai_complete
from snowflake.core import Root

# ─── 2. CONFIGURATION ───
DB, SCHEMA, CSS_NAME = "RAG_DB", "RAG_SCHEMA", "CUSTOMER_REVIEW_SEARCH"
MODEL, N_RESULTS, SLIDE_WINDOW = "claude-3-5-sonnet", 10, 12

SYSTEM_PROMPT = """You are a customer review analysis chatbot. Your role is to ONLY answer questions about customer reviews and feedback.

STRICT GUIDELINES:
1. ONLY use information from the provided customer review context below
2. If asked about topics unrelated to customer reviews (e.g., general knowledge, coding, math, news), respond: "I can only answer questions about customer reviews. Please ask about product feedback, customer experiences, or review insights."
3. If the context doesn't contain relevant information, say: "I don't have enough information in the customer reviews to answer that."
4. Stay focused on: product features, customer satisfaction, complaints, praise, quality, pricing, shipping, or customer service mentioned in reviews
5. Do NOT make up information or use knowledge outside the provided reviews
6. Provide a clear, helpful answer based ONLY on the customer reviews above. If you cite information, mention it naturally.
7. If the user's question cannot be answered with the provided context, ask them to be more specific and decline to answer the question."""

WELCOME = """Hello! I'm a customer review chatbot. Ask me anything about our products - I'll search through customer feedback to find relevant insights.

We sell the following products: Thermal Gloves, Alpine Skis, Carbon Fiber Poles, Ski Goggles, Performance Racing Skis, Insulated Jackets, Avalanche Safety Packs, Mountain Series Helmets, Alpine Base Layers, and Pro Ski Boots."""

INFO_TEXT = """This chatbot uses **Snowflake Cortex Search** to find relevant customer reviews from a sample of 100 reviews, then uses an LLM to synthesise answers.

**How it works:**
1. Your question is rewritten using conversation context for better search results
2. The rewritten query is sent to a Cortex Search Service
3. Semantically similar review chunks are retrieved and filtered by similarity
4. The LLM generates an answer grounded in those reviews and the conversation history

You can adjust the similarity threshold in the sidebar, and view the sources used in the expandable panel below each response.

**Sources panel:**
- ✅ = Chunk passed to LLM (meets threshold)
- ❌ = Chunk retrieved but filtered out
"""

REWRITE_PROMPT = """Based on the chat history below and the question, generate a search query that makes the question self-contained. Answer with only the query. Assume the reader of this query will have no knowledge of the chat history.

<chat_history>
{chat_history}
</chat_history>

<question>
{question}
</question>"""

PROMPT = """<system>
{sys}
</system>

<context>
{ctx}
</context>

<conversation>
{conv}
YOUR RESPONSE: """

# ─── 3. FUNCTIONS ───
@st.cache_resource
def get_session():
    S = Session.builder.configs(st.secrets["connections"]["snowflake"]).create()
    S.sql(f"USE SCHEMA {DB}.{SCHEMA}").collect()
    return S

@st.cache_resource
def get_css(_s):
    "Initialise Cortex Search Service and discover columns"
    R = Root(_s)
    css = R.databases[DB].schemas[SCHEMA].cortex_search_services[CSS_NAME]
    cols = _s.sql(f"DESC CORTEX SEARCH SERVICE {DB}.{SCHEMA}.{CSS_NAME}").collect()[0].columns.split(",")
    return css, cols

def call_llm(p): return json.loads(S.range(1).select(ai_complete(MODEL, p)).collect()[0][0])

def search_css(q, threshold):
    "Query CSS, add valid flag based on cosine similarity threshold"
    results = css.search(query=q, columns=cols, limit=N_RESULTS).results
    for c in results:
        c["valid"] = c["@scores"]["cosine_similarity"] >= threshold
    return results

def get_chat_history():
    "Get recent conversation as formatted string within sliding window"
    start = max(0, len(ss["ms"]) - SLIDE_WINDOW)
    return "\n\n".join([f"{m['role']}: {m['content']}" for m in ss["ms"][start:]])

def rewrite_question(question):
    "Rewrite a follow-up question to be self-contained using conversation context"
    if len(ss["ms"]) <= 3: return question
    p = REWRITE_PROMPT.format(chat_history=get_chat_history(), question=question)
    return call_llm(p)

def fmt_prompt(chunks):
    "Build RAG prompt with system, context (valid chunks only), and conversation"
    conv = "\n\n".join([f"{m['role']}: {m['content']}" for m in ss["ms"][1:]])
    valid_chunks = [c for c in chunks if c["valid"]]
    ctx = "\n\n".join([f"### Source: {c['FILE_NAME']} ###\n{c['CHUNK_TEXT']}" for c in valid_chunks])
    return PROMPT.format(sys=SYSTEM_PROMPT, ctx=ctx, conv=conv)

def show_ctx(ctx):
    "Format chunks for display in expander with valid/invalid indicators"
    with st.expander("View sources:"):
        for i, o in enumerate(ctx):
            icon = "✅" if o["valid"] else "❌"
            st.write(f"**{icon} {o['FILE_NAME']}** (similarity: {o['@scores']['cosine_similarity']:.2f})")
            st.write(o["CHUNK_TEXT"])
            if i < len(ctx) - 1: st.divider()

def clear_history():
    if "ms" in ss: del ss["ms"]
    if "ctxs" in ss: del ss["ctxs"]

# ─── 4. SETUP ───
S = get_session()
ss = st.session_state
css, cols = get_css(S)

# ─── 5. SESSION STATE INITIALISATION ───
if "ms" not in ss: ss["ms"] = [dict(role="system", content=SYSTEM_PROMPT), dict(role="assistant", content=WELCOME)]
if "ctxs" not in ss: ss["ctxs"] = dict()

# ─── 6. SIDEBAR ───
with st.sidebar:
    min_cos = st.slider("Similarity Threshold", min_value=0.25, max_value=0.75, value=0.50, step=0.05)
    st.caption("""
    **Lower threshold (0.25–0.40):** More chunks pass through, broader context but may include less relevant results.
    
    **Higher threshold (0.60–0.75):** Stricter filtering, only highly relevant chunks pass through but may miss useful context.
    
    **Recommended (0.40–0.60):** Balanced approach for most queries.
    """)
    st.divider()
    st.button("Clear chat", on_click=clear_history, use_container_width=True)

# ─── 7. MAIN CONTENT ───
st.title("Customer Review Chatbot")
st.info(INFO_TEXT)
st.divider()

for i, m in enumerate(ss["ms"]):
    if m["role"] == "system": continue
    with st.chat_message(m["role"]):
        st.write(m["content"])
        if i in ss["ctxs"]: show_ctx(ss["ctxs"][i])

# ─── 8. INPUT HANDLING ───
if inp := st.chat_input("Ask about customer reviews..."):
    st.chat_message("user").write(inp)
    ss["ms"].append(dict(role="user", content=inp))

    try:
        with st.spinner("Searching reviews..."):
            q = rewrite_question(inp)
            ctx = search_css(q, min_cos)
            valid_ctx = [c for c in ctx if c["valid"]]

        if not valid_ctx:
            msg = f"Your query returned no results with similarity ≥ {min_cos:.2f}. Try lowering the threshold in the sidebar or being more specific."
            st.chat_message("assistant").write(msg)
            ss["ms"].pop()
            st.stop()

        ss["ctxs"][len(ss["ms"])] = ctx

        with st.spinner("Generating answer..."):
            r = call_llm(fmt_prompt(ctx))
            ss["ms"].append(dict(role="assistant", content=r))
            with st.chat_message("assistant"):
                st.write(r)
                show_ctx(ctx)

    except Exception as e:
        st.error(f"Error: {e}")
        ss["ms"].pop()
