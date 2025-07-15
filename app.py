import streamlit as st
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import os
from dotenv import load_dotenv


class AIFoundryAssistant:
    load_dotenv('keys.env')


    def __init__(self, openai_key, openai_endpoint, deployment_name, search_api_key, search_endpoint, index_name):
        self.client = AzureOpenAI(
            api_key=openai_key,
            api_version="2025-01-01-preview",
            azure_endpoint=openai_endpoint
        )
        self.deployment_name = deployment_name
        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(search_api_key)
        )
        self.default_search_cache = []
        self.cache_initialized = False

    def search_documents(self, query, top=5):
        try:
            results = self.search_client.search(search_text=query, top=top)
            formatted_results = []

            for result in results:
                snippet = []
                for key, value in result.items():
                    if not key.startswith('@') and isinstance(value, str) and value.strip():
                        snippet.append(f"{key}: {value}")
                if snippet:
                    formatted_results.append("\n".join(snippet))

            return formatted_results
        except Exception as e:
            st.error(f"Search error: {str(e)}")
            return []

    def initialize_default_cache(self):
        if not self.cache_initialized:
            self.default_search_cache = self.search_documents("Arehone", top=15)
            self.cache_initialized = True
            return len(self.default_search_cache)
        return len(self.default_search_cache)

    def get_search_results_with_fallback(self, user_query):
        search_results = []
        search_strategy = "direct"

        if user_query.strip():
            search_results = self.search_documents(user_query, top=8)

        if not search_results:
            enhanced_query = f"what could be {user_query} and Arehone"
            search_results = self.search_documents(enhanced_query, top=8)
            if search_results:
                search_strategy = "enhanced"

        if not search_results:
            if not self.cache_initialized:
                self.initialize_default_cache()
            search_results = self.default_search_cache
            search_strategy = "default"

        return search_results, search_strategy

    def get_response(self, user_input, search_results, search_strategy, history=[]):
        try:
            formatted_results = "\n\n".join(search_results) if search_results else "No information found."

            if search_strategy == "direct":
                system_prompt = f"""
You are Arehone's AI assistant helping employers and recruiters learn about Arehone Matodzi.

Below are retrieved facts and background about Arehone based on their professional documents. Use them to answer the user's question clearly, concisely, and informatively.

Knowledge Base:
{formatted_results}

User Question: "{user_input}"
"""
            elif search_strategy == "enhanced":
                system_prompt = f"""
You are Arehone's AI assistant. Based on the enhanced search combining the user question and Arehone's profile, here’s what we found.

Data:
{formatted_results}

User Question: "{user_input}"
"""
            else:
                system_prompt = f"""
The user asked about "{user_input}", but no exact matches were found. Here's what we know about Arehone Matodzi in general:

General Profile:
{formatted_results}
"""

            contact_info = """
---
📞 **Want to connect directly with Arehone?**
- LinkedIn: https://www.linkedin.com/in/arehone-matodzi-766ab0210/
- Email: arehonematodzi456@gmail.com
- Phone: 0739298456
"""

            messages = [
                {"role": "system", "content": system_prompt.strip() + contact_info},
                *history[-10:],  # keep context
                {"role": "user", "content": user_input}
            ]

            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                temperature=1,

            )

            return response.choices[0].message.content

        except Exception as e:
            return f"""⚠️ Error: {str(e)}

You can reach out to Arehone directly:
- LinkedIn: https://www.linkedin.com/in/arehone-matodzi-766ab0210/
- Email: arehonematodzi456@gmail.com
- Phone: 0739298456
"""


def main():
    st.set_page_config(page_title="Arehone's AI Assistant", layout="wide", page_icon="🤖")

    st.markdown("""
    <style>
    .thinking-box {
        background-color: #f0f8ff;
        border-left: 4px solid #4CAF50;
        padding: 10px;
        margin: 10px 0;
        border-radius: 5px;
    }
    .strategy-info {
        font-size: 0.8em;
        color: #666;
        font-style: italic;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("🤖 Arehone's AI Assistant")
    st.markdown("*Get to know Arehone Matodzi - Your potential next hire!*")

    load_dotenv('keys.env')

    # Get environment variables
    OPENAI_KEY = os.getenv("OPENAI_KEY")
    OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
    DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")
    SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")
    SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT")
    INDEX_NAME = os.getenv("INDEX_NAME")

    # Init Assistant
    if "assistant" not in st.session_state:
        st.session_state.assistant = AIFoundryAssistant(
            openai_key=OPENAI_KEY,
            openai_endpoint=OPENAI_ENDPOINT,
            deployment_name=DEPLOYMENT_NAME,
            search_api_key=SEARCH_API_KEY,
            search_endpoint=SEARCH_ENDPOINT,
            index_name=INDEX_NAME
        )

    assistant = st.session_state.assistant

    if "messages" not in st.session_state:
        st.session_state.messages = []
        welcome_msg = """👋 **Welcome! I'm Arehone's AI Assistant.**

I'm here to help you learn about Arehone Matodzi's skills, experience, and background.

**Try asking me about:**
- Technical skills and experience
- Project portfolio
- Educational background
- Work history
- Specific technologies or tools
- Anything else you'd like to know!

*What would you like to know about Arehone?*"""
        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Ask me anything about Arehone...")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            thinking_placeholder = st.empty()
            with thinking_placeholder.container():
                st.markdown('<div class="thinking-box">🤔 <strong>Thinking...</strong> Searching for information...</div>', unsafe_allow_html=True)

            search_results, search_strategy = assistant.get_search_results_with_fallback(user_input)

            strategy_messages = {
                "direct": "✅ Found specific information in knowledge base",
                "enhanced": "🔍 Using enhanced search strategy",
                "default": "📚 Using general knowledge about Arehone"
            }

            with thinking_placeholder.container():
                st.markdown(f'<div class="thinking-box">🤔 <strong>Processing...</strong> {strategy_messages.get(search_strategy)}</div>', unsafe_allow_html=True)

            reply = assistant.get_response(user_input, search_results, search_strategy, history=st.session_state.messages[:-1])

            thinking_placeholder.empty()
            st.markdown(reply)
            st.markdown(f'<p class="strategy-info">Response generated using {search_strategy} search strategy</p>', unsafe_allow_html=True)

            st.session_state.messages.append({"role": "assistant", "content": reply})

    # Sidebar
    with st.sidebar:
        st.header("📊 System Status")

        if assistant.cache_initialized:
            st.success(f"✅ Knowledge base ready ({len(assistant.default_search_cache)} documents)")
        else:
            st.info("💡 Knowledge base will initialize when needed")

        st.header("🔍 How I Work")
        st.write("""
**Search Strategy:**
1. Direct Search
2. Enhanced Fallback
3. Cached Knowledge

**Always Available:**
- RAG + LLM responses
- Direct Arehone contact info
""")

        if st.button("🔄 Pre-load Knowledge Base"):
            with st.spinner("Loading knowledge base..."):
                cache_size = assistant.initialize_default_cache()
                st.success(f"✅ Loaded {cache_size} documents")

        st.header("📞 Contact")
        st.markdown("""
- [LinkedIn](https://www.linkedin.com/in/arehone-matodzi-766ab0210/)
- [Email](mailto:arehonematodzi456@gmail.com)
- Phone: 0739298456
""")

        st.header("💬 Chat Stats")
        st.metric("Messages", len(st.session_state.messages))

        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()


if __name__ == "__main__":
    main()

