import streamlit as st
import google.generativeai as genai
import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import requests
import random
import time

# ---- 유튜브 비디오 ID 추출 함수 ----
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

# ---- Youtube 자막 추출 (최대한 IP차단 우회) ----
class TimeoutSession(requests.Session):
    def __init__(self, timeout=15, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = timeout
    def request(self, method, url, **kwargs):
        kwargs.setdefault('timeout', self.timeout)
        return super().request(method, url, **kwargs)

def get_random_headers():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1'
    ]
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9,ko-KR;q=0.8,ko;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

def setup_custom_session():
    session = TimeoutSession(timeout=15)
    session.headers.update(get_random_headers())
    session.cookies.update({
        'CONSENT': 'YES+cb.20240101-17-p0.en+FX+000',
        'SOCS': 'CAI'
    })
    return session

def get_transcript(video_id):
    max_attempts = 5
    preferred_langs = ['ko', 'en']
    for attempt in range(max_attempts):
        try:
            if attempt > 0:
                delay = random.uniform(2, 5) * attempt
                st.info(f"🔄 재시도 {attempt + 1}/{max_attempts} (대기: {delay:.1f}초)")
                time.sleep(delay)
            custom_session = setup_custom_session()
            transcript_list_obj = YouTubeTranscriptApi.list_transcripts(video_id, http_client=custom_session)
            selected_transcript = None
            # 1. 우선: 한국어/영어 수동 자막
            for lang_code in preferred_langs:
                for t in transcript_list_obj:
                    if not t.is_generated and t.language_code == lang_code:
                        selected_transcript = t
                        break
                if selected_transcript:
                    break
            # 2. 우선: 한국어/영어 자동 자막
            if not selected_transcript:
                for lang_code in preferred_langs:
                    for t in transcript_list_obj:
                        if t.is_generated and t.language_code == lang_code:
                            selected_transcript = t
                            break
                    if selected_transcript:
                        break
            # 3. 기타 수동
            if not selected_transcript:
                for t in transcript_list_obj:
                    if not t.is_generated:
                        selected_transcript = t
                        break
            # 4. 기타 자동
            if not selected_transcript:
                for t in transcript_list_obj:
                    if t.is_generated:
                        selected_transcript = t
                        break
            # 자막 다운로드
            if selected_transcript:
                transcript_data = selected_transcript.fetch()
                full_text = ' '.join([item['text'] for item in transcript_data if 'text' in item])
                transcript_type = "수동 생성" if not selected_transcript.is_generated else "자동 생성"
                lang_info = f"{selected_transcript.language} ({selected_transcript.language_code})"
                return full_text, f"{transcript_type} - {lang_info}"
            else:
                return None, None
        except TranscriptsDisabled:
            return None, "이 비디오는 자막이 비활성화되어 있습니다."
        except NoTranscriptFound:
            return None, "자막을 찾을 수 없습니다."
        except requests.exceptions.RequestException as req_err:
            if attempt >= max_attempts - 1:
                err_msg = str(req_err)
                if "429" in err_msg or "forbidden" in err_msg or "403" in err_msg:
                    return None, "YouTube 서버가 Streamlit Cloud 등 공용 서버 IP를 차단했습니다. 몇 분~몇 시간 후 다시 시도하거나, Colab/로컬에서 직접 실행해보세요."
                return None, f"네트워크 오류: {err_msg[:100]}"
            continue
        except Exception as e:
            if attempt >= max_attempts - 1:
                return None, f"알 수 없는 오류: {str(e)[:100]}"
            continue
    return None, "모든 재시도 실패"

# ---- Gemini 요약 ----
def summarize_text(text, api_key):
    try:
        genai.configure(api_key=api_key)
        max_len = 100000
        if len(text) > max_len:
            text = text[:max_len]
            st.caption(f"자막이 매우 길어 앞부분 {max_len}자만 요약에 사용합니다.")
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
        if "API key not valid" in str(e):
            st.warning("Gemini API 키가 유효하지 않은 것 같습니다.")
        elif "quota" in str(e).lower():
            st.warning("Gemini API 사용 할당량을 초과했을 수 있습니다.")
        return f"요약 생성에 실패했습니다. 오류: {str(e)[:200]}"

# ---- Streamlit App ----
def main():
    st.set_page_config(page_title="YouTube 자막 AI 요약", page_icon="📺", layout="wide")
    st.title("📺 YouTube 자막 AI 요약기")
    st.caption("YouTube 비디오의 자막을 추출하고 Gemini AI로 요약합니다. (Streamlit Cloud에서 동작)")
    st.info("⚠️ 일부 영상은 YouTube 차단정책(IP Block) 때문에 실패할 수 있습니다. 실패시 Colab/로컬 환경을 권장합니다.")

    gemini_api_key = st.text_input("🔑 Gemini AI Studio API Key", type="password", help="Google AI Studio에서 발급받은 키 입력")
    video_url = st.text_input("🎥 YouTube URL 또는 비디오 ID", placeholder="예: https://www.youtube.com/watch?v=dQw4w9WgXcQ 또는 dQw4w9WgXcQ")

    if st.button("🚀 자막 추출 및 요약", type="primary", disabled=not (gemini_api_key and video_url)):
        with st.spinner("YouTube 자막 추출 중..."):
            video_id = extract_video_id(video_url)
            if not video_id:
                st.error("유효한 YouTube URL 또는 Video ID가 아닙니다.")
                st.stop()
            transcript_text, method = get_transcript(video_id)
        if not transcript_text:
            st.error(f"❌ 자막을 가져올 수 없습니다: {method}")
            st.info("**실패 원인 예시:**\n"
                    "- 영상에 자막이 없음\n"
                    "- 비공개/연령제한/멤버십 영상\n"
                    "- YouTube가 Streamlit Cloud 서버의 IP를 차단함(자주 발생)\n\n"
                    "💡 Colab/로컬 환경에서는 차단 가능성이 낮음")
            return
        st.success(f"✅ 자막 추출 성공! ({method})")
        with st.expander("📜 원본 자막 펼치기", expanded=True):
            st.text_area("자막 내용", transcript_text, height=300)
            st.download_button("📥 자막 다운로드 (.txt)", transcript_text, f"transcript_{video_id}.txt", mime="text/plain")
        with st.spinner("Gemini AI로 요약 생성 중..."):
            summary = summarize_text(transcript_text, gemini_api_key)
        st.markdown("### 🤖 Gemini AI 요약")
        st.markdown(summary, unsafe_allow_html=True)
        st.download_button("📥 요약 다운로드 (.md)", summary, f"summary_{video_id}.md", mime="text/markdown")

if __name__ == "__main__":
    main()
