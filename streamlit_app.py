import streamlit as st
import google.generativeai as genai
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import re
from urllib.parse import urlparse, parse_qs

# 유튜브 비디오 ID 추출 함수
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

# 자막 추출 함수 (구버전/신버전 모두 지원)
def get_transcript(video_id):
    preferred_langs = ['ko', 'en']
    try:
        # 인스턴스 메서드 우선 시도 (구버전 지원)
        ytt_api = YouTubeTranscriptApi()
        if hasattr(ytt_api, "list"):
            transcript_list = ytt_api.list(video_id)
        else:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    except Exception as e:
        return None, f"자막 추출 실패: {str(e)}"

    selected_transcript = None
    # 수동 한글/영어
    for lang in preferred_langs:
        for t in transcript_list:
            if not t.is_generated and t.language_code == lang:
                selected_transcript = t
                break
        if selected_transcript:
            break
    # 자동 한글/영어
    if not selected_transcript:
        for lang in preferred_langs:
            for t in transcript_list:
                if t.is_generated and t.language_code == lang:
                    selected_transcript = t
                    break
            if selected_transcript:
                break
    # 기타 수동
    if not selected_transcript:
        for t in transcript_list:
            if not t.is_generated:
                selected_transcript = t
                break
    # 기타 자동
    if not selected_transcript:
        for t in transcript_list:
            if t.is_generated:
                selected_transcript = t
                break

    if selected_transcript:
        try:
            transcript_data = selected_transcript.fetch()
            text = ' '.join([item['text'] for item in transcript_data if 'text' in item])
            transcript_type = "수동 생성" if not selected_transcript.is_generated else "자동 생성"
            lang_info = f"{selected_transcript.language} ({selected_transcript.language_code})"
            return text, f"{transcript_type} - {lang_info}"
        except Exception as e:
            return None, f"자막 fetch 실패: {str(e)}"
    else:
        # 사용 가능한 자막 목록 안내
        langlist = [f"{t.language} ({t.language_code}, {'수동' if not t.is_generated else '자동'})"
                    for t in transcript_list]
        return None, f"우선순위에 맞는 자막을 찾을 수 없습니다. 전체: {', '.join(langlist)}"

# Gemini 요약 함수
def summarize_text(text, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"""다음 YouTube 자막을 한국어로 상세히 요약해주세요. 요약에는 다음 요소들이 포함되어야 합니다:

1.  **📌 주요 주제 및 목적**: 이 영상이 무엇에 관한 내용인지, 주요 메시지는 무엇인지 설명합니다.
2.  **🔑 핵심 내용**: 영상에서 다루는 주요 정보, 주장, 논점들을 3-7개의 불릿 포인트로 정리합니다. 각 포인트는 구체적인 내용을 포함해야 합니다.
3.  **💡 결론 및 시사점**: 영상의 결론은 무엇이며, 시청자에게 어떤 생각할 거리나 교훈을 주는지 설명합니다. 가능하다면 영상에서 제시된 제안이나 전망도 포함합니다.
4.  **🗣️ 어조 및 스타일**: 영상의 전반적인 분위기나 전달 스타일 (예: 정보 제공, 설득, 비판, 유머 등)에 대해 간략히 언급합니다.

---
자막 내용:
{text}
---

위 형식에 맞춰 한국어로 명확하고 간결하게, 하지만 충분한 정보를 담아 작성해주세요."""
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"요약 생성 실패: {str(e)}"

def main():
    st.set_page_config(page_title="YouTube 자막 AI 요약", page_icon="📺")
    st.title("📺 SnapTube : 자막추출 AI 요약기")
    st.caption("YouTube 주소를 입력하면 자막+요약을 바로 확인 (AI Studio API Key 필요)")

    api_key = st.text_input("🔑 Gemini AI Studio API Key", type="password")
    url = st.text_input("🎥 YouTube URL 또는 비디오 ID", placeholder="예: https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    if st.button("🚀 자막 추출 및 요약", disabled=not (api_key and url)):
        video_id = extract_video_id(url)
        if not video_id:
            st.error("유효한 YouTube URL 또는 Video ID가 아닙니다.")
            st.stop()

        with st.spinner("유튜브 자막 추출 중..."):
            try:
                transcript, method = get_transcript(video_id)
            except TranscriptsDisabled:
                st.error("이 비디오는 자막이 비활성화되어 있습니다.")
                st.stop()
            except NoTranscriptFound:
                st.error("이 비디오에는 자막이 없습니다.")
                st.stop()

        if not transcript:
            st.error(f"자막 추출 실패: {method}")
            st.info("가능한 원인:\n"
                    "- 비공개/연령제한/멤버십 영상\n"
                    "- 자막 없음\n"
                    "- 네트워크/버전 이슈\n"
                    "Cloud에서 빈번한 경우 Colab/로컬에서 실행 권장")
            return

        st.success(f"✅ 자막 추출 성공! ({method})")
        with st.expander("📜 원본 자막 펼치기", expanded=True):
            st.text_area("자막 내용", transcript, height=300)
            st.download_button("📥 자막 다운로드 (.txt)", transcript, f"transcript_{video_id}.txt", mime="text/plain")

        with st.spinner("Gemini AI로 요약 생성 중..."):
            summary = summarize_text(transcript, api_key)
        st.markdown("### 🤖 Gemini AI 요약")
        st.markdown(summary, unsafe_allow_html=True)
        st.download_button("📥 요약 다운로드 (.md)", summary, f"summary_{video_id}.md", mime="text/markdown")

if __name__ == "__main__":
    main()
