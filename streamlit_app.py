import streamlit as st
import google.generativeai as genai
import requests
import re
from urllib.parse import urlparse, parse_qs
import random
import time
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from youtube_transcript_api._api import _TranscriptApi
from youtube_transcript_api._errors import RequestBlockedException, TooManyRequestsException

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

def get_random_headers():
    """랜덤 User-Agent와 헤더 생성"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Android 14; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0'
    ]
    
    languages = [
        'en-US,en;q=0.9',
        'en-GB,en;q=0.9',
        'ko-KR,ko;q=0.8,en-US;q=0.6,en;q=0.4',
        'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
        'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'
    ]
    
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': random.choice(languages),
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0' if 'Mobile' not in random.choice(user_agents) else '?1',
        'sec-ch-ua-platform': f'"{random.choice(["Windows", "macOS", "Linux"])}"'
    }

def get_free_proxies():
    """무료 프록시 목록 (실제 사용시 더 신뢰할 수 있는 프록시 서비스 권장)"""
    return [
        None,  # 프록시 없이 먼저 시도
        # 여기에 실제 프록시를 추가할 수 있습니다
    ]

def create_custom_session():
    """커스텀 세션 생성 (IP 차단 우회용)"""
    session = requests.Session()
    session.headers.update(get_random_headers())
    
    # 쿠키 설정 (선택적)
    session.cookies.update({
        'CONSENT': 'YES+cb.20210328-17-p0.en+FX+1',
        'SOCS': 'CAI',
        'YSC': 'random_value_' + str(random.randint(1000, 9999))
    })
    
    return session

def get_transcript_with_retry(video_id, max_attempts=5):
    """재시도 로직과 IP 우회를 포함한 자막 추출"""
    
    for attempt in range(max_attempts):
        try:
            if attempt > 0:
                delay = random.uniform(2, 5) * attempt
                st.info(f"🔄 시도 {attempt + 1}/{max_attempts} (대기: {delay:.1f}초)")
                time.sleep(delay)
            else:
                st.info(f"🔄 시도 {attempt + 1}/{max_attempts}")
            
            # 랜덤 헤더로 세션 생성
            custom_session = create_custom_session()
            
            # youtube-transcript-api의 내부 세션을 커스텀 세션으로 교체
            original_session = requests.Session()
            _TranscriptApi._session = custom_session
            
            try:
                # 자막 목록 가져오기
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                # 수동 생성 자막 우선 검색
                manual_transcript = None
                auto_transcript = None
                
                for transcript in transcript_list:
                    if not transcript.is_generated:  # 수동 생성
                        manual_transcript = transcript
                        break
                
                # 수동 생성이 없으면 자동 생성 찾기
                if not manual_transcript:
                    for transcript in transcript_list:
                        if transcript.is_generated:  # 자동 생성
                            auto_transcript = transcript
                            break
                
                # 선택된 자막 가져오기
                selected_transcript = manual_transcript if manual_transcript else auto_transcript
                
                if selected_transcript:
                    # 자막 내용 다운로드 (여기서도 지연 추가)
                    time.sleep(random.uniform(0.5, 1.5))
                    transcript_data = selected_transcript.fetch()
                    
                    # 텍스트만 추출
                    full_text = ' '.join([item['text'] for item in transcript_data])
                    
                    # 타입 정보
                    transcript_type = "수동 생성" if not selected_transcript.is_generated else "자동 생성"
                    lang_info = f"({selected_transcript.language_code})"
                    
                    st.success(f"✅ 성공! 시도 {attempt + 1}회만에 자막 추출")
                    return full_text, f"{transcript_type} {lang_info}"
                else:
                    st.warning("사용 가능한 자막이 없습니다.")
                    return None, None
                    
            finally:
                # 원래 세션으로 복구
                _TranscriptApi._session = original_session
                
        except (RequestBlockedException, TooManyRequestsException) as e:
            st.warning(f"IP 차단 또는 요청 한도 초과 (시도 {attempt + 1})")
            if attempt == max_attempts - 1:
                st.error("모든 시도 실패: IP가 차단되었습니다.")
                return None, None
            continue
            
        except TranscriptsDisabled:
            st.warning("이 비디오는 자막이 비활성화되어 있습니다.")
            return None, None
            
        except NoTranscriptFound:
            st.warning("이 비디오에서 자막을 찾을 수 없습니다.")
            return None, None
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # IP 차단 관련 에러 확인
            if any(keyword in error_msg for keyword in ['blocked', 'ip', 'cloud', 'too many requests']):
                st.warning(f"IP 관련 오류 (시도 {attempt + 1}): {str(e)[:100]}...")
                if attempt == max_attempts - 1:
                    st.error("IP 차단으로 모든 시도 실패")
                    return None, None
                continue
            else:
                st.error(f"자막 추출 중 오류: {e}")
                return None, None
    
    return None, None

def get_transcript(video_id):
    """메인 자막 추출 함수"""
    return get_transcript_with_retry(video_id)

def summarize_text(text, api_key):
    """Gemini로 요약 생성"""
    try:
        genai.configure(api_key=api_key)
        
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
        return f"요약 생성 실패: {e}"

def main():
    st.set_page_config(
        page_title="YouTube 자막 요약기",
        page_icon="📺",
        layout="wide"
    )
    
    st.title("📺 YouTube 자막 요약기")
    st.markdown("YouTube 비디오의 자막을 추출하고 Gemini AI로 요약합니다.")
    st.caption("🛡️ youtube-transcript-api + IP 차단 우회 기능")
    
    gemini_api_key = st.text_input(
        "🔑 Gemini API Key",
        type="password",
        help="Google AI Studio에서 발급받은 API 키"
    )
    
    video_input = st.text_input(
        "🎥 YouTube URL 또는 비디오 ID",
        placeholder="예: https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )
    
    # 고급 설정
    with st.expander("🔧 고급 설정"):
        max_attempts = st.slider("최대 재시도 횟수", 1, 10, 5)
        st.caption("IP 차단 시 재시도할 최대 횟수를 설정합니다.")
    
    if st.button("🚀 자막 추출 및 요약", type="primary", disabled=(not gemini_api_key)):
        if not video_input:
            st.error("YouTube URL을 입력해주세요!")
            return
        
        video_id = extract_video_id(video_input)
        if not video_id:
            st.error("유효한 YouTube URL이 아닙니다.")
            return
        
        st.info(f"🎯 비디오 ID: {video_id}")
        
        # 자막 추출
        with st.spinner("자막 추출 중... (IP 차단 우회 기능 활성화)"):
            transcript_text, method = get_transcript_with_retry(video_id, max_attempts)
        
        if not transcript_text:
            st.error("❌ 자막 추출에 실패했습니다.")
            with st.expander("💡 해결 방법"):
                st.markdown("""
                **IP 차단 문제 해결:**
                - 최대 재시도 횟수를 늘려보세요 (고급 설정)
                - 몇 시간 후 다시 시도해보세요
                - 다른 네트워크 환경에서 시도해보세요
                
                **기타 문제:**
                - 비디오에 자막이 있는지 확인
                - 비디오가 공개 상태인지 확인
                - 다른 비디오로 시도
                """)
            return
        
        st.success(f"✅ 자막 추출 성공! ({method})")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📜 원본 자막")
            st.text_area("자막 내용", transcript_text, height=400)
            st.download_button(
                "📥 자막 다운로드",
                transcript_text,
                f"transcript_{video_id}.txt",
                mime="text/plain",
                key="download_transcript"
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
                mime="text/markdown",
                key="download_summary"
            )

if __name__ == "__main__":
    main()
