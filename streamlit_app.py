import streamlit as st
import google.generativeai as genai
import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

def extract_video_id(url):
    """YouTube URL에서 비디오 ID 추출"""
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

def get_transcript(video_id):
    """자막 가져오기: 수동 생성 우선, 차선으로 자동 생성"""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # 1. 수동 생성 자막 찾기 (언어 상관없이)
        for transcript in transcript_list:
            if not transcript.is_generated:
                fetched_transcript = transcript.fetch()
                text = ' '.join([item['text'] for item in fetched_transcript])
                st.caption(f"수동 생성 자막 발견 ({transcript.language_code})")
                return text, f"수동 생성 ({transcript.language_code})"
        
        # 2. 자동 생성 자막 찾기 (언어 상관없이)
        for transcript in transcript_list:
            if transcript.is_generated:
                fetched_transcript = transcript.fetch()
                text = ' '.join([item['text'] for item in fetched_transcript])
                st.caption(f"자동 생성 자막 발견 ({transcript.language_code})")
                return text, f"자동 생성 ({transcript.language_code})"
                
    except TranscriptsDisabled:
        st.warning("자막이 비활성화되어 있습니다.")
        return None, None
    except NoTranscriptFound:
        st.warning("자막을 찾을 수 없습니다.")
        return None, None
    except Exception as e:
        st.error(f"자막 추출 중 오류: {e}")
        return None, None
    
    return None, None

def summarize_text(text, api_key):
    """Gemini로 요약 생성"""
    try:
        genai.configure(api_key=api_key)
        
        # 텍스트가 너무 길면 앞부분만 사용
        if len(text) > 30000:
            text = text[:30000]
            st.caption("자막이 너무 길어 앞부분만 요약에 사용합니다.")
        
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        prompt = f"""다음 YouTube 자막을 한국어로 요약해주세요:

자막 내용:
{text}

요약 형식:
## 📌 주요 주제
## 🔑 핵심 내용 (3-5개)
## 💡 결론 및 시사점

한국어로 명확하고 간결하게 작성해주세요."""
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        st.error(f"요약 생성 중 오류: {e}")
        return f"요약 생성 실패: {e}"

def main():
    st.set_page_config(
        page_title="YouTube 자막 요약기",
        page_icon="📺",
        layout="wide"
    )
    
    st.title("📺 YouTube 자막 요약기")
    st.markdown("YouTube 비디오의 자막을 추출하고 Gemini AI로 요약합니다.")
    
    # API 키 입력
    gemini_api_key = st.text_input(
        "🔑 Gemini API Key",
        type="password",
        help="Google AI Studio에서 발급받은 API 키를 입력하세요."
    )
    
    if gemini_api_key:
        st.success("API 키가 입력되었습니다.")
    
    # YouTube URL 입력
    video_input = st.text_input(
        "🎥 YouTube URL 또는 비디오 ID",
        placeholder="예: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )
    
    if st.button("🚀 자막 추출 및 요약", type="primary", disabled=(not gemini_api_key)):
        if not video_input:
            st.error("YouTube URL을 입력해주세요!")
            return
        
        video_id = extract_video_id(video_input)
        if not video_id:
            st.error("유효한 YouTube URL이 아닙니다.")
            return
            
        st.info(f"비디오 ID: {video_id}")
        
        # 자막 추출
        with st.spinner("자막 추출 중..."):
            transcript_text, method = get_transcript(video_id)
        
        if not transcript_text:
            st.error("자막을 가져올 수 없습니다. 자막이 있는 다른 비디오를 시도해보세요.")
            return
        
        st.success(f"자막 추출 성공! ({method})")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📜 원본 자막")
            st.text_area("자막 내용", transcript_text, height=400)
            st.download_button(
                "📥 자막 다운로드",
                transcript_text,
                f"transcript_{video_id}.txt",
                mime="text/plain"
            )
        
        with col2:
            st.markdown("### 🤖 AI 요약")
            with st.spinner("요약 생성 중..."):
                summary = summarize_text(transcript_text, gemini_api_key)
            
            st.markdown(summary)
            st.download_button(
                "📥 요약 다운로드",
                summary,
                f"summary_{video_id}.md",
                mime="text/markdown"
            )

if __name__ == "__main__":
    main()
