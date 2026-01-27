# Imports
import streamlit as st
from snowflake.snowpark import Session
from snowflake.cortex import complete
from time import time
import json

# Cached Functions
@st.cache_resource
def get_session():
    return Session.builder.configs(st.secrets["connections"]["snowflake"]).create()

@st.cache_data(show_spinner=False)
def call_cortex_llm(prompt):
    response = complete(session=s, model=m, prompt=prompt)
    return json.loads(response)

# Validation Function
def validate_inputs(description):
    if not description:
        st.warning("Please enter a description!")
        st.stop()
    if len(description) < 10:
        st.warning("Please provide a more detailed description (at least 10 characters)")
        st.stop()

# Generation Function
def generate_with_status(prompt):
    with st.status("Generating your theme...", expanded=True) as status:
        st.write(":material/psychology: Analyzing your requirements...")
        st.write(":material/flash_on: Generating config.toml...")
        response = call_cortex_llm(prompt)
        st.write(":material/check_circle: Theme generated!")
        status.update(label="Theme ready!", state="complete", expanded=False)
    return response

# Setup
s = get_session()
m = "claude-3-5-sonnet"
PROMPT_TEMPLATE = """
<task>

You are a Streamlit theming expert. Generate a complete config.toml file for a Streamlit app based on these requirements:

- Base color preference: {base_color}
- Style description: {description}
- Creativity level: {creativity}/10 (higher = more experimental color choices)

Requirements:
1. Include both [theme.light] and [theme.dark] sections
2. Include a [theme.sidebar] section with complementary colors
3. Use appropriate primaryColor, backgroundColor, secondaryBackgroundColor, textColor
4. Modify buttonRadius if appropriate based on user requirements
5. Include chartCategoricalColors with 3-5 coordinated colors
6. enableStaticServing should remain false

Return your response as valid JSON with exactly two fields:
- "thinking": A 2-3 sentence explanation of your design decisions and color theory reasoning
- "config": The complete config.toml content as a string

Example response format:
{{"thinking": "I chose a deep purple primary color to convey creativity...", "config": "[server]\nenableStaticServing = false\n..."}}

</task>


<example>

[server]
enableStaticServing = false

[theme]
primaryColor = "#00a3e0"
borderColor = "#582c83"
showWidgetBorder = true
baseRadius = "0.3rem"
buttonRadius = "full"
headingFontWeights = [600, 500, 500, 500, 500, 500]
headingFontSizes = ["3rem", "2.5rem", "2.25rem", "2rem", "1.5rem", "1rem"]
chartCategoricalColors = ["#00a3e0", "#582c83", "#ffc862"]

[theme.light]
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#1a1a2e"
linkColor = "#00a3e0"

[theme.dark]
backgroundColor = "#1a1a2e"
secondaryBackgroundColor = "#16213e"
textColor = "#ffffff"
linkColor = "#00a3e0"

[theme.sidebar]
backgroundColor = "#582c83"
secondaryBackgroundColor = "#1a1a2e"
borderColor = "#00a3e0"

</example>
"""

# Interface
st.title(":material/palette: AI Theme Generator")
st.write("Generate custom Streamlit themes using AI. Describe your desired look and let Cortex create a config.toml for you.")

with st.sidebar:
    st.header(":material/tune: Theme Settings")
    with st.form("theme_form"):
        base_color = st.selectbox(
            "Base color palette:",
            ["Blue", "Purple", "Green", "Orange", "Red", "Teal", "Monochrome"]
        )
        description = st.text_area(
            "Describe your theme:",
            placeholder="e.g., Modern and minimal, corporate professional, playful and colorful..."
        )
        creativity = st.slider("Creativity level:", 1, 10, 5)
        st.caption("Once you've generated a theme, try clicking Generate again to see the cache in action")
        submitted = st.form_submit_button("Generate Theme")

if submitted:
    validate_inputs(description)
    
    prompt = PROMPT_TEMPLATE.format(
        base_color=base_color,
        description=description,
        creativity=creativity
    )
    
    response_sent = time()
    response = generate_with_status(prompt)
    query_time = time() - response_sent

    with st.expander("View Prompt"):
        st.markdown(prompt)
    
    with st.container(border=True):
        st.subheader(":material/lightbulb: Design Thinking")
        st.info(response["thinking"])
        
        st.subheader(":material/code: Generated config.toml")
        st.code(response["config"], language="toml")
        st.caption(f"Generated in {query_time:.2f} seconds")
