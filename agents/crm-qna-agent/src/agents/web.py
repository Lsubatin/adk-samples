# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Agent streamlit web app"""

import asyncio
import importlib.util
from io import BytesIO
import logging
import os
import sys
from time import time
from typing import Optional
import uuid

import streamlit as st

from google.genai.types import Content, Part

from google.adk import Agent, Runner
from google.adk.events import Event
from google.adk.sessions import Session
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService

from PIL import Image


_root_agent: Optional[Agent] = None # Root Agent

logging.getLogger().setLevel(logging.INFO)

st.set_page_config(layout="wide",
                   page_icon=":material/bar_chart:",
                   page_title="Data Q&A Agent Demo")

st.title("Data Agent with Gemini and Google Agent Development Kit")
st.subheader("The agent has access to Salesforce.com CRM data.")
st.markdown("### Ask a question you would normally ask a CRM Business Analyst.")
st.markdown("""
* Top 5 customers in every country.
* What are our best lead sources?
* Lead conversion trends in the US.
""".strip())

hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {
    display:none !important;
}
.block-container {
    padding-top: 2rem;
    padding-bottom: 5rem;
    padding-left: 2rem;
    padding-right: 2rem;
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


@st.fragment
def _process_function_calls(function_calls):
  title = f"⚡ {', '.join([fc.name for fc in function_calls])}"
  with st.expander(title):
    for fc in function_calls:
      title = f'**{fc.name}**'
      if fc.id:
        title += f' ({fc.id})'
      st.write(title)
      st.write(fc.args)


@st.fragment
def _process_function_responses(function_responses):
  title = f"✔️ {', '.join([fr.name for fr in function_responses])}"
  with st.expander(title):
    for fr in function_responses:
      title = f'**{fr.name}**'
      if fr.id:
        title += f' ({fr.id})'
      st.write(title)
      st.write(fr.response)


def _process_event(event: Event):
    if not event:
        return
    session = get_session()
    artifact_service = st.session_state["artifact_service"]

    function_calls = []
    function_responses = []

    if event.content and event.content.parts:
        content = event.content
        for part in content.parts: # type: ignore
            if part.text and not part.text.strip():
                continue
            if part.thought and part.text:
                msg = '\n'.join('> %s' % f
                            for f in part.text.strip().split()) # type: ignore
            else:
                msg = part.text or ""
                msg = msg.strip()
            if part.function_call:
                function_calls.append(part.function_call)
            elif part.function_response:
                function_responses.append(part.function_response)
        if msg:
            if content.role == "model":
                msg_role = "ai"
            elif content.role == "user":
                msg_role = "human"
            else:
                msg_role = "assistant"
            with st.chat_message(msg_role):
                st.markdown(msg, unsafe_allow_html=True)

    if event.actions.artifact_delta:
        for filename, version in event.actions.artifact_delta.items():
            artifact = artifact_service.load_artifact(
                app_name=session.app_name, user_id=session.user_id,
                session_id=session.id, filename=filename, version=version
            )
            if artifact.inline_data:
                if artifact.inline_data.mime_type.startswith('image/'):
                    with BytesIO(artifact.inline_data.data) as image_io:
                        with Image.open(image_io) as img:
                            st.image(img)
            elif artifact.text:
                if filename.endswith(".json"):
                    st.markdown(f"```json\n{artifact.text}\n```", unsafe_allow_html=True)
                else:
                    st.markdown(artifact.text, unsafe_allow_html=True)

    if function_calls:
        _process_function_calls(function_calls)
    if function_responses:
        _process_function_responses(function_responses)


def _render_chat(events):
    if events is None:
        if "event_history" not in st.session_state:
            return
        events = st.session_state.event_history
    for event in events:
        _process_event(event)


async def ask_agent(question: str):
    start = time()
    session = get_session()
    content = Content(parts=[
        Part.from_text(text=question)
    ],role="user")

    user_event = Event(author="user", content=content)
    st.session_state["event_history"].append(user_event)
    _render_chat([user_event])

    events = get_agent_runner().run_async(user_id=session.user_id,
                                          session_id=session.id,
                                          new_message=content)
    async for event in events:
        st.session_state.event_history.append(event)
        _render_chat([event])
    end = time()
    st.text(f"Flow duration: {end - start:.2f}s")


def get_session() -> Session:
    if "adk_session" not in st.session_state:
        session = get_agent_runner().session_service.create_session(
                                      app_name="inventory_agent",
                                      user_id=uuid.uuid4().hex)
        st.session_state.event_history = []
        st.session_state.adk_session = session
    return st.session_state.adk_session


def get_root_agent() -> Agent:
    global _root_agent
    if _root_agent:
        return _root_agent
    root_files = [
        "__init__.py",
        "__main__.py",
        "agent.py",
        "main.py"
    ]
    module_name = "adk_root_agent_module"
    agent_dir = os.environ.get("AGENT_DIRECTORY", os.path.abspath("."))
    for file_name in root_files:
        spec = importlib.util.spec_from_file_location(module_name,
                            f"{agent_dir}/{file_name}")
        if spec:
            break
    module = importlib.util.module_from_spec(spec) # type: ignore
    sys.modules[module_name] = module
    spec.loader.exec_module(module) # type: ignore
    _root_agent = getattr(module, "root_agent")
    return _root_agent # type: ignore


def get_agent_runner()-> Runner:
    if "adk_runner" not in st.session_state:
        session_service = InMemorySessionService()
        artifact_service = InMemoryArtifactService()
        memory_service = InMemoryMemoryService()
        st.session_state["artifact_service"] = artifact_service
        runner = Runner(app_name="inventory_agent",
                        agent=get_root_agent(),
                        artifact_service=artifact_service,
                        session_service=session_service,
                        memory_service=memory_service)
        st.session_state["adk_runner"] = runner
    return st.session_state["adk_runner"]

async def app():
    #if "history" not in st.session_state:
    #    st.session_state.history = []
    # Display chat messages from history on app rerun
    # for message in st.session_state.history:
    #     if message["content_type"] == "message":
    #         role = message.get("role", "user")
    #         content = message["content"]
    #         with st.chat_message(role):
    #             st.markdown(content, unsafe_allow_html=True)
    #     else:
    #         _process_event(message["event"])

    top = st.container()
    with st.spinner("Thinking...", show_time=False):
        question = st.chat_input("Try \"Top 5 customers in every country\"")
        with top:
            # if question:
            #     with st.chat_message("user"):
            #         st.markdown(question, unsafe_allow_html=True)
            #         st.session_state.history.append({
            #             "content_type": "message",
            #             "role": "user",
            #             "content": question
            #         })
            with st.spinner("Thinking...", show_time=True):
                _render_chat(None)
                if question:
                    await ask_agent(question)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(app())

