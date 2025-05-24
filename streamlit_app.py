import streamlit as st
import requests
import google.generativeai as genai
import re
from urllib.parse import urlparse, parse_qs
import json
import xml.etree.ElementTree as ET
import html

# YouTube 라이브러리 import (간단한 방식)
youtube_api_available = False
try:
    from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, NoTranscriptAvailable
    youtube_api_available = True
    st.success("✅ YouTube 라이브러리 로드 성공")
except ImportError:
    st.warning("⚠️ youtube-transcript-api 라이브러리를 찾을 수 없습니다.")
    st.info("직접 스크래핑 방식으로 작동합니다.")

# --- 비디오 ID 추출 ---
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

# --- YouTube API 자막 추출 ---
def get_transcript_youtube_api(video_id):
    """YouTube API로 자막 가져오기"""
    if not youtube_api_available:
        return None, "라이브러리 없음"
    
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # 한국어 수동 자막 우선
        try:
            transcript = transcript_list.find_manually_created_transcript(['ko'])
            return ' '.join([item['text'] for item in transcript.fetch()]), "YouTube API (ko, 수동)"
        except: pass
        
        # 영어 수동 자막
        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
            return ' '.join([item['text'] for item in transcript.fetch()]), "YouTube API (en, 수동)"
        except: pass
        
        # 한국어 자동 자막
        try:
            transcript = transcript_list.find_generated_transcript(['ko'])
            return ' '.join([item['text'] for item in transcript.fetch()]), "YouTube API (ko, 자동)"
        except: pass
        
        # 영어 자동 자막
        try:
            transcript = transcript_list.find_generated_transcript(['en'])
            return ' '.join([item['text'] for item in transcript.fetch()]), "YouTube API (en, 자동)"
        except: pass
        
        return None, "자막 없음"
        
    except Exception as e:
        return None, f"API 오류: {str(e)}"

# --- 직접 스크래핑 ---
def get_transcript_scraping(video_id):
    """직접 스크래핑으로 자막 가져오기"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        url = f"https://www.youtube.com/watch?v={video_id}"
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code != 200:
            return None
        
        # 자막 트랙 찾기
        caption_tracks = []
        
        # playerCaptionsTracklistRenderer 찾기
        match = re.search(r'"playerCaptionsTracklistRenderer":\s*(\{.*?\})', response.text)
        if match:
            try:
                data = json.loads(match.group(1).encode('utf-8').decode('unicode_escape'))
                if "captionTracks" in data:
                    caption_tracks.extend(data["captionTracks"])
            except: pass
        
        # 기본 captionTracks 찾기
        match = re.search(r'"captionTracks":(\[.*?\])', response.text)
        if match:
            try:
                tracks = json.loads(match.group(1).encode('utf-8').decode('unicode_escape'))
                caption_tracks.extend(tracks)
            except: pass
        
        if not caption_tracks:
            return None
        
        # 우선순위로 자막 선택
        selected_url = None
        
        # 한국어 수동 자막 우선
        for track in caption_tracks:
            if (track.get("languageCode") == "ko" and 
                track.get("kind") != "asr" and 
                "baseUrl" in track):
                selected_url = track["baseUrl"]
                break
        
        # 영어 수동 자막
        if not selected_url:
            for track in caption_tracks:
                if (track.get("languageCode") == "en" and 
                    track.get("kind") != "asr" and 
                    "baseUrl" in track):
                    selected_url = track["baseUrl"]
                    break
        
        # 한국어 자동 자막
        if not selected_url:
            for track in caption_tracks:
                if (track.get("languageCode") == "ko" and 
                    "baseUrl" in track):
                    selected_url = track["baseUrl"]
                    break
        
        # 영어 자동 자막
        if not selected_url:
            for track in caption_tracks:
                if (track.get("languageCode") == "en" and 
                    "baseUrl" in track):
                    selected_url = track["baseUrl"]
                    break
        
        # 아무 자막이나
        if not selected_url:
            for track in caption_tracks:
                if "baseUrl" in track:
                    selected_url = track["baseUrl"]
                    break
        
        if not selected_url:
            return None
        
        # 자막 내용 가져오기
        if 'format=' not in selected_url:
            selected_url += "&format=srv3"
        
        caption_response = requests.get(selected_url, headers=headers, timeout=15)
        if caption_response.status_code != 200:
            return None
        
        # XML 파싱
        try:
            root = ET.fromstring(caption_response.text)
            texts = []
            
            for elem in root.findall('.//text'):
                if elem.text:
                    texts.append(elem.text.strip())
            
            if texts:
                full_text = ' '.join(texts)
                full_text = html.unescape(full_text)
                full_text = re.sub(r'\s+', ' ', full_text).strip()
                return full_text if len(full_text) > 30 else None
                
        except: pass
        
        return None
        
    except Exception:
        return None

# --- 자막 가져오기 통합 ---
def get_transcript(video_id):
    """자막 가져오기"""
    
    # 방법 1: YouTube API
    if youtube_api_available:
        st.info("🔄 YouTube API로 자막 추출 중...")
        text, method = get_transcript_youtube_api(video_id)
        if text:
            st.success(f"✅ {method}")
            return text, method
    
    # 방법 2: 직접 스크래핑
    st.info("🔄 직접 스크래핑으로 자막 추출 중...")
    text = get_transcript_scraping(video_id)
    if text:
        st.success("✅ 직접 스크래핑 성공")
        return text, "직접 스크래핑"
    
    return None, None

# --- Gemini 요약 ---
def summarize_with_gemini(text, api_key):
    """Gemini로 요약"""
    try:
        genai.configure(api_key=api_key)
        
        # 텍스트 길이 제한
        if len(text) > 30000:
            text = text[:30000]
            st.caption("자막이 길어 앞부분만 요약에 사용합니다.")
        
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        prompt = f"""다음 YouTube 영상 자막을 한국어로 요약해주세요:

{text}

다음 형식으로 요약해주세요:

## 📌 핵심 주제
(영상의 주요 주제를 1-2문장으로)

## 🔑 주요 내용
1. (첫 번째 핵심 내용)
2. (두 번째 핵심 내용)
3. (세 번째 핵심 내용)

## 💡 결론 및 시사점
(영상의 결론과 교훈)
"""
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        return f"❌ 요약 생성 실패: {str(e)}"

# --- Streamlit UI ---
def main():
    st.set_page_config(
        page_title="YouTube 자막 요약기",
        page_icon="📺",
        layout="wide"
    )
    
    st.title("📺 YouTube 자막 요약기")
    st.markdown("YouTube 비디오의 자막을 추출하고 Gemini AI로 요약합니다.")
    
    # API 키 입력
    with st.sidebar:
        st.header("⚙️ 설정")
        api_key = st.text_input("🔑 Gemini API Key", type="password")
        
        if api_key:
            st.success("✅ API 키 입력됨")
        else:
            st.warning("⚠️ API 키를 입력하세요")
        
        st.link_button("API 키 발급", "https://makersuite.google.com/app/apikey")
    
    # 비디오 URL 입력
    video_url = st.text_input(
        "🎥 YouTube URL 또는 비디오 ID",
        placeholder="https://www.youtube.com/watch?v=..."
    )
    
    # 실행 버튼
    if st.button("🚀 자막 추출 및 요약", type="primary", disabled=not api_key):
        if not video_url:
            st.error("❌ YouTube URL을 입력하세요!")
            return
        
        # 비디오 ID 추출
        video_id = extract_video_id(video_url)
        if not video_id:
            st.error("❌ 유효하지 않은 YouTube URL입니다!")
            return
        
        st.info(f"🎯 비디오 ID: {video_id}")
        
        # 자막 추출
        with st.spinner("자막 추출 중..."):
            transcript, method = get_transcript(video_id)
        
        if not transcript:
            st.error("❌ 자막을 가져올 수 없습니다.")
            st.info("비디오에 자막이 있는지, 공개 상태인지 확인해주세요.")
            return
        
        # 결과 표시
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📜 원본 자막")
            st.text_area("자막 내용", transcript, height=400)
            st.download_button(
                "📥 자막 다운로드",
                transcript,
                f"transcript_{video_id}.txt",
                mime="text/plain"
            )
        
        with col2:
            st.subheader("🤖 AI 요약")
            with st.spinner("요약 생성 중..."):
                summary = summarize_with_gemini(transcript, api_key)
            
            if "❌" in summary:
                st.error(summary)
            else:
                st.markdown(summary)
                st.download_button(
                    "📥 요약 다운로드",
                    summary,
                    f"summary_{video_id}.md",
                    mime="text/markdown"
                )

if __name__ == "__main__":
    main()
