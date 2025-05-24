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
    """자막 가져오기 - 여러 방법 시도"""
    
    progress_placeholder = st.empty()
    
    # 방법 1: 페이지 스크래핑 (가장 안정적)
    try:
        progress_placeholder.info("🔄 방법 1: 페이지 스크래핑 시도 중...")
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            page_content = response.text
            
            # 여러 패턴으로 시도
            patterns = [
                r'"captionTracks":\s*(\[.*?\])',
                r'"captions".*?"captionTracks":\s*(\[.*?\])',
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
                            progress_placeholder.success(f"✅ {len(tracks)}개 자막 트랙 발견")
                            
                            # 수동 생성 자막 우선
                            manual_tracks = [t for t in tracks if t.get('kind') != 'asr' and 'baseUrl' in t]
                            auto_tracks = [t for t in tracks if t.get('kind') == 'asr' and 'baseUrl' in t]
                            
                            selected_track = None
                            track_type = None
                            
                            if manual_tracks:
                                selected_track = manual_tracks[0]
                                track_type = "수동"
                            elif auto_tracks:
                                selected_track = auto_tracks[0]
                                track_type = "자동"
                            
                            if selected_track and 'baseUrl' in selected_track:
                                caption_url = selected_track['baseUrl']
                                lang = selected_track.get('languageCode', 'unknown')
                                
                                # 자막 내용 다운로드
                                caption_response = requests.get(caption_url, headers=headers, timeout=15)
                                
                                if caption_response.status_code == 200:
                                    return parse_caption_xml(caption_response.text, f"{track_type} 생성 ({lang})", progress_placeholder)
                                    
                    except (json.JSONDecodeError, KeyError):
                        continue
    
    except Exception as e:
        progress_placeholder.warning(f"방법 1 실패: {str(e)[:50]}...")
    
    # 방법 2: timedtext API
    try:
        progress_placeholder.info("🔄 방법 2: timedtext API 시도 중...")
        list_url = f"https://www.youtube.com/api/timedtext?type=list&v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(list_url, headers=headers, timeout=15)
        
        if response.status_code == 200 and response.text.strip():
            try:
                root = ET.fromstring(response.text)
                tracks = root.findall('.//track')
                
                if tracks:
                    progress_placeholder.success(f"✅ {len(tracks)}개 자막 트랙 발견")
                    
                    # 수동 생성 우선
                    manual_tracks = [t for t in tracks if t.get('kind') != 'asr']
                    auto_tracks = [t for t in tracks if t.get('kind') == 'asr']
                    
                    selected_track = None
                    track_type = None
                    
                    if manual_tracks:
                        selected_track = manual_tracks[0]
                        track_type = "수동"
                    elif auto_tracks:
                        selected_track = auto_tracks[0]
                        track_type = "자동"
                    
                    if selected_track:
                        lang_code = selected_track.get('lang_code', 'unknown')
                        caption_url = f"https://www.youtube.com/api/timedtext?lang={lang_code}&v={video_id}"
                        
                        if selected_track.get('kind') == 'asr':
                            caption_url += "&kind=asr"
                        
                        caption_response = requests.get(caption_url, headers=headers, timeout=15)
                        
                        if caption_response.status_code == 200:
                            return parse_caption_xml(caption_response.text, f"{track_type} 생성 ({lang_code})", progress_placeholder)
                            
            except ET.ParseError as e:
                progress_placeholder.warning(f"XML 파싱 실패: {str(e)[:50]}...")
                
    except Exception as e:
        progress_placeholder.warning(f"방법 2 실패: {str(e)[:50]}...")
    
    # 방법 3: 다른 User-Agent로 재시도
    try:
        progress_placeholder.info("🔄 방법 3: 다른 브라우저로 재시도 중...")
        url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        
        if response.status_code == 200:
            match = re.search(r'"captionTracks":\s*(\[.*?\])', response.text)
            
            if match:
                try:
                    tracks_str = match.group(1).encode('utf-8').decode('unicode_escape')
                    tracks = json.loads(tracks_str)
                    
                    if tracks:
                        for track in tracks:
                            if 'baseUrl' in track:
                                caption_url = track['baseUrl']
                                lang = track.get('languageCode', 'unknown')
                                track_type = "수동" if track.get('kind') != 'asr' else "자동"
                                
                                caption_response = requests.get(caption_url, headers=headers, timeout=15)
                                
                                if caption_response.status_code == 200:
                                    result = parse_caption_xml(caption_response.text, f"{track_type} 생성 ({lang})", progress_placeholder)
                                    if result[0]:  # 성공하면 바로 반환
                                        return result
                                        
                except (json.JSONDecodeError, KeyError):
                    pass
                    
    except Exception as e:
        progress_placeholder.warning(f"방법 3 실패: {str(e)[:50]}...")
    
    progress_placeholder.empty()
    return None, None

def parse_caption_xml(xml_content, method_info, progress_placeholder):
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
                progress_placeholder.success(f"✅ 자막 추출 성공! ({method_info})")
                return full_text, method_info
        
        # XML 파싱 실패시 정규식으로 텍스트 추출 시도
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
                    progress_placeholder.success(f"✅ 자막 추출 성공! ({method_info})")
                    return full_text, method_info
        
    except ET.ParseError:
        # 완전히 다른 형식일 수 있으니 정규식으로 시도
        text_content = re.sub(r'<[^>]+>', '', xml_content)
        text_content = html.unescape(text_content).strip()
        if len(text_content) > 30:
            progress_placeholder.success(f"✅ 자막 추출 성공! ({method_info})")
            return text_content, method_info
    
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
            # 디버깅을 위해 직접 테스트해보기
            st.write("**🔍 디버깅 정보:**")
            
            # 페이지 접근 테스트
            try:
                test_url = f"https://www.youtube.com/watch?v={video_id}"
                test_response = requests.get(test_url, timeout=10)
                st.write(f"- 페이지 접근: ✅ 성공 (상태코드: {test_response.status_code})")
                
                # captionTracks 패턴 검색
                if '"captionTracks"' in test_response.text:
                    st.write("- captionTracks 패턴: ✅ 발견됨")
                    
                    # 실제 매치 시도
                    match = re.search(r'"captionTracks":\s*(\[.*?\])', test_response.text)
                    if match:
                        st.write("- 정규식 매치: ✅ 성공")
                        try:
                            tracks_str = match.group(1).encode('utf-8').decode('unicode_escape')
                            tracks = json.loads(tracks_str)
                            st.write(f"- JSON 파싱: ✅ 성공 ({len(tracks)}개 트랙)")
                            
                            # 각 트랙 정보 표시
                            for i, track in enumerate(tracks):
                                track_info = f"트랙 {i+1}: "
                                if 'languageCode' in track:
                                    track_info += f"언어={track['languageCode']}, "
                                if 'kind' in track:
                                    track_info += f"타입={track['kind']}, "
                                else:
                                    track_info += "타입=수동, "
                                if 'baseUrl' in track:
                                    track_info += "URL=있음"
                                else:
                                    track_info += "URL=없음"
                                st.write(f"  - {track_info}")
                                
                        except json.JSONDecodeError as e:
                            st.write(f"- JSON 파싱: ❌ 실패 ({e})")
                        except Exception as e:
                            st.write(f"- 트랙 처리: ❌ 실패 ({e})")
                    else:
                        st.write("- 정규식 매치: ❌ 실패")
                else:
                    st.write("- captionTracks 패턴: ❌ 없음")
                    
            except Exception as e:
                st.write(f"- 페이지 접근: ❌ 실패 ({e})")
            
            # timedtext API 테스트
            try:
                timedtext_url = f"https://www.youtube.com/api/timedtext?type=list&v={video_id}"
                timedtext_response = requests.get(timedtext_url, timeout=10)
                st.write(f"- timedtext API: 상태코드 {timedtext_response.status_code}")
                if timedtext_response.status_code == 200 and timedtext_response.text.strip():
                    st.write(f"- timedtext 응답 길이: {len(timedtext_response.text)} 문자")
                    try:
                        root = ET.fromstring(timedtext_response.text)
                        tracks = root.findall('.//track')
                        st.write(f"- timedtext 트랙 수: {len(tracks)}개")
                    except ET.ParseError as e:
                        st.write(f"- timedtext XML 파싱: ❌ 실패 ({e})")
                else:
                    st.write("- timedtext API: ❌ 빈 응답")
            except Exception as e:
                st.write(f"- timedtext API: ❌ 실패 ({e})")
            
            with st.expander("💡 해결 방법"):
                st.markdown("""
                - 비디오에 자막이 있는지 확인
                - 비디오가 공개 상태인지 확인
                - 다른 비디오로 시도
                - 몇 분 후 다시 시도
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
