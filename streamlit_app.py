"""
YouTube Transcript Summarizer – Streamlit Cloud App
--------------------------------------------------
This app lets a user
1. Paste **any YouTube URL**.
2. Supply their **Google AI Studio (Generative AI) API key**.
3. Click **Summarize** to automatically
   * extract the *video_id* from the URL,
   * fetch the open-captions transcript, and
   * generate a concise Markdown summary using a Gemini model.

Deploy this single file on **Streamlit Cloud** together with a
`requirements.txt` containing:
    streamlit
    youtube-transcript-api
    google-generativeai

Author: Adapted 2025-05-24
"""

from __future__ import annotations

# ---------------------------- Standard libs -----------------------------
import os
import re
import urllib.parse as urlparse
from typing import List

# ---------------------------- Third-party -------------------------------
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from youtube_transcript_api.proxies import WebshareProxyConfig

# Google Generative AI SDK
from google import genai
from google.genai import types

###########################################################################
# ------------------------------- UI ------------------------------------ #
###########################################################################

st.set_page_config(
    page_title="YouTube Transcript Summarizer",
    page_icon="🎬",
    layout="centered",
)

with st.sidebar:
    st.title("🔑 Google AI Studio API Key")
    api_key = st.text_input(
        "Enter your API key", type="password", placeholder="AIza…"
    )
    st.markdown(
        """Get one at **[Google AI Studio → API keys](https://aistudio.google.com/app/apikey)**.""",
        help="The key never leaves your browser – it is only sent to Google’s API.",
    )
    st.divider()
    st.caption("Made with Streamlit • YouTube Transcript API • Gemini ✨")

st.title("🎞️ YouTube Transcript Summarizer")

video_url: str | None = st.text_input(
    "Paste a YouTube video URL",
    placeholder="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
)

start_button = st.button("📑 Summarize", type="primary")

###########################################################################
# ----------------------------- Utilities -------------------------------- #
###########################################################################

def extract_video_id(url: str) -> str | None:
    """Return the YouTube *video_id* from a full / short / embed URL."""
    parsed = urlparse.urlparse(url.strip())

    # youtube.com or www.youtube.com
    if parsed.hostname and "youtube.com" in parsed.hostname:
        query = urlparse.parse_qs(parsed.query)
        if "v" in query:
            return query["v"][0]
        match = re.match(r"/(embed|shorts)/([\w-]{11})", parsed.path)
        if match:
            return match.group(2)

    # youtu.be/{id}
    if parsed.hostname and parsed.hostname.endswith("youtu.be"):
        return parsed.path.lstrip("/")
    return None

@st.cache_data(show_spinner=False)
def fetch_transcript(video_id: str) -> str:
    """Download transcript text for *video_id* and return as a single string."""
    # transcript: List[dict] = YouTubeTranscriptApi.get_transcript(
    #     video_id,
    #     languages=["ko", "en"],
    # )
      
    ytt_api = YouTubeTranscriptApi(
        proxy_config=WebshareProxyConfig(
            proxy_username="rdgbjthx",
            proxy_password="4b4dux3d9pkc",
        )
    )
    
    # all requests done by ytt_api will now be proxied through Webshare
    transcript = ytt_api.fetch(video_id)
  
    return " ".join(chunk["text"] for chunk in transcript)

# ----------------------------------------------------------------------- #
# NOTE ▸ The *user explicitly requested* the following summarize() be used
#        exactly. We wrap it unchanged except for adding the api_key param
#        the Streamlit app passes in.
# ----------------------------------------------------------------------- #

def summarize(text: str, api_key: str) -> str:
    """Generate a Markdown summary of *text* using Gemini 2.5 Flash."""
    # — keep the body as-is per user instruction —
    client = genai.Client(api_key=api_key)

    model = "gemini-2.5-flash-preview-05-20"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=(
                        "Summarize and Write the good readability Report "
                        "with numberings of text below in their language as Markdown.\n"
                        f"{text}"
                    )
                ),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        system_instruction="You are a Professional writer.",
        temperature=0.1,
    )

    # Collect streamed chunks
    output: List[str] = []
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if chunk.text:
            output.append(chunk.text)
    return "".join(output)

###########################################################################
# --------------------------- Action logic ------------------------------- #
###########################################################################

if start_button:
    # ------ Basic validation ------------------------------------------ #
    if not api_key:
        st.error("Please provide your Google AI Studio API key in the sidebar.")
        st.stop()
    if not video_url:
        st.error("Please paste a YouTube URL to continue.")
        st.stop()

    # ------ Extract video ID ------------------------------------------ #
    with st.spinner("Extracting video ID …"):
        vid = extract_video_id(video_url)
    if not vid:
        st.error("❌ Unable to extract a valid video ID from the URL.")
        st.stop()
    st.success(f"Video ID: `{vid}`")

    # ------ Fetch transcript ------------------------------------------ #
    with st.spinner("Fetching transcript from YouTube …"):
        try:
            transcript_text = fetch_transcript(vid)
        except TranscriptsDisabled:
            st.error("Transcripts are disabled for this video.")
            st.stop()
        except Exception as exc:
            st.error(f"Unable to retrieve transcript: {exc}")
            st.stop()
    st.success(f"Retrieved {len(transcript_text):,} characters of transcript.")
    # ------ 요약 결과를 왼쪽과 오른쪽 열에 표시 ---------------------------------- #
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📜 Raw Transcript")
        st.write(transcript_text)

    with col2:
        # ------ Summarise -------------------------------------------------- #
        with st.spinner("Generating summary with Gemini …"):
            try:
                summary_md = summarize(transcript_text, api_key)
            except Exception as exc:
                st.error(f"Gemini error: {exc}")
                st.stop()
        st.markdown("### 🔍 Summary")
        st.markdown(summary_md)

    st.toast("Done! ✨", icon="🎉")
