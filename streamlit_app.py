import streamlit as st
import google.generativeai as genai
import requests
import re
from urllib.parse import urlparse, parse_qs
import random
import time
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
        'Cache-Control': 'max-age=0'
    }

def patch_requests_session():
    """requests 모듈의 기본 세션을 패치하여 헤더 변경"""
    original_session_init = requests.Session.__init__
    
    def new_session_init(self):
        original_session_init(self)
        # 랜덤 헤더 적용
        headers = get_random_headers()
        self.headers.update(headers)
        
        # 쿠키 설정
        self.cookies.update({
            'CONSENT': 'YES+cb.20210328-17-p0.en+FX+1',
            'SOCS': 'CAI',
            'YSC': f'random_value_{random.randint(1000, 9999)}'
        })
    
    # 패치 적용
    requests.Session.__init__ = new_session_init
    return original_session_init

def restore_requests_session(original_init):
    """원래 세션으로 복구"""
    requests.Session.__init__ = original_init

def get_transcript_with_retry(video_id, max_attempts=5):
    """재시도 로직과 IP 우회를 포함한 자막 추출"""
    
    original_session_init = None
    
    for attempt in range(max_attempts):
        try:
            if attempt > 0:
                delay = random.uniform(2, 5) * attempt
                st.info(f"🔄 시도 {attempt + 1}/{max_attempts} (대기: {delay:.1f}초)")
                time.sleep(delay)
            else:
                st.info(f"🔄 시도 {attempt + 1}/{max_attempts}")
            
            # 각 시도마다 새로운 랜덤 헤더로 requests 세션 패치
            if original_session_init is None:
                original_session_init = patch_requests_session()
            else:
                # 이미 패치된 경우, 새로운 헤더로 다시 패치
                restore_requests_session(original_session_init)
                patch_requests_session()
            
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
                    
                    # 세션 복구
                    if original_session_init:
                        restore_requests_session(original_session_init)
                    
                    return full_text, f"{transcript_type} {lang_info}"
                else:
                    st.warning("사용 가능한 자막이 없습니다.")
                    if original_session_init:
                        restore_requests_session(original_session_init)
                    return None, None
                    
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            st.warning(f"자막 문제: {e}")
            if original_session_init:
                restore_requests_session(original_session_init)
            return None, None
                
        except Exception as e:
            error_msg = str(e).lower()
            
            # IP 차단 관련 에러 문자열로 확인
            blocked_keywords = [
                'blocked', 'ip', 'cloud', 'too many requests', 'request', 
                '429', '403', 'forbidden', 'rate limit', 'quota', 'ban'
            ]
            
            if any(keyword in error_msg for keyword in blocked_keywords):
                st.warning(f"IP 차단 감지 (시도 {attempt + 1}): {str(e)[:100]}...")
                if attempt == max_attempts - 1:
                    st.error("IP 차단으로 모든 시도 실패")
                    if original_session_init:
                        restore_requests_session(original_session_init)
                    return None, None
                continue
            else:
                st.error(f"자막 추출 중 오류: {e}")
                if original_session_init:
                    restore_requests_session(original_session_init)
                return None, None
    
    if original_session_init:
        restore_requests_session(original_session_init)
    return None, None

def get_transcript_simple(video_id):
    """간단한 자막 추출 (우회 기능 없이)"""
    try:
        st.info("🔄 기본 방법으로 자막 추출 시도...")
        
        # 기본 방법으로 시도
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # 수동 생성 자막 우선
        selected_transcript = None
        transcript_type = None
        
        for transcript in transcript_list:
            if not transcript.is_generated:
                selected_transcript = transcript
                transcript_type = "수동 생성"
                break
        
        if not selected_transcript:
            for transcript in transcript_list:
                if transcript.is_generated:
                    selected_transcript = transcript
                    transcript_type = "자동 생성"
                    break
        
        if selected_transcript:
            transcript_data = selected_transcript.fetch()
            full_text = ' '.join([item['text'] for item in transcript_data])
            lang_info = f"({selected_transcript.language_code})"
            
            st.success("✅ 기본 방법으로 자막 추출 성공!")
            return full_text, f"{transcript_type} {lang_info}"
        
        return None, None
        
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        st.warning(f"자막 없음: {e}")
        return None, None
        
    except Exception as e:
        error_msg = str(e).lower()
        blocked_keywords = [
            'blocked', 'ip', 'cloud', 'too many requests', 'request',
            '429', '403', 'forbidden', 'rate limit', 'quota', 'ban'
        ]
        
        if any(keyword in error_msg for keyword in blocked_keywords):
            st.warning("⚠️ IP 차단 가능성 - 우회 모드로 전환합니다...")
            return get_transcript_with_retry(video_id)
        else:
            st.error(f"자막 추출 오류: {e}")
            return None, None

def get_transcript(video_id):
    """메인 자막 추출 함수 - 기본 방법 먼저 시도, 필요시 우회"""
    return get_transcript_simple(video_id)

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
    st.caption("🛡️ youtube-transcript-api + 스마트 IP 차단 우회")
    
    gemini_api_key = st.text_input(
        "🔑 Gemini API Key",
        type="password",
        help="Google AI Studio에서 발급받은 API 키"
    )
    
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
        
        st.info(f"🎯 비디오 ID: {video_id}")
        
        # 자막 추출
        with st.spinner("자막 추출 중... (필요시 IP 차단 우회 모드 자동 활성화)"):
            transcript_text, method = get_transcript(video_id)
        
        if not transcript_text:
            st.error("❌ 자막 추출에 실패했습니다.")
            with st.expander("💡 해결 방법"):
                st.markdown("""
                **일반적인 해결 방법:**
                - 비디오에 자막이 실제로 있는지 확인
                - 비디오가 공개 상태인지 확인 (비공개/연령제한 불가)
                - 다른 자막이 있는 비디오로 시도
                
                **IP 차단 관련:**
                - 몇 시간 후 다시 시도
                - 다른 네트워크 환경에서 시도
                - VPN 사용 고려
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
