"""
YouTube Transcript Summarizer – Streamlit Cloud App
--------------------------------------------------
This app lets a user
1. Paste **any YouTube URL**.
2. Supply their **Google AI Studio (Generative AI) API key**.
3. Click **Summarize** to automatically
   * extract the *video_id* from the URL,
   * fetch the open‑captions transcript, and
   * generate a concise Markdown summary using a Gemini model.

Deploy this single file on **Streamlit Cloud** together with a
`requirements.txt` containing:
    streamlit
    youtube-transcript-api
    google-generativeai

Author: Adapted from *Youtube_Contents_Summary.ipynb* (2025‑05‑24)
"""

from __future__ import annotations

import os
import re
import textwrap
import urllib.parse as urlparse
from typing import List

import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled

from google import genai

###########################################################################
# ------------------------------- UI ------------------------------------ #
###########################################################################

st.set_page_config(
    page_title="YouTube Transcript Summarizer",
    page_icon="🎬",
    layout="centered",
)

# --- Sidebar (API key input & instructions) -----------------------------
with st.sidebar:
    st.title("🔑 Google AI Studio API Key")
    api_key = st.text_input(
        "Enter your API key", type="password", placeholder="AIza…"
    )
    st.markdown(
        """Get one at **[Google AI Studio → API keys](https://aistudio.google.com/app/apikey)**.""",
        help="The key never leaves your browser – it is only sent to Google’s API.",
    )
    st.divider()
    st.caption("Made with Streamlit • YouTube Transcript API • Gemini ✨")

# --- Main content --------------------------------------------------------

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
        # /embed/{id} or /shorts/{id}
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
    transcript: List[dict] = YouTubeTranscriptApi.get_transcript(
        video_id,
        languages=["ko", "en", "en-US", "en-GB"],
    )
    return " ".join(chunk["text"] for chunk in transcript)

@st.cache_resource(show_spinner=False)
def summarize(text: str, api_key: str) -> str:
    """Summarise *text* using Gemini and return Markdown output."""
  
    client = genai.Client(
        api_key=api_key,
    )

    model = "gemini-2.5-flash-preview-05-20"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=f'Summarize and Write the good readability Report with numberings of text below in their language as Markdown.\n {text}'),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        system_instruction='You are a Professioal writer.',
        temperature=0.1
    )

    # Gemini can handle ~1 M tokens, but we keep prompts below 30k chars
    CHUNK = 15000
    if len(text) <= CHUNK:
        prompt = _build_prompt(text)
        return model.generate_content(prompt).text

    # Long transcripts → chunk summarisation, then hierarchical summarisation
    partial_summaries: List[str] = []
    for i in range(0, len(text), CHUNK):
        part = text[i : i + CHUNK]
        prompt = _build_prompt(part)
        partial = model.generate_content(prompt).text
        partial_summaries.append(partial)

    # Second‑pass summary
    second_prompt = _build_prompt("\n\n".join(partial_summaries))
    return model.generate_content(second_prompt).text

def _build_prompt(transcript_chunk: str) -> str:
    """Return a language‑agnostic prompt for Gemini."""
    return textwrap.dedent(
        f"""
        You are a world‑class note‑taker.
        Summarise the following YouTube transcript as **concise bullet points** in the transcript’s original language.
        Capture all key ideas, numbers, and speaker arguments. Use Markdown.
        Transcript:
        {transcript_chunk}
        """
    ).strip()

###########################################################################
# --------------------------- Action logic ------------------------------- #
###########################################################################

if start_button:
    if not api_key:
        st.error("Please provide your Google AI Studio API key in the sidebar.")
        st.stop()

    if not video_url:
        st.error("Please paste a YouTube URL to continue.")
        st.stop()

    with st.spinner("Extracting video ID …"):
        vid = extract_video_id(video_url)
    if not vid:
        st.error("❌ Unable to extract a valid video ID from the URL.")
        st.stop()

    st.success(f"Video ID: `{vid}`")

    # ------------------ Transcript retrieval --------------------------- #
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

    with st.expander("Raw transcript"):
        st.write(transcript_text)

    # ------------------ Summarisation --------------------------------- #
    with st.spinner("Generating summary with Gemini …"):
        try:
            summary_md = summarize(transcript_text, api_key)
        except Exception as exc:
            st.error(f"Gemini error: {exc}")
            st.stop()

    st.markdown("### 🔍 Summary")
    st.markdown(summary_md)

    st.toast("Done! ✨", icon="🎉")
