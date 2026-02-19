# ─── 1. IMPORTS ───
import streamlit as st, json
from snowflake.snowpark import Session
from snowflake.snowpark.functions import ai_complete
from snowflake.core import Root

# ─── 2. CONFIGURATION ───
DB, SCHEMA, CSS_NAME = "RAG_DB", "RAG_SCHEMA", "CUSTOMER_REVIEW_SEARCH"
MODEL, N_RESULTS = "claude-3-5-sonnet", 10

SYSTEM_PROMPT = """You are a customer review analysis assistant. Your role is to ONLY answer questions about customer reviews and feedback.

STRICT GUIDELINES:
1. ONLY use information from the provided customer review context below
2. If asked about topics unrelated to customer reviews, respond: "I can only answer questions about customer reviews. Please ask about product feedback, customer experiences, or review insights."
3. If the context doesn't contain relevant information, say: "I don't have enough information in the customer reviews to answer that."
4. Stay focused on: product features, customer satisfaction, complaints, praise, quality, pricing, shipping, or customer service mentioned in reviews
5. Do NOT make up information or use knowledge outside the provided reviews
6. Provide a clear, helpful answer based ONLY on the customer reviews above. If you cite information, mention it naturally."""

PROMPT = """<system>
{sys}
</system>

<context>
{ctx}
</context>

<question>
{question}
</question>

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

def fmt_prompt(question, chunks):
    "Build RAG prompt with system instructions and valid context chunks"
    valid_chunks = [c for c in chunks if c["valid"]]
    ctx = "\n\n".join([f"### Source: {c['FILE_NAME']} ###\n{c['CHUNK_TEXT']}" for c in valid_chunks])
    return PROMPT.format(sys=SYSTEM_PROMPT, ctx=ctx, question=question)

def show_ctx(ctx):
    "Display retrieved chunks with valid/invalid indicators"
    with st.expander("View sources:"):
        for i, o in enumerate(ctx):
            icon = "✅" if o["valid"] else "❌"
            st.write(f"**{icon} {o['FILE_NAME']}** (similarity: {o['@scores']['cosine_similarity']:.2f})")
            st.write(o["CHUNK_TEXT"])
            if i < len(ctx) - 1: st.divider()

# ─── 4. SETUP ───
S = get_session()
css, cols = get_css(S)

# ─── 5. SIDEBAR ───
with st.sidebar:
    min_cos = st.slider("Similarity Threshold", min_value=0.25, max_value=0.75, value=0.50, step=0.05)
    st.caption("""
    **Lower (0.25–0.40):** Broader context, may include less relevant results.
    **Higher (0.60–0.75):** Stricter filtering, may miss useful context.
    **Recommended (0.40–0.60):** Balanced approach for most queries.
    """)

# ─── 6. MAIN CONTENT ───
st.title("Customer Review Search")
st.info("""Ask a question about our products and we'll search customer reviews for relevant insights.

**Products:** Thermal Gloves, Alpine Skis, Carbon Fiber Poles, Ski Goggles, Performance Racing Skis, Insulated Jackets, Avalanche Safety Packs, Mountain Series Helmets, Alpine Base Layers, and Pro Ski Boots.""")

# ─── 7. INPUT HANDLING ───
if q := st.text_input("What would you like to know about our products?"):
    ctx = search_css(q, min_cos)
    valid_ctx = [c for c in ctx if c["valid"]]

    if not valid_ctx:
        st.warning(f"No results met the similarity threshold ({min_cos:.2f}). Try lowering it in the sidebar or rephrasing your question.")
        st.stop()

    try:
        with st.spinner("Searching reviews and generating answer..."):
            r = call_llm(fmt_prompt(q, ctx))

        st.subheader("Answer")
        with st.container(border=True):
            st.markdown(r)
        show_ctx(ctx)

    except Exception as e:
        st.error(f"Error: {e}")
