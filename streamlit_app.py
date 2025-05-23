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
    """자막 가져오기 - IP 우회 기본 활성화"""
    
    # 진행상황 표시용 placeholder
    status_placeholder = st.empty()
    
    try:
        ytt_api = YouTubeTranscriptApi()
        
        # 1단계: 프록시로 시도 (기본 활성화)
        status_placeholder.info("🔄 IP 우회로 자막 가져오는 중...")
        
        proxies = get_working_proxies()
        
        for i, proxy in enumerate(proxies):
            try:
                status_placeholder.info(f"🔄 프록시 {i+1}/{len(proxies)} 시도 중...")
                
                # 프록시로 자막 목록 가져오기
                transcript_list = ytt_api.list(video_id, proxies=proxy)
                
                fetched = None
                used_transcript = None
                
                # 수동 자막 우선
                for transcript in transcript_list:
                    if transcript.is_generated == 0:
                        fetched = transcript.fetch()
                        used_transcript = transcript
                        break
                
                # 수동 자막이 없으면 자동 자막
                if fetched is None:
                    for transcript in transcript_list:
                        if transcript.is_generated == 1:
                            fetched = transcript.fetch()
                            used_transcript = transcript
                            break
                
                if fetched:
                    # 성공!
                    status_placeholder.success(f"✅ 프록시 {i+1}로 성공! ({used_transcript.language})")
                    
                    # 텍스트 합치기
                    output = ''
                    for f in fetched:
                        output += f.text + ' '
                    
                    return output.strip(), used_transcript.language, len(fetched)
                
            except Exception as e:
                # 이 프록시는 실패, 다음 프록시 시도
                continue
        
        # 2단계: 모든 프록시 실패시 직접 시도
        status_placeholder.info("🔄 직접 연결 시도 중...")
        
        try:
            transcript_list = ytt_api.list(video_id)
            
            fetched = None
            used_transcript = None
            
            # 수동 자막 우선
            for transcript in transcript_list:
                if transcript.is_generated == 0:
                    fetched = transcript.fetch()
                    used_transcript = transcript
                    break
            
            # 수동 자막이 없으면 자동 자막
            if fetched is None:
                for transcript in transcript_list:
                    if transcript.is_generated == 1:
                        fetched = transcript.fetch()
                        used_transcript = transcript
                        break
            
            if fetched:
                status_placeholder.success(f"✅ 직접 연결 성공! ({used_transcript.language})")
                
                output = ''
                for f in fetched:
                    output += f.text + ' '
                
                return output.strip(), used_transcript.language, len(fetched)
        
        except Exception as e:
            pass
        
        # 완전 실패
        status_placeholder.error("❌ 모든 방법 실패")
        return None, None, None
        
    except Exception as e:
        status_placeholder.error("❌ 오류 발생")
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
    
    # API 키 입력
    api_key = st.text_input(
        "🔑 Gemini API Key",
        type="password",
        help="Google AI Studio에서 무료로 발급받으세요"
    )
    
    if st.button("🔗 API 키 발급받기"):
        st.markdown("[Google AI Studio로 이동 →](https://makersuite.google.com/app/apikey)")
    
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
                ### 🚨 여전히 실패하는 경우
                
                1. **VPN 사용** (가장 확실)
                   - ExpressVPN, NordVPN, ProtonVPN 등
                   - 미국, 유럽 서버 선택
                
                2. **로컬에서 실행** (100% 안정적)
                   ```bash
                   pip install streamlit youtube-transcript-api google-generativeai
                   streamlit run app.py
                   ```
                
                3. **다른 비디오로 테스트**
                   - 자막이 확실히 있는 비디오
                   - TED Talks 추천
                
                4. **시간을 두고 재시도**
                   - 잠시 후 다시 시도
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
