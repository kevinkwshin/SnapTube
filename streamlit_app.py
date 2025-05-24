import streamlit as st
import google.generativeai as genai
import requests
import re
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET
import html
import json

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

def get_transcript(video_id):
    """자막 가져오기 - 간단하고 효과적인 방법"""
    
    # 방법 1: 페이지 스크래핑으로 captionTracks 찾기
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            page_content = response.text
            
            # captionTracks 패턴 찾기
            match = re.search(r'"captionTracks":\s*(\[.*?\])', page_content)
            
            if match:
                try:
                    tracks_str = match.group(1).encode('utf-8').decode('unicode_escape')
                    tracks = json.loads(tracks_str)
                    
                    if tracks:
                        # 수동 생성 자막 우선 (kind가 'asr'이 아닌 것)
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
                        
                        if selected_track:
                            caption_url = selected_track['baseUrl']
                            lang = selected_track.get('languageCode', 'unknown')
                            track_type = "수동" if selected_track.get('kind') != 'asr' else "자동"
                            
                            # 자막 다운로드
                            caption_response = requests.get(caption_url, headers=headers, timeout=10)
                            
                            if caption_response.status_code == 200:
                                # XML에서 텍스트 추출
                                try:
                                    root = ET.fromstring(caption_response.text)
                                    texts = []
                                    
                                    for elem in root.findall('.//text'):
                                        if elem.text:
                                            clean_text = html.unescape(elem.text.strip())
                                            texts.append(clean_text)
                                    
                                    if texts:
                                        full_text = ' '.join(texts)
                                        full_text = re.sub(r'\s+', ' ', full_text).strip()
                                        
                                        if len(full_text) > 50:
                                            return full_text, f"{track_type} 생성 ({lang})"
                                            
                                except ET.ParseError:
                                    # XML 파싱 실패시 원본 텍스트에서 추출 시도
                                    text_content = re.sub(r'<[^>]+>', '', caption_response.text)
                                    text_content = html.unescape(text_content).strip()
                                    if len(text_content) > 50:
                                        return text_content, f"{track_type} 생성 ({lang})"
                                        
                except json.JSONDecodeError:
                    pass
    
    except Exception:
        pass
    
    # 방법 2: timedtext API 시도
    try:
        list_url = f"https://www.youtube.com/api/timedtext?type=list&v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(list_url, headers=headers, timeout=10)
        
        if response.status_code == 200 and response.text.strip():
            try:
                root = ET.fromstring(response.text)
                tracks = root.findall('.//track')
                
                if tracks:
                    # 수동 생성 우선
                    selected_track = None
                    track_type = None
                    
                    for track in tracks:
                        if track.get('kind') != 'asr':
                            selected_track = track
                            track_type = "수동"
                            break
                    
                    if not selected_track:
                        for track in tracks:
                            if track.get('kind') == 'asr':
                                selected_track = track
                                track_type = "자동"
                                break
                    
                    if selected_track:
                        lang_code = selected_track.get('lang_code', 'unknown')
                        caption_url = f"https://www.youtube.com/api/timedtext?lang={lang_code}&v={video_id}"
                        
                        if selected_track.get('kind') == 'asr':
                            caption_url += "&kind=asr"
                        
                        caption_response = requests.get(caption_url, headers=headers, timeout=10)
                        
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
                                    full_text = re.sub(r'\s+', ' ', full_text).strip()
                                    
                                    if len(full_text) > 50:
                                        return full_text, f"{track_type} 생성 ({lang_code})"
                                        
                            except ET.ParseError:
                                pass
                                
            except ET.ParseError:
                pass
                
    except Exception:
        pass
    
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
        with st.spinner("자막 추출 중..."):
            transcript_text, method = get_transcript(video_id)
        
        if not transcript_text:
            st.error("❌ 자막을 가져올 수 없습니다.")
            with st.expander("💡 해결 방법"):
                st.markdown("""
                - 비디오에 자막이 있는지 확인
                - 비디오가 공개 상태인지 확인
                - 다른 비디오로 시도
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
