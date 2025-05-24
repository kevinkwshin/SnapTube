import streamlit as st
import google.generativeai as genai
import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import requests
import random
import time

# TimeoutSession class (as defined in the previous good answer)
class TimeoutSession(requests.Session):
    def __init__(self, timeout=15, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = timeout

    def request(self, method, url, **kwargs):
        kwargs.setdefault('timeout', self.timeout)
        return super().request(method, url, **kwargs)

# extract_video_id, get_random_headers, setup_custom_session (as defined previously)
# ...
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
    elif re.fullmatch(r"^[a-zA-Z0-9_-]{11}$", url): # Checks if the input itself is a valid video ID
        return url
    else:
        return None

def get_random_headers():
    """랜덤 User-Agent 헤더 생성"""
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
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'TE': 'trailers'
    }

def setup_custom_session():
    """프록시와 헤더를 설정한 세션 생성 (TimeoutSession 사용)"""
    session = TimeoutSession(timeout=15) 
    session.headers.update(get_random_headers())
    session.cookies.update({
        'CONSENT': 'YES+cb.20240101-17-p0.en+FX+000', 
        'SOCS': 'CAI', 
    })
    return session

# MODIFIED get_transcript function
def get_transcript(video_id):
    """YouTube Transcript API로 자막 가져오기 - 명시적 반복 및 is_generated 확인 사용"""
    max_attempts = 5
    preferred_langs = ['ko', 'en']  # 선호 언어 순서 (한국어, 영어)

    for attempt in range(max_attempts):
        try:
            if attempt > 0:
                delay = random.uniform(2, 5) * attempt
                st.info(f"🔄 재시도 {attempt + 1}/{max_attempts} (대기: {delay:.1f}초)")
                time.sleep(delay)

            st.info(f"🛠️ 새로운 연결 설정 중... (시도 {attempt + 1})")
            custom_session = setup_custom_session()

            st.info("📋 자막 목록 조회 중...")
            # YouTubeTranscriptApi.list_transcripts는 video_id에 대한 모든 Transcript 객체 목록을 반환
            transcript_list_obj = YouTubeTranscriptApi.list_transcripts(video_id, http_client=custom_session)
            
            # transcript_list_obj는 TranscriptList 객체이며, 이를 반복하여 개별 Transcript 객체에 접근 가능
            # 또는 transcript_list_obj.find_manually_created_transcript 등 사용 가능
            # 여기서는 사용자 요청에 따라 명시적으로 반복하겠습니다.

            selected_transcript = None
            
            # 우선 순위:
            # 1. 수동 생성, 선호 언어 (ko, en 순)
            # 2. 자동 생성, 선호 언어 (ko, en 순)
            # 3. 수동 생성, 기타 언어 (목록에서 처음 발견되는 것)
            # 4. 자동 생성, 기타 언어 (목록에서 처음 발견되는 것)

            # 1단계: 수동 생성, 선호 언어
            st.info(f"🔍 1단계: 선호 언어({', '.join(preferred_langs)})의 '수동 생성' 자막 검색...")
            for lang_code in preferred_langs:
                for t in transcript_list_obj: # TranscriptList 객체를 직접 순회
                    if not t.is_generated and t.language_code == lang_code:
                        selected_transcript = t
                        st.info(f"✔️ '수동 생성' 선호 자막 ({t.language_code}) 발견!")
                        break
                if selected_transcript:
                    break
            
            # 2단계: 자동 생성, 선호 언어
            if not selected_transcript:
                st.info(f"🔍 2단계: 선호 언어({', '.join(preferred_langs)})의 '자동 생성' 자막 검색...")
                for lang_code in preferred_langs:
                    for t in transcript_list_obj:
                        if t.is_generated and t.language_code == lang_code:
                            selected_transcript = t
                            st.info(f"✔️ '자동 생성' 선호 자막 ({t.language_code}) 발견!")
                            break
                    if selected_transcript:
                        break

            # 3단계: 수동 생성, 기타 언어
            if not selected_transcript:
                st.info("🔍 3단계: 사용 가능한 다른 '수동 생성' 자막 검색...")
                for t in transcript_list_obj:
                    if not t.is_generated:
                        selected_transcript = t
                        st.info(f"✔️ 기타 '수동 생성' 자막 ({t.language_code}) 발견!")
                        break
            
            # 4단계: 자동 생성, 기타 언어
            if not selected_transcript:
                st.info("🔍 4단계: 사용 가능한 다른 '자동 생성' 자막 검색...")
                for t in transcript_list_obj:
                    if t.is_generated:
                        selected_transcript = t
                        st.info(f"✔️ 기타 '자동 생성' 자막 ({t.language_code}) 발견!")
                        break

            if selected_transcript:
                st.info(f"⬇️ '{selected_transcript.language} ({selected_transcript.language_code})' 자막 내용 다운로드 중...")
                # selected_transcript는 Transcript 객체이므로 .fetch() 메서드를 가짐
                # list_transcripts에 http_client를 전달했으므로 fetch 시에도 해당 클라이언트 사용됨
                transcript_data = selected_transcript.fetch()

                if not transcript_data or len(transcript_data) == 0:
                    if attempt < max_attempts - 1:
                        st.warning("빈 자막 데이터 - 재시도 중...")
                        continue
                    else:
                        st.error("❌ 자막 데이터가 비어있습니다.")
                        return None, None

                full_text = ' '.join([item['text'] for item in transcript_data if 'text' in item])

                if not full_text or len(full_text.strip()) < 10:
                    if attempt < max_attempts - 1:
                        st.warning("자막 텍스트가 너무 짧거나 유효하지 않음 - 재시도 중...")
                        continue
                    else:
                        st.error("❌ 유효한 자막 텍스트를 찾을 수 없습니다.")
                        return None, None

                transcript_type = "수동 생성" if not selected_transcript.is_generated else "자동 생성"
                lang_info = f"{selected_transcript.language} ({selected_transcript.language_code})"

                st.success(f"✅ 자막 다운로드 성공! (시도 {attempt + 1}회)")
                return full_text, f"{transcript_type} - {lang_info}"
            else:
                # transcript_list_obj 자체는 있었으나 조건에 맞는 자막이 없는 경우
                st.error("❌ 우선순위에 맞는 자막을 찾을 수 없습니다.")
                available_transcripts_info = []
                for t_obj in transcript_list_obj:
                     available_transcripts_info.append(
                         f"{t_obj.language} ({t_obj.language_code}, {'수동' if not t_obj.is_generated else '자동'})"
                     )
                if available_transcripts_info:
                    st.info(f"사용 가능한 전체 자막 목록: {', '.join(available_transcripts_info)}")
                else:
                     # 이 경우는 NoTranscriptFound 예외에서 처리되어야 하지만, 방어적으로 추가
                    st.info("이 비디오에는 어떤 자막도 없는 것 같습니다.")
                return None, None

        except TranscriptsDisabled:
            st.error("❌ 이 비디오는 자막이 비활성화되어 있습니다.")
            return None, None
        except NoTranscriptFound: # list_transcripts에서 아무것도 못 찾으면 발생
            st.error(f"❌ 이 비디오 ID({video_id})에 대한 자막을 찾을 수 없습니다. ID를 확인하거나 영상에 자막이 있는지 확인해주세요.")
            return None, None
        except requests.exceptions.Timeout:
            st.warning(f"🌐 요청 시간 초과 - 재시도 중... ({attempt + 1}/{max_attempts})")
            if attempt >= max_attempts - 1:
                st.error("❌ 요청 시간 초과가 지속됩니다.")
                return None, None
            continue 
        except requests.exceptions.RequestException as req_err:
            error_msg = str(req_err).lower()
            st.warning(f"🌐 네트워크 요청 오류: {str(req_err)[:100]}... - 재시도 중... ({attempt + 1}/{max_attempts})")
            if any(keyword in error_msg for keyword in ['429', '403', 'too many requests', 'forbidden', 'blocked']):
                 st.warning(f"🚫 IP 관련 문제로 추정됨 - 재시도 중...")
            if attempt >= max_attempts - 1:
                st.error(f"❌ 네트워크 요청 오류가 지속됩니다: {req_err}")
                return None, None
            continue
        except Exception as e:
            error_msg = str(e).lower()
            st.warning(f"🔍 예상치 못한 오류 발생: {str(e)[:150]}...")
            
            if any(keyword in error_msg for keyword in ['no element found', 'xml', 'parse', 'column 0', 'line 1']):
                if attempt < max_attempts - 1:
                    st.warning(f"XML 파싱 오류 감지 - 재시도 중...")
                    continue
                else:
                    st.error("❌ 자막 데이터 파싱에 계속 실패합니다.")
                    return None, None

            blocked_keywords = [
                'blocked', 'ip', 'cloud', 'too many requests', 
                '429', '403', 'forbidden', 'rate limit', 'quota',
                'denied', 'access denied'
            ]
            if any(keyword in error_msg for keyword in blocked_keywords):
                if attempt < max_attempts - 1:
                    st.warning(f"🚫 IP 차단 또는 접근 제한 감지 - 재시도... ({attempt + 1}/{max_attempts})")
                    continue
                else:
                    st.error("❌ 모든 IP 우회 시도 실패 또는 접근이 계속 거부됩니다.")
                    st.info("💡 해결방법: 잠시 후 다시 시도하거나, 네트워크 환경(예: VPN)을 변경해보세요.")
                    return None, None
            
            if attempt < max_attempts - 1:
                st.warning(f"🛠️ 알 수 없는 오류로 인해 재시도... ({attempt + 1}/{max_attempts})")
                continue
            else:
                st.error(f"❌ 최종 시도 실패. 예상치 못한 오류: {e}")
                return None, None
    
    st.error("❌ 모든 재시도가 실패했습니다. 자막을 가져올 수 없습니다.")
    return None, None

# summarize_text and main functions (as defined in the previous good answer)
# ...
def summarize_text(text, api_key):
    """Gemini로 요약 생성"""
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
        st.error(f"요약 생성 중 오류 발생: {e}")
        if "API key not valid" in str(e):
            st.warning("Gemini API 키가 유효하지 않은 것 같습니다. 확인해주세요.")
        elif "quota" in str(e).lower():
            st.warning("Gemini API 사용 할당량을 초과했을 수 있습니다.")
        return "요약 생성에 실패했습니다. API 키 또는 서비스 상태를 확인해주세요."

def main():
    st.set_page_config(
        page_title="YouTube 자막 요약기",
        page_icon="📺",
        layout="wide"
    )
    
    st.title("📺 YouTube 자막 요약기")
    st.markdown("YouTube 비디오의 자막을 추출하고 Gemini AI로 요약합니다.")
    st.caption("🔍 `youtube-transcript-api` 사용 (수동/자동 자막, 한국어/영어 우선)")
    
    if 'gemini_api_key' not in st.session_state:
        st.session_state.gemini_api_key = ""
    if 'video_id_history' not in st.session_state:
        st.session_state.video_id_history = [] 
    if 'current_video_input' not in st.session_state: # Ensure key exists
        st.session_state.current_video_input = ""


    with st.sidebar:
        st.header("설정")
        st.session_state.gemini_api_key = st.text_input(
            "🔑 Gemini API Key",
            type="password",
            value=st.session_state.gemini_api_key,
            help="Google AI Studio에서 발급받은 API 키 (https://aistudio.google.com/app/apikey)"
        )
        st.markdown("---")
        st.markdown("최근 5개 비디오 ID:")
        # Display most recent 5, but ensure unique keys for buttons if IDs can repeat in history
        # For simplicity, assuming video_id itself is unique enough for this display
        for i, vid in enumerate(reversed(st.session_state.video_id_history[-5:])):
            if st.button(f"ID: {vid}", key=f"history_btn_{vid}_{i}", help=f"{vid} 다시 불러오기"):
                 st.session_state.current_video_input = vid
                 st.experimental_rerun() # Rerun to update the input field


    video_input_key = "video_input_field"
    
    # Use value from session_state if set by history button
    current_input_value = st.session_state.current_video_input if st.session_state.current_video_input else ""
        
    video_input = st.text_input(
        "🎥 YouTube URL 또는 비디오 ID",
        placeholder="예: https://www.youtube.com/watch?v=dQw4w9WgXcQ 또는 dQw4w9WgXcQ",
        value=current_input_value, # Use the value from session state
        key=video_input_key
    )
    # Clear current_video_input after using it so it doesn't persist on manual input changes
    if st.session_state.current_video_input:
        st.session_state.current_video_input = ""
    
    submit_button = st.button(
        "🚀 자막 추출 및 요약", 
        type="primary", 
        disabled=(not st.session_state.gemini_api_key or not video_input)
    )

    if submit_button:
        if not video_input: 
            st.error("YouTube URL 또는 비디오 ID를 입력해주세요!")
            return
        
        video_id = extract_video_id(video_input)
        if not video_id:
            st.error("유효한 YouTube URL 또는 비디오 ID가 아닙니다. ID는 11자의 영문, 숫자, '-', '_' 조합입니다.")
            return
        
        st.info(f"🎯 비디오 ID: {video_id}")
        if video_id not in st.session_state.video_id_history:
            st.session_state.video_id_history.append(video_id)
            if len(st.session_state.video_id_history) > 10: 
                st.session_state.video_id_history.pop(0)


        transcript_placeholder = st.empty()
        summary_placeholder = st.empty()

        with transcript_placeholder.container():
            st.markdown("### 📜 원본 자막")
            transcript_text_area = st.empty()
            download_transcript_button = st.empty()

        with summary_placeholder.container():
            st.markdown("### 🤖 AI 요약 (Gemini 1.5 Flash)")
            summary_text_area = st.empty()
            download_summary_button = st.empty()

        with st.spinner("자막 추출 중... 이 작업은 몇 초에서 몇 분까지 소요될 수 있습니다."):
            transcript_text, method = get_transcript(video_id)
        
        if not transcript_text:
            with transcript_placeholder.container(): # Ensure error message is in the right place
                 st.error("❌ 자막을 가져올 수 없습니다. 위의 로그를 확인해주세요.")
                 with st.expander("💡 해결 방법"):
                    st.markdown("""
                    **확인사항:**
                    - 비디오에 자막이 실제로 있는지 YouTube에서 직접 확인해주세요.
                    - 비디오가 공개 상태인지 확인해주세요 (비공개/일부공개/연령제한 영상은 자막 접근이 어려울 수 있습니다).
                    - 짧은 영상이나 다른 인기있는 영상으로 테스트 해보세요.
                    
                    **IP 차단 또는 네트워크 문제 관련:**
                    - 몇 분 또는 몇 시간 후 다시 시도해주세요.
                    - 다른 네트워크 환경(예: 다른 Wi-Fi, 모바일 핫스팟, VPN)에서 시도해보세요.
                    - 브라우저 확장 프로그램 (특히 광고 차단기, VPN 확장)을 일시적으로 비활성화 해보세요.
                    """)
            return # Stop further processing
        
        st.success(f"✅ 자막 추출 성공! ({method})")
        
        with transcript_placeholder.container():
            st.markdown("### 📜 원본 자막")
            transcript_text_area.text_area("자막 내용", transcript_text, height=300, key="transcript_content_display")
            download_transcript_button.download_button(
                "📥 자막 다운로드 (.txt)",
                transcript_text,
                f"transcript_{video_id}.txt",
                mime="text/plain",
                key="download_transcript_button"
            )
        
        with st.spinner("Gemini AI로 요약 생성 중..."):
            summary = summarize_text(transcript_text, st.session_state.gemini_api_key)
        
        with summary_placeholder.container():
            st.markdown("### 🤖 AI 요약 (Gemini 1.5 Flash)")
            summary_text_area.markdown(summary, unsafe_allow_html=True) 
            download_summary_button.download_button(
                "📥 요약 다운로드 (.md)",
                summary,
                f"summary_{video_id}.md",
                mime="text/markdown",
                key="download_summary_button"
            )

if __name__ == "__main__":
    main()
