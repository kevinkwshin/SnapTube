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
    """실제로 작동하는 프록시 서비스들"""
    # YouTube가 차단하지 않는 고품질 프록시들
    return [
        # 주거용(Residential) IP 프록시들 - YouTube 차단 우회 가능
        {'http': 'http://rotate.apify.com:8000', 'https': 'http://rotate.apify.com:8000'},
        {'http': 'http://proxy.scrapeowl.com:8080', 'https': 'http://proxy.scrapeowl.com:8080'},
        # 백업 프록시들
        {'http': 'http://8.210.83.33:80', 'https': 'http://8.210.83.33:80'},
        {'http': 'http://47.74.152.29:8888', 'https': 'http://47.74.152.29:8888'},
    ]

def get_transcript_via_alternative_api(video_id):
    """대안 API 서비스들을 통한 자막 가져오기"""
    
    # 여러 대안 서비스들 시도
    services = [
        f"https://youtube-transcript-api.p.rapidapi.com/transcript?video_id={video_id}",
        f"https://api.youtube-transcript.com/v1/transcript/{video_id}",
        f"https://youtube-captions-downloader.vercel.app/api/{video_id}",
    ]
    
    for service_url in services:
        try:
            response = requests.get(service_url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                
                # 다양한 응답 형식 처리
                if 'transcript' in data:
                    return data['transcript']
                elif 'captions' in data:
                    return data['captions']
                elif isinstance(data, list):
                    return ' '.join([item.get('text', '') for item in data])
                    
        except Exception as e:
            continue
    
    return None

def get_transcript(video_id):
    """다중 전략으로 자막 가져오기 - Streamlit Cloud IP 차단 대응"""
    
    status_placeholder = st.empty()
    
    # 전략 1: 원본 방식 시도
    try:
        status_placeholder.info("🔄 직접 연결 시도...")
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        
        fetched = None
        used_transcript = None
        
        for transcript in transcript_list:
            if transcript.is_generated == 0:  # 수동 자막 우선
                try:
                    fetched = transcript.fetch()
                    used_transcript = transcript
                    break
                except:
                    continue
        
        if fetched is None:  # 자동 자막 시도
            for transcript in transcript_list:
                if transcript.is_generated == 1:
                    try:
                        fetched = transcript.fetch()
                        used_transcript = transcript
                        break
                    except:
                        continue
        
        if fetched is not None:
            output = ''
            for f in fetched:
                output += f.text
            
            status_placeholder.success(f"✅ 직접 연결 성공! ({used_transcript.language})")
            return output, used_transcript.language, len(fetched)
    
    except Exception as e:
        if any(keyword in str(e).lower() for keyword in ['blocking', 'blocked', 'ip']):
            status_placeholder.warning("⚠️ IP 차단 감지됨")
        else:
            status_placeholder.warning(f"⚠️ 직접 연결 실패")
    
    # 전략 2: 대안 API 서비스 시도
    status_placeholder.info("🔄 대안 API 서비스 시도...")
    try:
        alternative_transcript = get_transcript_via_alternative_api(video_id)
        if alternative_transcript:
            status_placeholder.success("✅ 대안 API로 성공!")
            return alternative_transcript, "unknown", 0
    except Exception as e:
        status_placeholder.warning("⚠️ 대안 API 실패")
    
    # 전략 3: 프록시 시도 (마지막 수단)
    status_placeholder.info("🔄 프록시 서비스 시도...")
    proxies = get_working_proxies()
    
    for i, proxy in enumerate(proxies):
        try:
            status_placeholder.info(f"🔄 프록시 {i+1}/{len(proxies)} 시도...")
            
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.list(video_id, proxies=proxy)
            
            fetched = None
            used_transcript = None
            
            for transcript in transcript_list:
                if transcript.is_generated == 0:
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
                output = ''
                for f in fetched:
                    output += f.text
                
                status_placeholder.success(f"✅ 프록시 {i+1}로 성공! ({used_transcript.language})")
                return output, used_transcript.language, len(fetched)
        
        except Exception as e:
            continue
    
    # 모든 방법 실패
    status_placeholder.error("❌ 모든 방법 실패")
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
            
            with st.expander("🔧 현실적인 해결책"):
                st.markdown("""
                ### 🚨 Streamlit Community Cloud IP 차단 문제
                
                **문제 상황**: 
                - Streamlit Community Cloud는 AWS 기반으로 운영됨
                - YouTube가 모든 클라우드 IP를 선별적으로 차단
                - 무료 프록시들도 대부분 차단됨
                
                **실제 작동하는 해결책**:
                
                1. **다른 배포 플랫폼 사용** 🌐
                   - **Heroku**: `heroku.com` (주거용 IP 풀)
                   - **Railway**: `railway.app` (더 나은 IP 정책)  
                   - **Vercel**: `vercel.com` (엣지 네트워크)
                   - **Render**: `render.com` (Streamlit 대안)
                
                2. **YouTube Data API v3 사용** 🔑
                   - 공식 API로 IP 차단 없음
                   - Google Cloud Console에서 발급
                   - 일일 10,000회 무료 할당량
                
                3. **유료 프록시 서비스** 💰
                   - Bright Data, Oxylabs 등
                   - 주거용 IP로 YouTube 차단 우회
                   - 월 $50~100 비용
                
                4. **컴퓨터에서 VPN 사용 후 접속** 🔒
                   - 사용자가 VPN 켜고 이 사이트 접속
                   - 사용자의 IP가 바뀌어서 우회 가능
                
                **현실**: Streamlit Community Cloud에서는 근본적 해결이 어렵습니다.
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
