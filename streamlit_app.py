import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from google import genai
from google.genai import types
import re
from urllib.parse import urlparse, parse_qs

# 유튜브 비디오 ID 추출 함수 (최적화)
def extract_video_id(url):
    if not url:
        return None
    url = url.strip()
    if "youtube.com/watch" in url:
        try:
            parsed_url = urlparse(url)
            return parse_qs(parsed_url.query)['v'][0]
        except (KeyError, IndexError):
            return None
    elif "youtu.be/" in url:
        try:
            return url.split("youtu.be/")[1].split("?")[0]
        except IndexError:
            return None
    elif "youtube.com/embed/" in url:
        try:
            return url.split("embed/")[1].split("?")[0]
        except IndexError:
            return None
    elif re.fullmatch(r"^[a-zA-Z0-9_-]{11}$", url):
        return url
    else:
        return None

# 자막 추출 (is_generated==0 수동만)
def get_manual_transcript(video_id):
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
    except TranscriptsDisabled:
        return None, "이 비디오는 자막이 비활성화되어 있습니다."
    except NoTranscriptFound:
        return None, "이 비디오에는 자막이 없습니다."
    except Exception as e:
        return None, f"자막 추출 실패: {str(e)}"

    for transcript in transcript_list:
        if transcript.is_generated == 0:
            try:
                fetched = transcript.fetch()
                output = ''.join([f['text'] for f in fetched if 'text' in f])
                return output, f"{transcript.language} ({transcript.language_code}) - 수동 생성"
            except Exception as e:
                return None, f"자막 fetch 실패: {str(e)}"
    return None, "수동 생성 자막(is_generated==0)이 없습니다."

# Gemini 2.5 Flash 요약 (Streaming)
def summarize_stream(text, api_key):
    client = genai.Client(api_key=api_key)
    model = "gemini-2.5-flash-preview-05-20"
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=f"Summarize and Write the good readability Report with numberings of text below in their language as Markdown.\n{text}"
                ),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        system_instruction='You are a Professional writer.',
        temperature=0.1
    )

    summary = ""
    try:
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if hasattr(chunk, 'text') and chunk.text:
                summary += chunk.text
                yield chunk.text
    except Exception as e:
        yield f"\n요약 생성 실패: {str(e)}"

def main():
    st.set_page_config(page_title="YouTube 자막 AI 요약기 (Gemini 2.5)", page_icon="📺")
    st.title("📺 SnapTube : 수동 자막 AI 요약기 (Gemini 2.5 Flash)")
    st.caption("AI Studio API Key와 YouTube 주소/ID를 입력하면 수동 생성 자막만 추출하여 Gemini 2.5로 Markdown 요약을 보여줍니다.")

    api_key = st.text_input("🔑 Gemini AI Studio API Key", type="password")
    url = st.text_input("🎥 YouTube URL 또는 Video ID", placeholder="예: https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    if st.button("🚀 자막 추출 및 요약", disabled=not (api_key and url)):
        video_id = extract_video_id(url)
        if not video_id:
            st.error("유효한 YouTube URL 또는 Video ID가 아닙니다.")
            st.stop()

        with st.spinner("유튜브 수동 자막 추출 중..."):
            transcript_text, method = get_manual_transcript(video_id)

        if not transcript_text:
            st.error(f"자막 추출 실패: {method}")
            st.info("가능한 원인:\n"
                    "- 수동 생성 자막 없음 (is_generated==0)\n"
                    "- 비공개/연령제한/멤버십 영상\n"
                    "- 네트워크/버전 문제")
            return

        st.success(f"✅ 자막 추출 성공! ({method})")
        with st.expander("📜 원본 자막 펼치기", expanded=True):
            st.text_area("자막 내용", transcript_text, height=300)
            st.download_button("📥 자막 다운로드 (.txt)", transcript_text, f"transcript_{video_id}.txt", mime="text/plain")

        st.markdown("### 🤖 Gemini 2.5 요약 (Markdown, Streaming)")
        summary_placeholder = st.empty()
        markdown_output = ""
        with st.spinner("Gemini 2.5로 요약 생성 중 (Streaming)..."):
            for chunk in summarize_stream(transcript_text, api_key):
                markdown_output += chunk
                summary_placeholder.markdown(markdown_output, unsafe_allow_html=True)
        st.success("✅ 요약 생성 완료!")
        st.download_button("📥 요약 다운로드 (.md)", markdown_output, f"summary_{video_id}.md", mime="text/markdown")

if __name__ == "__main__":
    main()
