import streamlit as st
import google.generativeai as genai
import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import requests
import random
import time

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
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

def setup_session_with_proxy():
    """프록시와 헤더를 설정한 세션 생성"""
    session = requests.Session()
    session.headers.update(get_random_headers())
    
    # 쿠키 설정
    session.cookies.update({
        'CONSENT': 'YES+cb.20210328-17-p0.en+FX+1',
        'SOCS': 'CAI'
    })
    
    return session

def patch_youtube_transcript_api():
    """youtube-transcript-api의 내부 요청들을 모두 패치"""
    import youtube_transcript_api._api as yt_api
    
    # 원본 함수들 백업
    original_session = getattr(yt_api, '_session', None)
    
    # 새로운 세션 생성
    session = setup_session_with_proxy()
    
    # youtube-transcript-api 내부 세션 교체
    if hasattr(yt_api, '_session'):
        yt_api._session = session
    
    # requests 모듈 자체도 패치
    original_get = requests.get
    original_post = requests.post
    
    def patched_get(*args, **kwargs):
        kwargs.setdefault('headers', {}).update(session.headers)
        kwargs.setdefault('cookies', session.cookies)
        kwargs.setdefault('timeout', 15)
        return original_get(*args, **kwargs)
    
    def patched_post(*args, **kwargs):
        kwargs.setdefault('headers', {}).update(session.headers)
        kwargs.setdefault('cookies', session.cookies)
        kwargs.setdefault('timeout', 15)
        return original_post(*args, **kwargs)
    
    requests.get = patched_get
    requests.post = patched_post
    
    return original_get, original_post, original_session

def restore_requests(original_get, original_post, original_session):
    """원본 requests 함수들 복원"""
    requests.get = original_get
    requests.post = original_post
    
    # youtube-transcript-api 세션도 복원
    if original_session is not None:
        import youtube_transcript_api._api as yt_api
        if hasattr(yt_api, '_session'):
            yt_api._session = original_session

def get_transcript(video_id):
    """YouTube Transcript API로 자막 가져오기 - 강화된 IP 차단 우회"""
    max_attempts = 5
    
    for attempt in range(max_attempts):
        # 패치 정보 저장
        patch_info = None
        
        try:
            if attempt > 0:
                delay = random.uniform(3, 8) * attempt  # 점진적으로 대기 시간 증가
                st.info(f"🔄 재시도 {attempt + 1}/{max_attempts} (대기: {delay:.1f}초)")
                time.sleep(delay)
            
            # 각 시도마다 완전히 새로운 패치 적용
            st.info(f"🛡️ IP 우회 설정 중... (시도 {attempt + 1})")
            patch_info = patch_youtube_transcript_api()
            
            try:
                # 사용 가능한 자막 목록 가져오기
                st.info("📋 자막 목록 조회 중...")
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                # 수동 생성 자막 우선 찾기
                manual_transcript = None
                auto_transcript = None
                
                for transcript in transcript_list:
                    if not transcript.is_generated:  # 수동 생성 자막
                        manual_transcript = transcript
                        st.info(f"📝 수동 생성 자막 발견: {transcript.language} ({transcript.language_code})")
                        break
                
                # 수동 생성이 없으면 자동 생성 찾기
                if not manual_transcript:
                    for transcript in transcript_list:
                        if transcript.is_generated:  # 자동 생성 자막
                            auto_transcript = transcript
                            st.info(f"🤖 자동 생성 자막 발견: {transcript.language} ({transcript.language_code})")
                            break
                
                # 선택된 자막으로 내용 가져오기
                selected_transcript = manual_transcript if manual_transcript else auto_transcript
                
                if selected_transcript:
                    try:
                        # 자막 내용 다운로드 전 추가 대기 및 준비
                        st.info("⬇️ 자막 내용 다운로드 중...")
                        time.sleep(random.uniform(2, 4))
                        
                        # 자막 내용 다운로드
                        transcript_data = selected_transcript.fetch()
                        
                        # 데이터 유효성 검사
                        if not transcript_data or len(transcript_data) == 0:
                            if attempt < max_attempts - 1:
                                st.warning("빈 자막 데이터 - 재시도 중...")
                                continue
                            else:
                                st.error("❌ 자막 데이터가 비어있습니다.")
                                return None, None
                        
                        # 텍스트만 추출하여 합치기
                        full_text = ' '.join([item['text'] for item in transcript_data if 'text' in item])
                        
                        # 텍스트 유효성 검사
                        if not full_text or len(full_text.strip()) < 10:
                            if attempt < max_attempts - 1:
                                st.warning("자막 텍스트가 너무 짧음 - 재시도 중...")
                                continue
                            else:
                                st.error("❌ 유효한 자막 텍스트를 찾을 수 없습니다.")
                                return None, None
                        
                        # 타입 정보 생성
                        transcript_type = "수동 생성" if not selected_transcript.is_generated else "자동 생성"
                        lang_info = f"{selected_transcript.language} ({selected_transcript.language_code})"
                        
                        # 성공시 패치 복원
                        if patch_info:
                            restore_requests(*patch_info)
                        
                        st.success(f"✅ 자막 다운로드 성공! (시도 {attempt + 1}회)")
                        return full_text, f"{transcript_type} - {lang_info}"
                        
                    except Exception as fetch_error:
                        error_msg = str(fetch_error).lower()
                        st.warning(f"🔍 fetch 오류 분석: {str(fetch_error)[:100]}...")
                        
                        # XML 파싱 오류
                        if any(keyword in error_msg for keyword in 
                               ['no element found', 'xml', 'parse', 'column 0', 'line 1']):
                            if attempt < max_attempts - 1:
                                st.warning(f"XML 파싱 오류 - 새로운 IP로 재시도...")
                                continue
                            else:
                                st.error("❌ 자막 데이터 파싱에 계속 실패합니다.")
                                return None, None
                        
                        # IP 차단 관련 오류
                        blocked_keywords = [
                            'blocked', 'ip', 'cloud', 'too many requests', 
                            '429', '403', 'forbidden', 'rate limit', 'quota',
                            'request', 'ban', 'denied'
                        ]
                        
                        if any(keyword in error_msg for keyword in blocked_keywords):
                            if attempt < max_attempts - 1:
                                st.warning(f"🚫 IP 차단 감지 - 우회 방법 변경 중... ({attempt + 1}/{max_attempts})")
                                continue
                            else:
                                st.error("❌ 모든 IP 우회 시도 실패")
                                return None, None
                        
                        # 네트워크 관련 오류
                        network_keywords = ['timeout', 'connection', 'network', 'dns']
                        if any(keyword in error_msg for keyword in network_keywords):
                            if attempt < max_attempts - 1:
                                st.warning(f"🌐 네트워크 오류 - 재시도...")
                                continue
                            else:
                                st.error("❌ 네트워크 연결 문제가 지속됩니다.")
                                return None, None
                        
                        # 기타 오류는 즉시 재발생
                        raise fetch_error
                else:
                    st.error("❌ 사용 가능한 자막을 찾을 수 없습니다.")
                    return None, None
            
            finally:
                # 패치 복원
                if patch_info:
                    restore_requests(*patch_info)
                
        except TranscriptsDisabled:
            if patch_info:
                restore_requests(*patch_info)
            st.error("❌ 이 비디오는 자막이 비활성화되어 있습니다.")
            return None, None
        except NoTranscriptFound:
            if patch_info:
                restore_requests(*patch_info)
            st.error("❌ 이 비디오에서 자막을 찾을 수 없습니다.")
            return None, None
        except Exception as e:
            if patch_info:
                restore_requests(*patch_info)
                
            error_msg = str(e).lower()
            st.warning(f"🔍 전체 오류 분석: {str(e)[:100]}...")
            
            # IP 차단 관련 에러 확인
            blocked_keywords = [
                'blocked', 'ip', 'cloud', 'too many requests', 
                '429', '403', 'forbidden', 'rate limit', 'quota',
                'request', 'ban', 'denied'
            ]
            
            if any(keyword in error_msg for keyword in blocked_keywords):
                if attempt < max_attempts - 1:
                    st.warning(f"🔄 IP 차단 우회 재시도... ({attempt + 1}/{max_attempts})")
                    continue
                else:
                    st.error("❌ 모든 IP 우회 방법이 실패했습니다.")
                    st.info("💡 해결방법: 몇 시간 후 다시 시도하거나 VPN을 사용해보세요.")
                    return None, None
            else:
                st.error(f"❌ 예상치 못한 오류: {e}")
                return None, None
    
    # 모든 시도 실패
    st.error("❌ 모든 재시도가 실패했습니다.")
    return None, None

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
    st.caption("🔍 youtube-transcript-api 사용 - 수동 생성 자막 우선")
    
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
        with st.spinner("자막 추출 중..."):
            transcript_text, method = get_transcript(video_id)
        
        if not transcript_text:
            st.error("❌ 자막을 가져올 수 없습니다.")
            with st.expander("💡 해결 방법"):
                st.markdown("""
                **확인사항:**
                - 비디오에 자막이 실제로 있는지 확인
                - 비디오가 공개 상태인지 확인 (비공개/연령제한 불가)
                - 다른 자막이 있는 비디오로 시도
                
                **IP 차단 관련:**
                - 몇 시간 후 다시 시도
                - 다른 네트워크 환경에서 시도
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
