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

def get_working_proxies():
    """작동하는 프록시 목록 가져오기"""
    # 실시간 무료 프록시 + 백업 프록시
    proxies = []
    
    # 실시간 프록시 가져오기
    try:
        response = requests.get('https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all', timeout=5)
        if response.status_code == 200:
            proxy_list = response.text.strip().split('\n')
            for proxy in proxy_list[:5]:  # 처음 5개만
                if ':' in proxy and len(proxy.split(':')) == 2:
                    host, port = proxy.split(':')
                    proxies.append({
                        'http': f'http://{host}:{port}',
                        'https': f'http://{host}:{port}'
                    })
    except:
        pass
    
    # 백업 프록시 추가
    backup_proxies = [
        {'http': 'http://8.210.83.33:80', 'https': 'http://8.210.83.33:80'},
        {'http': 'http://47.74.152.29:8888', 'https': 'http://47.74.152.29:8888'},
        {'http': 'http://43.134.234.74:80', 'https': 'http://43.134.234.74:80'},
        {'http': 'http://20.111.54.16:80', 'https': 'http://20.111.54.16:80'},
    ]
    
    proxies.extend(backup_proxies)
    return proxies

def get_transcript(video_id):
    """원본 코드 구조를 정확히 따른 자막 가져오기"""
    
    # 진행상황 표시용
    status_placeholder = st.empty()
    
    # 원본 코드와 완전히 동일한 구조
    ytt_api = YouTubeTranscriptApi()
    
    # 먼저 프록시 없이 시도 (원본 코드 그대로)
    try:
        status_placeholder.info("🔄 원본 방식으로 시도 중...")
        
        # retrieve the available transcripts
        transcript_list = ytt_api.list(video_id)
        
        # iterate over all available transcripts
        fetched = None
        used_transcript = None
        
        for transcript in transcript_list:
            # the Transcript object provides metadata properties
            if transcript.is_generated == 0:  # get youtube subtitle (원본 코드와 동일)
                try:
                    fetched = transcript.fetch()
                    used_transcript = transcript
                    break
                except:
                    continue
        
        # 수동 자막이 없으면 자동 생성 자막 시도
        if fetched is None:
            for transcript in transcript_list:
                if transcript.is_generated == 1:
                    try:
                        fetched = transcript.fetch()
                        used_transcript = transcript
                        break
                    except:
                        continue
        
        if fetched is not None:
            # 원본 코드와 완전히 동일한 방식
            output = ''
            for f in fetched:
                output += f.text  # 원본 코드와 정확히 동일 (공백 없이)
            
            status_placeholder.success(f"✅ 성공! ({used_transcript.language})")
            return output, used_transcript.language, len(fetched)
    
    except Exception as e:
        # IP 차단 감지
        if any(keyword in str(e).lower() for keyword in ['blocking', 'blocked', 'ip']):
            status_placeholder.warning("⚠️ IP 차단 감지, 프록시로 재시도...")
            
            # 프록시로 재시도
            proxies = get_working_proxies()
            
            for i, proxy in enumerate(proxies):
                try:
                    status_placeholder.info(f"🔄 프록시 {i+1}/{len(proxies)} 시도...")
                    
                    # 프록시 적용하여 원본 코드와 동일한 로직 실행
                    transcript_list = ytt_api.list(video_id, proxies=proxy)
                    
                    fetched = None
                    used_transcript = None
                    
                    # 원본 코드와 동일한 로직
                    for transcript in transcript_list:
                        if transcript.is_generated == 0:  # get youtube subtitle
                            try:
                                fetched = transcript.fetch()
                                used_transcript = transcript
                                break
                            except:
                                continue
                    
                    if fetched is None:
                        for transcript in transcript_list:
                            if transcript.is_generated == 1:
                                try:
                                    fetched = transcript.fetch()
                                    used_transcript = transcript
                                    break
                                except:
                                    continue
                    
                    if fetched is not None:
                        # 원본 코드와 동일
                        output = ''
                        for f in fetched:
                            output += f.text  # 원본과 정확히 동일
                        
                        status_placeholder.success(f"✅ 프록시 {i+1}로 성공! ({used_transcript.language})")
                        return output, used_transcript.language, len(fetched)
                
                except Exception as proxy_error:
                    continue
            
            status_placeholder.error("❌ 모든 프록시 실패")
        else:
            status_placeholder.error(f"❌ 오류: {str(e)}")
    
    return None, None, None

def summarize_text(text, api_key):
    """Gemini AI 요약"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
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
        return response.text
        
    except Exception as e:
        return f"요약 생성 실패: {str(e)}"

def main():
    st.set_page_config(
        page_title="YouTube 자막 요약기",
        page_icon="📺"
    )
    
    st.title("📺 YouTube 자막 요약기")
    st.write("**IP 우회 기본 적용** - YouTube 비디오 자막을 자동으로 추출하고 AI 요약")
    
    # 간단한 안내
    with st.expander("💡 사용법"):
        st.markdown("""
        1. **Gemini API 키 입력** ([여기서 발급](https://makersuite.google.com/app/apikey))
        2. **YouTube URL 또는 비디오 ID 입력**
        3. **요약 생성 버튼 클릭**
        
        ✅ **IP 우회 자동 적용** - 별도 설정 불필요  
        ✅ **여러 프록시 자동 시도** - 높은 성공률  
        ✅ **수동/자동 자막 모두 지원**
        """)
    
    # API 키 입력 (같은 row에 버튼 배치)
    col1, col2 = st.columns([3, 1])
    
    with col1:
        api_key = st.text_input(
            "🔑 Gemini API Key",
            type="password",
            help="Google AI Studio에서 무료로 발급받으세요"
        )
    
    with col2:
        st.write("")  # 빈 공간으로 정렬
        if st.button("🔗 API 키 발급"):
            st.markdown("[Google AI Studio →](https://makersuite.google.com/app/apikey)")
    
    # 비디오 입력
    video_input = st.text_input(
        "🎥 YouTube URL 또는 비디오 ID",
        placeholder="https://www.youtube.com/watch?v=_wUoLrYyJBg",
        help="YouTube URL 전체 또는 11자리 비디오 ID (예: _wUoLrYyJBg)"
    )
    
    # 처리 버튼
    if st.button("🚀 자막 추출 및 AI 요약", type="primary", use_container_width=True):
        if not api_key:
            st.error("❌ Gemini API Key를 입력해주세요!")
            return
        
        if not video_input:
            st.error("❌ YouTube URL을 입력해주세요!")
            return
        
        # 비디오 ID 추출
        video_id = extract_video_id(video_input)
        st.info(f"🎯 비디오 ID: {video_id}")
        
        # 자막 가져오기 (IP 우회 자동 적용)
        transcript, language, segments = get_transcript(video_id)
        
        if not transcript:
            st.error("❌ 자막을 가져올 수 없습니다")
            
            with st.expander("🔧 추가 해결책"):
                st.markdown("""
                ### 🚨 IP 차단 문제 지속
                
                **현재 상황**: YouTube가 클라우드 서버 IP를 차단하고 있습니다.
                
                **검증된 해결책**:
                
                1. **VPN 사용** 🔒 (가장 확실)
                   - ExpressVPN, NordVPN, ProtonVPN 등
                   - 미국, 유럽 서버 선택 후 새로고침
                
                2. **모바일 핫스팟** 📱 (간단함)
                   - 휴대폰 핫스팟으로 인터넷 연결 변경
                   - 다른 통신사 네트워크 사용
                
                3. **다른 시간대 재시도** ⏰
                   - 트래픽이 적은 시간대에 시도
                   - 몇 시간 후 다시 시도
                
                4. **다른 비디오 테스트** 📺
                   - 자막이 확실히 있는 인기 비디오
                   - 짧은 비디오로 먼저 테스트
                
                **참고**: 이는 YouTube의 정책이며, 모든 클라우드 기반 앱이 동일한 문제를 겪습니다.
                """)
            return
        
        # 성공시 결과 표시
        st.success(f"✅ 자막 추출 성공! ({language} 언어, {segments:,}개 세그먼트, {len(transcript):,}자)")
        
        # 탭으로 결과 구성
        tab1, tab2 = st.tabs(["🤖 **AI 요약**", "📜 **원본 자막**"])
        
        with tab1:
            with st.spinner("🤖 AI 요약 생성 중..."):
                summary = summarize_text(transcript, api_key)
            
            st.markdown("### 🤖 AI 요약")
            st.markdown(summary)
            
            # 요약 다운로드
            st.download_button(
                "📥 요약 다운로드",
                summary,
                f"youtube_summary_{video_id}.md",
                mime="text/markdown",
                use_container_width=True
            )
        
        with tab2:
            st.markdown("### 📜 원본 자막")
            st.text_area(
                "추출된 자막",
                transcript,
                height=400,
                help="자막 내용을 확인하고 복사할 수 있습니다"
            )
            
            # 자막 다운로드
            st.download_button(
                "📥 자막 다운로드",
                transcript,
                f"youtube_transcript_{video_id}.txt",
                mime="text/plain",
                use_container_width=True
            )

if __name__ == "__main__":
    main()
