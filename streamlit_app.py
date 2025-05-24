import streamlit as st
import google.generativeai as genai
import requests
import re
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET
import html
import json
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

def get_transcript_method1(video_id):
    """방법 1: YouTube timedtext API 직접 호출"""
    try:
        st.info("🔄 방법 1: timedtext API 시도 중...")
        
        list_url = f"https://www.youtube.com/api/timedtext?type=list&v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        response = requests.get(list_url, headers=headers, timeout=15)
        
        if response.status_code == 200 and response.text.strip():
            try:
                root = ET.fromstring(response.text)
                tracks = root.findall('.//track')
                
                if tracks:
                    st.success(f"✅ {len(tracks)}개의 자막 트랙 발견")
                    
                    # 수동 생성 자막 우선 검색
                    manual_tracks = [t for t in tracks if t.get('kind') != 'asr']
                    auto_tracks = [t for t in tracks if t.get('kind') == 'asr']
                    
                    selected_track = None
                    track_type = None
                    
                    if manual_tracks:
                        selected_track = manual_tracks[0]
                        track_type = "수동 생성"
                        st.info("📝 수동 생성 자막 선택")
                    elif auto_tracks:
                        selected_track = auto_tracks[0]
                        track_type = "자동 생성"
                        st.info("🤖 자동 생성 자막 선택")
                    
                    if selected_track is not None:
                        lang_code = selected_track.get('lang_code', 'unknown')
                        
                        # 자막 내용 다운로드
                        caption_url = f"https://www.youtube.com/api/timedtext?lang={lang_code}&v={video_id}"
                        if selected_track.get('kind') == 'asr':
                            caption_url += "&kind=asr"
                        
                        caption_response = requests.get(caption_url, headers=headers, timeout=15)
                        
                        if caption_response.status_code == 200:
                            return parse_xml_transcript(caption_response.text, f"{track_type} ({lang_code})")
                            
            except ET.ParseError as e:
                st.warning(f"XML 파싱 오류: {e}")
        
        st.warning("❌ 방법 1 실패")
        return None, None
        
    except Exception as e:
        st.warning(f"❌ 방법 1 오류: {e}")
        return None, None

def get_transcript_method2(video_id):
    """방법 2: YouTube 페이지 스크래핑"""
    try:
        st.info("🔄 방법 2: 페이지 스크래핑 시도 중...")
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            page_content = response.text
            
            # 여러 패턴으로 captionTracks 찾기
            patterns = [
                r'"captionTracks":\s*(\[.*?\])',
                r'"captions":\s*\{[^}]*"playerCaptionsTracklistRenderer":\s*\{[^}]*"captionTracks":\s*(\[.*?\])',
                r'captionTracks["\']:\s*(\[.*?\])'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_content, re.DOTALL)
                if match:
                    try:
                        tracks_str = match.group(1)
                        # 유니코드 이스케이프 처리
                        tracks_str = tracks_str.encode('utf-8').decode('unicode_escape')
                        tracks = json.loads(tracks_str)
                        
                        if tracks:
                            st.success(f"✅ {len(tracks)}개의 자막 트랙 발견")
                            
                            # 수동 생성 자막 우선
                            manual_tracks = [t for t in tracks if t.get('kind') != 'asr' and 'baseUrl' in t]
                            auto_tracks = [t for t in tracks if t.get('kind') == 'asr' and 'baseUrl' in t]
                            
                            selected_track = None
                            track_type = None
                            
                            if manual_tracks:
                                selected_track = manual_tracks[0]
                                track_type = "수동 생성"
                                st.info("📝 수동 생성 자막 선택")
                            elif auto_tracks:
                                selected_track = auto_tracks[0]
                                track_type = "자동 생성"
                                st.info("🤖 자동 생성 자막 선택")
                            
                            if selected_track and 'baseUrl' in selected_track:
                                caption_url = selected_track['baseUrl']
                                lang = selected_track.get('languageCode', 'unknown')
                                
                                caption_response = requests.get(caption_url, headers=headers, timeout=15)
                                
                                if caption_response.status_code == 200:
                                    return parse_xml_transcript(caption_response.text, f"{track_type} ({lang})")
                                    
                    except (json.JSONDecodeError, KeyError) as e:
                        continue
            
        st.warning("❌ 방법 2 실패")
        return None, None
        
    except Exception as e:
        st.warning(f"❌ 방법 2 오류: {e}")
        return None, None

def get_transcript_method3(video_id):
    """방법 3: 대체 스크래핑 방법"""
    try:
        st.info("🔄 방법 3: 대체 스크래핑 시도 중...")
        
        # 다른 User-Agent로 시도
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.youtube.com/',
        }
        
        # 임베드 페이지에서 시도
        embed_url = f"https://www.youtube.com/embed/{video_id}"
        response = requests.get(embed_url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            content = response.text
            
            # 다양한 패턴으로 시도
            patterns = [
                r'"captions".*?"captionTracks":\s*(\[.*?\])',
                r'captionTracks["\']?\s*:\s*(\[.*?\])',
                r'"playerCaptionsTracklistRenderer".*?"captionTracks":\s*(\[.*?\])'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    try:
                        tracks_str = match.group(1)
                        tracks_str = tracks_str.encode('utf-8').decode('unicode_escape')
                        tracks = json.loads(tracks_str)
                        
                        if tracks:
                            st.success(f"✅ {len(tracks)}개의 자막 트랙 발견 (임베드)")
                            
                            # 수동 생성 우선
                            for track in tracks:
                                if 'baseUrl' in track and track.get('kind') != 'asr':
                                    caption_url = track['baseUrl']
                                    lang = track.get('languageCode', 'unknown')
                                    
                                    caption_response = requests.get(caption_url, headers=headers, timeout=15)
                                    if caption_response.status_code == 200:
                                        st.info("📝 수동 생성 자막 선택")
                                        return parse_xml_transcript(caption_response.text, f"수동 생성 ({lang})")
                            
                            # 자동 생성으로 폴백
                            for track in tracks:
                                if 'baseUrl' in track and track.get('kind') == 'asr':
                                    caption_url = track['baseUrl']
                                    lang = track.get('languageCode', 'unknown')
                                    
                                    caption_response = requests.get(caption_url, headers=headers, timeout=15)
                                    if caption_response.status_code == 200:
                                        st.info("🤖 자동 생성 자막 선택")
                                        return parse_xml_transcript(caption_response.text, f"자동 생성 ({lang})")
                                        
                    except (json.JSONDecodeError, KeyError):
                        continue
        
        st.warning("❌ 방법 3 실패")
        return None, None
        
    except Exception as e:
        st.warning(f"❌ 방법 3 오류: {e}")
        return None, None

def parse_xml_transcript(xml_content, method_info):
    """XML 자막 파싱"""
    try:
        root = ET.fromstring(xml_content)
        texts = []
        
        # 다양한 XML 태그 시도
        for tag in ['text', 'p', 's', 'span']:
            elements = root.findall(f'.//{tag}')
            if elements:
                for elem in elements:
                    if elem.text and elem.text.strip():
                        clean_text = html.unescape(elem.text.strip())
                        # 줄바꿈 문자 제거
                        clean_text = re.sub(r'\n+', ' ', clean_text)
                        texts.append(clean_text)
                break
        
        if texts:
            full_text = ' '.join(texts)
            # 중복 공백 제거
            full_text = re.sub(r'\s+', ' ', full_text).strip()
            
            if len(full_text) > 50:  # 최소 길이 체크
                return full_text, method_info
        
        return None, None
        
    except ET.ParseError as e:
        st.warning(f"XML 파싱 실패: {e}")
        # XML이 아닐 수도 있으니 텍스트 그대로 반환 시도
        if xml_content and len(xml_content) > 50:
            clean_text = html.unescape(xml_content)
            clean_text = re.sub(r'<[^>]+>', '', clean_text)  # HTML 태그 제거
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            if len(clean_text) > 50:
                return clean_text, method_info
        return None, None

def get_transcript(video_id):
    """모든 방법을 순차적으로 시도하여 자막 가져오기"""
    methods = [
        get_transcript_method1,
        get_transcript_method2,
        get_transcript_method3
    ]
    
    for i, method in enumerate(methods, 1):
        try:
            transcript_text, method_info = method(video_id)
            if transcript_text:
                st.success(f"✅ 방법 {i} 성공! ({method_info})")
                return transcript_text, method_info
            
            # 실패 시 잠시 대기
            if i < len(methods):
                time.sleep(1)
                
        except Exception as e:
            st.warning(f"방법 {i} 예외 발생: {e}")
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
        with st.spinner("자막 추출 중... (여러 방법을 순차적으로 시도합니다)"):
            transcript_text, method = get_transcript(video_id)
        
        if not transcript_text:
            st.error("❌ 모든 방법으로 자막 추출에 실패했습니다.")
            with st.expander("해결 방법", expanded=True):
                st.markdown("""
                **가능한 원인:**
                - 비디오에 자막이 없음 (자동 생성 자막도 없음)
                - 비디오가 비공개 또는 연령 제한
                - 지역 제한으로 접근 불가
                - YouTube의 일시적인 서비스 제한
                
                **해결 방법:**
                - 다른 공개 비디오로 시도
                - 자막이 확실히 있는 비디오 선택
                - 몇 분 후 다시 시도
                """)
            return
        
        st.success(f"✅ 자막 추출 성공! ({method})")
        st.info(f"📊 자막 길이: {len(transcript_text):,}자")
        
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
