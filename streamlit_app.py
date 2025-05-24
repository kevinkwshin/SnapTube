import streamlit as st
import google.generativeai as genai
import requests
import re
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET
import html

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

def get_video_info(video_id, youtube_api_key):
    """YouTube Data API로 비디오 정보 가져오기"""
    try:
        url = f"https://www.googleapis.com/youtube/v3/videos"
        params = {
            'part': 'snippet',
            'id': video_id,
            'key': youtube_api_key
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'items' in data and len(data['items']) > 0:
            return data['items'][0]['snippet']
        else:
            return None
    except Exception as e:
        st.error(f"비디오 정보 가져오기 실패: {e}")
        return None

def get_transcript_from_timedtext(video_id):
    """YouTube의 timedtext API를 통해 자막 가져오기"""
    try:
        # 자막 목록 가져오기
        list_url = f"https://www.youtube.com/api/timedtext?type=list&v={video_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(list_url, headers=headers)
        
        if response.status_code != 200:
            return None, None
            
        # XML 파싱하여 사용 가능한 자막 찾기
        try:
            root = ET.fromstring(response.text)
            tracks = root.findall('.//track')
            
            if not tracks:
                return None, None
            
            # 수동 생성 자막 우선 찾기
            manual_track = None
            auto_track = None
            
            for track in tracks:
                kind = track.get('kind', '')
                if kind != 'asr':  # 수동 생성
                    manual_track = track
                    break
                else:  # 자동 생성
                    if auto_track is None:
                        auto_track = track
            
            # 사용할 트랙 선택
            selected_track = manual_track if manual_track is not None else auto_track
            
            if selected_track is None:
                return None, None
            
            # 자막 다운로드
            lang_code = selected_track.get('lang_code', 'unknown')
            kind = selected_track.get('kind', '')
            track_type = "수동 생성" if kind != 'asr' else "자동 생성"
            
            caption_url = f"https://www.youtube.com/api/timedtext?lang={lang_code}&v={video_id}"
            if kind == 'asr':
                caption_url += "&kind=asr"
            
            caption_response = requests.get(caption_url, headers=headers)
            
            if caption_response.status_code == 200:
                # XML에서 텍스트 추출
                caption_root = ET.fromstring(caption_response.text)
                texts = []
                
                for text_elem in caption_root.findall('.//text'):
                    if text_elem.text:
                        clean_text = html.unescape(text_elem.text.strip())
                        texts.append(clean_text)
                
                if texts:
                    full_text = ' '.join(texts)
                    return full_text, f"{track_type} ({lang_code})"
                    
        except ET.ParseError:
            pass
            
    except Exception as e:
        st.error(f"자막 추출 중 오류: {e}")
    
    return None, None

def get_transcript_fallback(video_id):
    """대체 방법으로 자막 가져오기"""
    try:
        # YouTube 페이지 스크래핑
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            page_content = response.text
            
            # captionTracks 패턴 찾기
            pattern = r'"captionTracks":\s*(\[.*?\])'
            match = re.search(pattern, page_content)
            
            if match:
                import json
                try:
                    tracks_str = match.group(1).encode('utf-8').decode('unicode_escape')
                    tracks = json.loads(tracks_str)
                    
                    # 수동 생성 자막 우선
                    manual_track = None
                    auto_track = None
                    
                    for track in tracks:
                        if 'baseUrl' in track:
                            if track.get('kind') != 'asr':
                                manual_track = track
                                break
                            else:
                                if auto_track is None:
                                    auto_track = track
                    
                    selected_track = manual_track if manual_track else auto_track
                    
                    if selected_track and 'baseUrl' in selected_track:
                        caption_url = selected_track['baseUrl']
                        caption_response = requests.get(caption_url, headers=headers)
                        
                        if caption_response.status_code == 200:
                            try:
                                root = ET.fromstring(caption_response.text)
                                texts = []
                                
                                for elem in root.findall('.//text'):
                                    if elem.text:
                                        clean_text = html.unescape(elem.text.strip())
                                        texts.append(clean_text)
                                
                                if texts:
                                    full_text = ' '.join(texts)
                                    track_type = "수동 생성" if selected_track.get('kind') != 'asr' else "자동 생성"
                                    lang = selected_track.get('languageCode', 'unknown')
                                    return full_text, f"{track_type} ({lang})"
                                    
                            except ET.ParseError:
                                pass
                                
                except json.JSONDecodeError:
                    pass
    
    except Exception as e:
        st.error(f"대체 방법 실패: {e}")
    
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
    
    col1, col2 = st.columns(2)
    
    with col1:
        gemini_api_key = st.text_input(
            "🔑 Gemini API Key",
            type="password",
            help="Google AI Studio에서 발급받은 API 키"
        )
    
    with col2:
        youtube_api_key = st.text_input(
            "🔑 YouTube Data API Key (선택사항)",
            type="password",
            help="YouTube Data API 키 (비디오 제목 표시용)"
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
        
        st.info(f"비디오 ID: {video_id}")
        
        # 비디오 정보 가져오기 (선택사항)
        if youtube_api_key:
            video_info = get_video_info(video_id, youtube_api_key)
            if video_info:
                st.success(f"📹 **{video_info['title']}**")
                st.caption(f"채널: {video_info['channelTitle']}")
        
        # 자막 추출
        with st.spinner("자막 추출 중..."):
            transcript_text, method = get_transcript_from_timedtext(video_id)
            
            if not transcript_text:
                st.warning("첫 번째 방법 실패. 대체 방법 시도 중...")
                transcript_text, method = get_transcript_fallback(video_id)
        
        if not transcript_text:
            st.error("자막을 가져올 수 없습니다. 다음을 확인해주세요:")
            with st.expander("해결 방법", expanded=True):
                st.markdown("""
                - 비디오에 자막이 실제로 존재하는지 확인
                - 비디오가 공개 상태인지 확인 
                - 다른 비디오로 시도해보기
                - YouTube Data API 키 추가 (선택사항)
                """)
            return
        
        st.success(f"자막 추출 성공! ({method})")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📜 원본 자막")
            st.text_area("자막 내용", transcript_text, height=400)
            st.download_button(
                "📥 자막 다운로드",
                transcript_text,
                f"transcript_{video_id}.txt",
                mime="text/plain"
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
                mime="text/markdown"
            )

if __name__ == "__main__":
    main()
