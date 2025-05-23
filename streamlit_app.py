import streamlit as st
import requests
import google.generativeai as genai
import re
from urllib.parse import urlparse, parse_qs
import json

def extract_video_id(url):
    """YouTube URL에서 비디오 ID 추출"""
    if "youtube.com/watch" in url:
        parsed_url = urlparse(url)
        return parse_qs(parsed_url.query)['v'][0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    elif "youtube.com/embed/" in url:
        return url.split("embed/")[1].split("?")[0]
    else:
        return url.strip()

def get_transcript_alternative_apis(video_id):
    """대안 API들을 사용해서 자막 가져오기"""
    
    # 진행 표시용
    progress_placeholder = st.empty()
    log_messages = []
    
    # 여러 무료 자막 API 서비스들 시도
    services = [
        {
            'name': 'YouTube Transcript API (무료)',
            'url': f'https://youtube-transcript-api.p.rapidapi.com/transcript?video_id={video_id}',
            'headers': {'X-RapidAPI-Host': 'youtube-transcript-api.p.rapidapi.com'}
        },
        {
            'name': 'Transcript API v2',
            'url': f'https://api.streamelements.com/kappa/v2/chatstats/{video_id}/transcript',
            'headers': {}
        },
        {
            'name': 'YouTube Subtitle API',
            'url': f'https://youtube-subtitles-api.herokuapp.com/api/subtitles/{video_id}',
            'headers': {}
        },
        {
            'name': 'OpenAI Whisper API (자막 생성)',
            'url': f'https://api.assemblyai.com/v2/transcript',
            'headers': {}
        }
    ]
    
    for i, service in enumerate(services):
        try:
            progress_placeholder.info(f"🔄 {service['name']} 시도 중... ({i+1}/{len(services)})")
            
            response = requests.get(
                service['url'], 
                headers=service['headers'],
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # 다양한 응답 형식 처리
                transcript_text = None
                
                if isinstance(data, list):
                    # 배열 형태의 자막
                    transcript_text = ' '.join([
                        item.get('text', '') or item.get('transcript', '') or str(item) 
                        for item in data
                    ])
                elif isinstance(data, dict):
                    # 객체 형태의 자막
                    if 'transcript' in data:
                        if isinstance(data['transcript'], list):
                            transcript_text = ' '.join([item.get('text', '') for item in data['transcript']])
                        else:
                            transcript_text = data['transcript']
                    elif 'subtitles' in data:
                        transcript_text = data['subtitles']
                    elif 'text' in data:
                        transcript_text = data['text']
                
                if transcript_text and len(transcript_text.strip()) > 100:
                    progress_placeholder.success(f"✅ {service['name']} 성공!")
                    return transcript_text.strip()
                else:
                    log_messages.append(f"❌ {service['name']}: 자막 내용이 너무 짧음")
                    
            else:
                log_messages.append(f"❌ {service['name']}: HTTP {response.status_code}")
                    
        except Exception as e:
            log_messages.append(f"❌ {service['name']}: {str(e)[:50]}...")
            continue
    
    # 모든 시도 실패시 로그 표시
    progress_placeholder.empty()
    
    if log_messages:
        with st.expander("🔍 상세 로그 보기"):
            for msg in log_messages:
                st.write(msg)
    
    return None

def get_transcript_youtube_direct(video_id):
    """YouTube에서 직접 자막 정보 가져오기 (스크래핑)"""
    
    progress_placeholder = st.empty()
    
    try:
        progress_placeholder.info("🔄 YouTube 직접 접근 시도...")
        
        # YouTube 페이지 헤더 설정 (봇 차단 우회)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        # YouTube watch 페이지 접근
        url = f"https://www.youtube.com/watch?v={video_id}"
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            # 자막 정보가 있는지 확인
            if 'captionTracks' in response.text:
                progress_placeholder.success("✅ 자막 정보 발견!")
                
                # 간단한 자막 URL 추출 (정규식 사용)
                caption_pattern = r'"captionTracks":\[{"baseUrl":"([^"]+)"'
                match = re.search(caption_pattern, response.text)
                
                if match:
                    caption_url = match.group(1).replace('\\u0026', '&')
                    
                    # 자막 다운로드
                    caption_response = requests.get(caption_url, headers=headers, timeout=10)
                    if caption_response.status_code == 200:
                        # XML 형태의 자막에서 텍스트 추출
                        import xml.etree.ElementTree as ET
                        try:
                            root = ET.fromstring(caption_response.content)
                            transcript_parts = []
                            
                            for text_elem in root.findall('.//text'):
                                if text_elem.text:
                                    transcript_parts.append(text_elem.text.strip())
                            
                            if transcript_parts:
                                progress_placeholder.success("✅ YouTube 직접 접근 성공!")
                                return ' '.join(transcript_parts)
                        except:
                            pass
            
            progress_placeholder.empty()
            return None
            
    except Exception as e:
        progress_placeholder.empty()
        with st.expander("🔍 상세 로그 보기"):
            st.write(f"❌ YouTube 직접 접근 실패: {str(e)}")
        return None

def get_transcript(video_id):
    """모든 방법을 시도해서 자막 가져오기"""
    
    # 방법 1: 대안 API들 시도
    transcript = get_transcript_alternative_apis(video_id)
    if transcript:
        return transcript, "대안 API", len(transcript)
    
    # 방법 2: YouTube 직접 접근 시도
    transcript = get_transcript_youtube_direct(video_id)
    if transcript:
        return transcript, "직접 접근", len(transcript)
    
    return None, None, None

def summarize_text(text, api_key):
    """Gemini로 요약 생성 - 안정적인 모델 사용"""
    try:
        genai.configure(api_key=api_key)
        
        # 안정적인 모델들을 순서대로 시도
        models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        
        for model_name in models:
            try:
                model = genai.GenerativeModel(model_name)
                
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
                if "not found" in str(e).lower():
                    continue  # 다음 모델 시도
                else:
                    raise e
        
        return "사용 가능한 Gemini 모델을 찾을 수 없습니다. API 키를 확인해주세요."
        
    except Exception as e:
        return f"요약 생성 실패: {str(e)}"

def main():
    st.set_page_config(
        page_title="YouTube 자막 요약기 (간편 버전)",
        page_icon="📺"
    )
    
    st.title("📺 YouTube 자막 요약기")
    st.write("YouTube 비디오의 자막을 추출하고 AI로 요약합니다.")
    
    # Gemini API 키 입력
    col1, col2 = st.columns([3, 1])
    
    with col1:
        gemini_api_key = st.text_input(
            "🔑 Gemini API Key",
            type="password",
            help="Google AI Studio에서 무료로 발급받으세요"
        )
    
    with col2:
        st.write("")  # 정렬용
        if st.button("🔗 API 키 발급"):
            st.markdown("[Google AI Studio →](https://makersuite.google.com/app/apikey)")
    
    # 비디오 URL 입력
    video_input = st.text_input(
        "🎥 YouTube URL 또는 비디오 ID",
        placeholder="https://www.youtube.com/watch?v=VIDEO_ID",
        help="YouTube URL 전체 또는 11자리 비디오 ID를 입력하세요"
    )
    
    # 처리 버튼
    if st.button("🚀 자막 추출 및 AI 요약", type="primary", use_container_width=True):
        if not gemini_api_key:
            st.error("❌ Gemini API Key를 입력해주세요!")
            return
        
        if not video_input:
            st.error("❌ YouTube URL을 입력해주세요!")
            return
        
        # 비디오 ID 추출
        video_id = extract_video_id(video_input)
        st.info(f"🎯 비디오 ID: {video_id}")
        
        # 자막 가져오기
        with st.spinner("📄 여러 방법으로 자막 가져오는 중..."):
            transcript, method, length = get_transcript(video_id)
        
        if not transcript:
            st.error("❌ 모든 방법으로 자막을 가져올 수 없습니다")
            
            with st.expander("🔧 해결 방법"):
                st.markdown("""
                ### 🚨 자막 추출 실패
                
                **가능한 원인:**
                1. 해당 비디오에 자막이 없음
                2. 비공개 또는 제한된 비디오
                3. 외부 API 서비스 일시 중단
                4. 네트워크 연결 문제
                
                **해결 방법:**
                1. **다른 비디오로 시도** 📺
                   - 자막이 확실히 있는 공개 비디오
                   - TED Talks, 교육 영상 추천
                
                2. **시간을 두고 재시도** ⏰
                   - 외부 서비스 복구 대기
                   - 다른 시간대에 시도
                
                3. **OAuth 버전 사용** 🔐
                   - 더 안정적인 공식 API 사용
                   - Google 인증 필요하지만 높은 성공률
                
                ### 📺 추천 테스트 비디오
                - TED Talks (자막 풍부)
                - Khan Academy (교육 콘텐츠)
                - 인기 있는 영어 비디오
                """)
            return
        
        # 성공
        st.success(f"✅ 자막 추출 성공! ({method}로 가져옴, {length:,}자)")
        
        # 결과를 탭으로 표시
        tab1, tab2 = st.tabs(["🤖 **AI 요약**", "📜 **원본 자막**"])
        
        with tab1:
            with st.spinner("🤖 AI 요약 생성 중..."):
                summary = summarize_text(transcript, gemini_api_key)
            
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
