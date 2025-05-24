import streamlit as st
import google.generativeai as genai
import requests
import re
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET
import html
import json
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
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0'
    ]
    
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }

def get_transcript_method1(video_id):
    """방법 1: 직접 스크래핑 (IP 차단 우회)"""
    try:
        st.info("🔄 방법 1: 직접 스크래핑 시도...")
        
        headers = get_random_headers()
        
        # 여러 URL 패턴 시도
        urls = [
            f"https://www.youtube.com/watch?v={video_id}",
            f"https://m.youtube.com/watch?v={video_id}",  # 모바일 버전
            f"https://www.youtube.com/embed/{video_id}"   # 임베드 버전
        ]
        
        for url in urls:
            try:
                # 랜덤 지연
                time.sleep(random.uniform(0.5, 2.0))
                
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    page_content = response.text
                    
                    # 여러 패턴으로 자막 정보 찾기
                    patterns = [
                        r'"captionTracks":\s*(\[.*?\])',
                        r'"captions".*?"captionTracks":\s*(\[.*?\])',  
                        r'captionTracks["\']:\s*(\[.*?\])',
                        r'"playerCaptionsTracklistRenderer".*?"captionTracks":\s*(\[.*?\])'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, page_content, re.DOTALL)
                        if match:
                            try:
                                tracks_str = match.group(1)
                                tracks_str = tracks_str.encode('utf-8').decode('unicode_escape')
                                tracks = json.loads(tracks_str)
                                
                                if tracks:
                                    st.success(f"✅ {len(tracks)}개 자막 트랙 발견")
                                    
                                    # 수동 생성 우선
                                    manual_tracks = [t for t in tracks if t.get('kind') != 'asr' and 'baseUrl' in t]
                                    auto_tracks = [t for t in tracks if t.get('kind') == 'asr' and 'baseUrl' in t]
                                    
                                    selected_track = None
                                    track_type = None
                                    
                                    if manual_tracks:
                                        selected_track = manual_tracks[0]
                                        track_type = "수동 생성"
                                    elif auto_tracks:
                                        selected_track = auto_tracks[0]
                                        track_type = "자동 생성"
                                    
                                    if selected_track:
                                        caption_url = selected_track['baseUrl']
                                        lang = selected_track.get('languageCode', 'unknown')
                                        
                                        # 자막 내용 다운로드
                                        time.sleep(random.uniform(0.5, 1.5))
                                        caption_headers = get_random_headers()
                                        caption_response = requests.get(caption_url, headers=caption_headers, timeout=10)
                                        
                                        if caption_response.status_code == 200:
                                            return parse_xml_transcript(caption_response.text, f"{track_type} ({lang})")
                                            
                            except (json.JSONDecodeError, KeyError):
                                continue
                                
            except requests.RequestException:
                continue
        
        return None, None
        
    except Exception as e:
        st.warning(f"방법 1 실패: {str(e)[:50]}...")
        return None, None

def get_transcript_method2(video_id):
    """방법 2: 다른 접근 방식 - API 엔드포인트 직접 호출"""
    try:
        st.info("🔄 방법 2: API 엔드포인트 시도...")
        
        headers = get_random_headers()
        
        # 다양한 API 엔드포인트 시도
        api_urls = [
            f"https://www.youtube.com/api/timedtext?type=list&v={video_id}",
            f"https://youtubei.googleapis.com/youtubei/v1/player?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8&videoId={video_id}",
        ]
        
        for api_url in api_urls:
            try:
                time.sleep(random.uniform(1.0, 2.0))
                response = requests.get(api_url, headers=headers, timeout=10)
                
                if response.status_code == 200 and response.text.strip():
                    if 'timedtext' in api_url:
                        # timedtext API 응답 처리
                        try:
                            root = ET.fromstring(response.text)
                            tracks = root.findall('.//track')
                            
                            if tracks:
                                st.success(f"✅ {len(tracks)}개 자막 트랙 발견 (API)")
                                
                                # 수동 생성 우선
                                selected_track = None
                                track_type = None
                                
                                for track in tracks:
                                    if track.get('kind') != 'asr':
                                        selected_track = track
                                        track_type = "수동 생성"
                                        break
                                
                                if not selected_track:
                                    for track in tracks:
                                        if track.get('kind') == 'asr':
                                            selected_track = track
                                            track_type = "자동 생성"
                                            break
                                
                                if selected_track:
                                    lang_code = selected_track.get('lang_code', 'unknown')
                                    caption_url = f"https://www.youtube.com/api/timedtext?lang={lang_code}&v={video_id}"
                                    
                                    if selected_track.get('kind') == 'asr':
                                        caption_url += "&kind=asr"
                                    
                                    time.sleep(random.uniform(0.5, 1.0))
                                    caption_response = requests.get(caption_url, headers=get_random_headers(), timeout=10)
                                    
                                    if caption_response.status_code == 200:
                                        return parse_xml_transcript(caption_response.text, f"{track_type} ({lang_code})")
                                        
                        except ET.ParseError:
                            continue
                            
            except requests.RequestException:
                continue
                
        return None, None
        
    except Exception as e:
        st.warning(f"방법 2 실패: {str(e)[:50]}...")
        return None, None

def get_transcript_method3(video_id):
    """방법 3: youtube-transcript-api with proxies (fallback)"""
    try:
        st.info("🔄 방법 3: youtube-transcript-api 라이브러리 시도...")
        
        # youtube-transcript-api 임포트 (선택적)
        try:
            from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
            
            # 프록시 없이 먼저 시도
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
                
                st.success(f"✅ youtube-transcript-api 성공!")
                return full_text, f"{transcript_type} {lang_info}"
                
        except (TranscriptsDisabled, NoTranscriptFound):
            return None, None
        except Exception:
            # 라이브러리가 없거나 차단된 경우
            return None, None
            
    except Exception:
        return None, None

def parse_xml_transcript(xml_content, method_info):
    """XML 자막 파싱"""
    try:
        root = ET.fromstring(xml_content)
        texts = []
        
        # 다양한 태그 시도
        for tag in ['text', 'p', 's']:
            elements = root.findall(f'.//{tag}')
            if elements:
                for elem in elements:
                    if elem.text and elem.text.strip():
                        clean_text = html.unescape(elem.text.strip())
                        clean_text = re.sub(r'\n+', ' ', clean_text)
                        texts.append(clean_text)
                break
        
        if texts:
            full_text = ' '.join(texts)
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            
            if len(full_text) > 30:
                return full_text, method_info
        
        # XML 파싱 실패시 정규식으로 텍스트 추출
        text_matches = re.findall(r'<text[^>]*>(.*?)</text>', xml_content, re.DOTALL)
        if text_matches:
            texts = []
            for match in text_matches:
                clean_text = re.sub(r'<[^>]+>', '', match)
                clean_text = html.unescape(clean_text.strip())
                if clean_text:
                    texts.append(clean_text)
            
            if texts:
                full_text = ' '.join(texts)
                full_text = re.sub(r'\s+', ' ', full_text).strip()
                
                if len(full_text) > 30:
                    return full_text, method_info
        
        return None, None
        
    except ET.ParseError:
        # 텍스트에서 직접 추출
        text_content = re.sub(r'<[^>]+>', '', xml_content)
        text_content = html.unescape(text_content).strip()
        if len(text_content) > 30:
            return text_content, method_info
        return None, None

def get_transcript(video_id):
    """모든 방법을 시도하여 자막 가져오기"""
    methods = [
        get_transcript_method1,  # 직접 스크래핑
        get_transcript_method2,  # API 엔드포인트
        get_transcript_method3   # youtube-transcript-api
    ]
    
    for method in methods:
        try:
            transcript_text, method_info = method(video_id)
            if transcript_text and len(transcript_text) > 50:
                return transcript_text, method_info
            
            # 각 방법 사이에 지연
            time.sleep(random.uniform(1.0, 3.0))
            
        except Exception as e:
            st.warning(f"방법 실패: {str(e)[:30]}...")
            continue
    
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
    st.caption("🛡️ IP 차단 우회 기능 포함")
    
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
        with st.spinner("자막 추출 중... (여러 방법을 시도합니다)"):
            transcript_text, method = get_transcript(video_id)
        
        if not transcript_text:
            st.error("❌ 모든 방법으로 자막 추출에 실패했습니다.")
            with st.expander("💡 해결 방법"):
                st.markdown("""
                **가능한 원인:**
                - 비디오에 자막이 없음
                - 비디오가 비공개/연령제한/지역제한
                - 일시적인 네트워크 문제
                
                **해결 방법:**
                - 자막이 확실히 있는 다른 공개 비디오로 시도
                - 몇 분 후 다시 시도
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
