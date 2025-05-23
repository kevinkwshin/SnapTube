import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import re
import requests
import time
import random

def extract_video_id(url):
    """YouTube URL에서 비디오 ID 추출"""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:embed\/)([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return url.strip()

def get_free_proxies():
    """무료 프록시 목록 가져오기"""
    try:
        # 실시간 무료 프록시 API
        response = requests.get('https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=US&ssl=all&anonymity=all', timeout=10)
        proxies = response.text.strip().split('\n')
        
        proxy_list = []
        for proxy in proxies[:3]:  # 처음 3개만 사용
            if ':' in proxy:
                host, port = proxy.split(':')
                proxy_dict = {
                    'http': f'http://{host}:{port}',
                    'https': f'http://{host}:{port}'
                }
                proxy_list.append(proxy_dict)
        
        return proxy_list
    except:
        # 백업 프록시 목록
        return [
            {'http': 'http://8.210.83.33:80', 'https': 'http://8.210.83.33:80'},
            {'http': 'http://47.74.152.29:8888', 'https': 'http://47.74.152.29:8888'},
        ]

def get_transcript_with_bypass(video_id, use_bypass=False):
    """IP 우회 기능이 포함된 자막 가져오기"""
    methods = []
    errors = []
    
    # Method 1: 직접 요청
    methods.append(("직접 요청", lambda: YouTubeTranscriptApi.get_transcript(video_id)))
    
    # Method 2: 프록시 사용 (우회 활성화시)
    if use_bypass:
        try:
            proxies = get_free_proxies()
            for i, proxy in enumerate(proxies):
                methods.append((f"프록시 {i+1}", lambda p=proxy: YouTubeTranscriptApi.get_transcript(video_id, proxies=p)))
        except:
            pass
    
    # Method 3: 다른 언어 시도
    methods.append(("다른 언어 시도", lambda: try_different_languages(video_id)))
    
    # 각 방법을 순차적으로 시도
    for method_name, method_func in methods:
        try:
            transcript = method_func()
            if transcript:
                # 성공한 방법 표시
                if "프록시" in method_name:
                    st.success(f"✅ {method_name}으로 IP 우회 성공!")
                elif method_name == "직접 요청":
                    st.success(f"✅ {method_name} 성공!")
                else:
                    st.success(f"✅ {method_name} 성공!")
                
                return transcript, None
        except Exception as e:
            error_msg = f"{method_name}: {str(e)[:100]}..."
            errors.append(error_msg)
            
            # IP 차단 감지
            if "blocking" in str(e).lower() or "blocked" in str(e).lower():
                if not use_bypass:
                    return None, f"IP 차단 감지됨. '🚀 IP 우회 활성화'를 체크하고 다시 시도하세요.\n\n상세 오류: {str(e)}"
            
            time.sleep(random.uniform(1, 2))  # 짧은 지연
    
    # 모든 방법 실패
    detailed_error = "모든 방법이 실패했습니다.\n\n시도한 방법들:\n" + "\n".join(errors)
    return None, detailed_error

def try_different_languages(video_id):
    """다른 언어 자막 시도"""
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    
    # 수동 자막 우선
    for transcript in transcript_list:
        if not transcript.is_generated:
            try:
                return transcript.fetch()
            except:
                continue
    
    # 자동 생성 자막
    for transcript in transcript_list:
        if transcript.is_generated:
            try:
                return transcript.fetch()
            except:
                continue
    
    raise Exception("사용 가능한 자막이 없습니다")

def get_transcript(video_id, use_bypass=False):
    """자막 가져오기 - IP 우회 기능 포함"""
    try:
        # IP 우회 기능 사용
        transcript_data, error = get_transcript_with_bypass(video_id, use_bypass)
        
        if error:
            return None, error, None
        
        if not transcript_data:
            return None, "자막을 가져올 수 없습니다", None
        
        # 자막 정보 수집
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list_transcripts(video_id)
        
        transcript_info = []
        for transcript in transcript_list:
            transcript_type = "수동 작성" if transcript.is_generated == 0 else "자동 생성"
            transcript_info.append(f"{transcript.language} ({transcript.language_code}) - {transcript_type}")
        
        # 사용된 자막 정보 (첫 번째 자막으로 가정)
        first_transcript = list(transcript_list)[0]
        
        # 자막 텍스트 합치기 (따옴표 제거)
        output = ''
        for f in transcript_data:
            text = f.text.replace("'", "").replace('"', '')
            output += text + ' '
        
        # 성공 정보 반환
        success_info = {
            'language': first_transcript.language,
            'language_code': first_transcript.language_code,
            'type': '수동 작성' if first_transcript.is_generated == 0 else '자동 생성',
            'segments': len(transcript_data),
            'total_chars': len(output.strip()),
            'available_transcripts': transcript_info
        }
        
        return output.strip(), None, success_info
        
    except Exception as e:
        detailed_error = f"자막 목록 가져오기 실패: {str(e)}\n\n가능한 원인:\n1. IP 차단 (IP 우회 활성화 권장)\n2. 잘못된 비디오 ID\n3. 비공개/삭제된 비디오\n4. 네트워크 오류"
        return None, detailed_error, None

def summarize_text(text, api_key):
    """Gemini를 사용한 텍스트 요약"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # 텍스트 길이 제한 제거 (필요시 Gemini가 자동 처리)
        prompt = f"""
다음 YouTube 비디오의 자막을 요약해주세요:

{text}

다음 형식으로 요약해주세요:
## 📌 주요 주제
## 🔑 핵심 내용 (3-5개 포인트)
## 💡 결론 및 시사점

한국어로 명확하고 간결하게 작성해주세요.
"""
        
        response = model.generate_content(prompt)
        return response.text, None
        
    except Exception as e:
        return None, str(e)

def main():
    st.set_page_config(
        page_title="YouTube 자막 요약기",
        page_icon="📺"
    )
    
    st.title("📺 YouTube 자막 요약기")
    st.write("YouTube 비디오의 자막을 추출하고 AI로 요약합니다.")
    
    # 사용법 안내
    with st.expander("💡 사용법 및 IP 차단 해결"):
        st.markdown("""
        ### 📋 사용법
        1. Gemini API 키 입력
        2. YouTube 비디오 URL 입력  
        3. **IP 차단시 '🚀 IP 우회 활성화' 체크**
        4. 요약 생성 버튼 클릭
        
        ### 🚨 IP 차단 문제
        **현상**: 클라우드 환경에서 YouTube가 IP를 차단
        
        **해결책**:
        1. **🚀 IP 우회 활성화** (앱 내장 기능)
        2. **VPN 사용** (컴퓨터에 설치)
        3. **로컬에서 실행** (100% 안정적)
        4. **모바일 핫스팟 사용**
        
        ### 🔧 로컬 실행 방법
        ```bash
        pip install streamlit youtube-transcript-api google-generativeai
        streamlit run app.py
        ```
        
        ### 🎯 자막 우선순위
        1. **수동 작성 자막** (사람이 직접 작성) - 가장 정확
        2. **자동 생성 자막** (YouTube AI 생성) - 차선책
        """)
    
    # IP 우회 옵션
    st.subheader("🚀 IP 우회 설정")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        use_bypass = st.checkbox(
            "🚀 IP 우회 활성화", 
            value=False,
            help="YouTube IP 차단시 활성화하세요. 무료 프록시를 사용하여 IP를 우회합니다."
        )
    
    with col2:
        if use_bypass:
            st.success("🔄 우회 모드")
        else:
            st.info("📍 직접 모드")
    
    if use_bypass:
        st.info("💡 IP 우회가 활성화되었습니다. 무료 프록시를 통해 YouTube에 접근합니다.")
    
    st.markdown("---")
    
    # API 키 입력
    api_key = st.text_input(
        "🔑 Gemini API Key",
        type="password",
        help="Google AI Studio에서 발급받으세요: https://makersuite.google.com/app/apikey"
    )
    
    # 링크 버튼 추가
    if st.button("🔗 AI Studio에서 API 키 발급받기"):
        st.markdown("[Google AI Studio로 이동하기](https://makersuite.google.com/app/apikey)")
    
    # 비디오 URL 입력
    video_input = st.text_input(
        "🎥 YouTube URL 또는 비디오 ID",
        placeholder="https://www.youtube.com/watch?v=VIDEO_ID",
        help="전체 YouTube URL 또는 11자리 비디오 ID (예: dQw4w9WgXcQ)를 입력하세요. 비디오 ID는 YouTube URL에서 'v=' 뒤의 11자리 문자입니다."
    )
    
    # 옵션
    show_transcript = st.checkbox("📜 원본 자막 표시", value=True)
    
    # 처리 버튼
    if st.button("🚀 자막 추출 및 요약", type="primary"):
        if not api_key:
            st.error("❌ Gemini API Key를 입력해주세요!")
            return
        
        if not video_input:
            st.error("❌ YouTube URL을 입력해주세요!")
            return
        
        # 비디오 ID 추출
        video_id = extract_video_id(video_input)
        st.info(f"🎯 비디오 ID: {video_id}")
        
        # 자막 가져오기 (IP 우회 포함)
        with st.spinner("📄 자막 가져오는 중..." + (" (IP 우회 시도)" if use_bypass else "")):
            transcript, error, info = get_transcript(video_id, use_bypass)
        
        if error:
            st.error(f"❌ 자막 가져오기 실패")
            
            # 세부 오류는 expander로 접기
            with st.expander("🔍 세부 오류 정보"):
                st.text(error)
            
            # 해결책 제시 (IP 우회 포함)
            with st.expander("🔧 해결 방법"):
                st.markdown("""
                ### 🔥 즉시 해결책
                
                **1순위: IP 우회 활성화** 🚀
                - 위의 '🚀 IP 우회 활성화' 체크박스를 켜고 다시 시도
                - 앱 내장 무료 프록시 사용
                
                **2순위: VPN 사용** 🔒
                - 컴퓨터에 VPN 앱 설치 (ExpressVPN, NordVPN, ProtonVPN)
                - 미국, 유럽 서버 선택 후 페이지 새로고침
                
                **3순위: 로컬에서 실행** 🏠 (100% 안정적)
                ```bash
                pip install streamlit youtube-transcript-api google-generativeai
                streamlit run app.py
                ```
                
                **4순위: 기타 방법** 📱
                - 모바일 핫스팟 사용
                - 다른 네트워크에서 접속
                - 시간을 두고 재시도
                
                ### 💡 원인 분석
                - 클라우드 환경 IP 차단 (AWS, GCP 등)
                - YouTube의 봇 방지 정책
                - 동일 IP에서 과도한 요청
                """)
            return
        
        if transcript and info:
            # 성공 메시지를 간결하게 표시
            st.success(f"✅ 자막 추출 성공! ({info['type']}, {info['total_chars']:,}자)")
            
            # 세부 정보는 expander로 접기
            with st.expander("📊 자막 상세 정보"):
                st.write(f"**사용된 자막**: {info['language']} ({info['language_code']}) - {info['type']}")
                st.write(f"**세그먼트 수**: {info['segments']:,}개")
                st.write(f"**총 글자 수**: {info['total_chars']:,}자")
                st.write("**사용 가능한 자막**:")
                for transcript_info in info['available_transcripts']:
                    st.write(f"- {transcript_info}")
            
            # 메인 콘텐츠 영역을 탭으로 구성 (큰 글씨로)
            st.markdown("---")
            st.markdown("## 📄 결과")
            
            # 큰 탭 만들기
            col1, col2 = st.columns(2)
            
            with col1:
                transcript_tab = st.button("📜 원본 자막 보기", use_container_width=True, type="secondary")
            
            with col2:
                summary_tab = st.button("🤖 AI 요약 보기", use_container_width=True, type="primary")
            
            # 세션 상태로 탭 관리
            if 'active_tab' not in st.session_state:
                st.session_state.active_tab = 'summary'  # 기본값을 AI 요약으로
            
            if transcript_tab:
                st.session_state.active_tab = 'transcript'
            elif summary_tab:
                st.session_state.active_tab = 'summary'
            
            # 선택된 탭에 따라 내용 표시
            if st.session_state.active_tab == 'transcript':
                st.markdown("---")
                st.markdown("### 📜 원본 자막")
                if show_transcript:
                    st.text_area(
                        "추출된 자막",
                        transcript,
                        height=400,
                        help="자막 내용을 확인하고 복사할 수 있습니다.",
                        key="transcript_area"
                    )
                    
                    # 다운로드 버튼
                    st.download_button(
                        "📥 자막 다운로드",
                        transcript,
                        f"youtube_transcript_{video_id}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                else:
                    st.info("📜 원본 자막 표시를 체크하면 여기에 표시됩니다.")
            
            elif st.session_state.active_tab == 'summary':
                st.markdown("---")
                st.markdown("### 🤖 AI 요약")
                
                # 요약 생성
                with st.spinner("🤖 AI 요약 생성 중..."):
                    summary, summary_error = summarize_text(transcript, api_key)
                
                if summary_error:
                    st.error(f"❌ 요약 생성 실패")
                    with st.expander("🔍 오류 세부사항"):
                        st.text(summary_error)
                    return
                
                if summary:
                    # 요약 내용 표시
                    st.markdown(summary)
                    
                    # 요약 다운로드 버튼
                    st.download_button(
                        "📥 요약 다운로드",
                        summary,
                        f"youtube_summary_{video_id}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )

if __name__ == "__main__":
    main()
