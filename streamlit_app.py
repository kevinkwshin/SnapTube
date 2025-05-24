import streamlit as st
import requests
import google.generativeai as genai
import re
from urllib.parse import urlparse, parse_qs
import json
import xml.etree.ElementTree as ET # for direct youtube transcript parsing

# youtube-transcript-api 라이브러리가 필요합니다.
# 터미널에서: pip install youtube-transcript-api
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

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
            return None # 잘못된 URL 형식
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
    elif re.match(r"^[a-zA-Z0-9_-]{11}$", url): # 11자리 비디오 ID 직접 입력
        return url
    else:
        return None # ID로 간주하기엔 너무 길거나 패턴이 다름

# --- 자막 추출 로직 (youtube-transcript-api 사용 최우선) ---
def get_transcript_from_youtube_api(video_id, preferred_languages=['ko', 'en']):
    """youtube-transcript-api 라이브러리를 사용하여 자막 가져오기"""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # 선호하는 언어 순서대로 자막 찾기
        for lang_code in preferred_languages:
            try:
                transcript = transcript_list.find_transcript([lang_code])
                fetched_transcript = transcript.fetch()
                return ' '.join([item['text'] for item in fetched_transcript]), f"YouTube API ({lang_code})"
            except NoTranscriptFound:
                continue # 다음 선호 언어 시도
        
        # 선호 언어가 없으면, 사용 가능한 아무 자막이나 (보통 자동 생성된 영어)
        try:
            transcript = transcript_list.find_generated_transcript(['en']) # 영어 자동자막 시도
            fetched_transcript = transcript.fetch()
            return ' '.join([item['text'] for item in fetched_transcript]), "YouTube API (auto-en)"
        except NoTranscriptFound:
            pass # 다른 언어 자동자막도 시도해볼 수 있으나, 일단 영어만

        # 정말 아무것도 없으면 첫번째 사용가능한 자막
        for available_transcript in transcript_list:
            fetched_transcript = available_transcript.fetch()
            return ' '.join([item['text'] for item in fetched_transcript]), f"YouTube API ({available_transcript.language_code})"

    except TranscriptsDisabled:
        st.warning(f"[{video_id}] 비디오에 대해 자막이 비활성화되어 있습니다.")
        return None, "자막 비활성화"
    except NoTranscriptFound:
        st.warning(f"[{video_id}] 비디오에 대해 어떤 언어의 자막도 찾을 수 없습니다.")
        return None, "자막 없음"
    except Exception as e:
        st.error(f"youtube-transcript-api 오류: {e}")
        return None, "API 오류"
    return None, "알 수 없는 이유"


# --- 대안 API (신뢰도 낮음, 최후의 수단) ---
def get_transcript_alternative_apis(video_id):
    """대안 API들을 사용해서 자막 가져오기 (신뢰도 낮음)"""
    progress_placeholder = st.empty()
    log_messages = []
    
    services = [
        # {
        #     'name': 'YouTube Transcript API (RapidAPI - 유료/키필요)',
        #     'url': f'https://youtube-transcript-api.p.rapidapi.com/transcript?video_id={video_id}',
        #     'headers': {'X-RapidAPI-Host': 'youtube-transcript-api.p.rapidapi.com', 'X-RapidAPI-Key': 'YOUR_RAPIDAPI_KEY'} # 키 필요
        # },
        # 아래 API들은 공개된 무료 API로, 현재 작동하지 않을 가능성이 매우 높습니다.
        # 실제 사용시에는 작동 여부를 확인하고, API 키가 필요한 경우 적절히 처리해야 합니다.
        {
            'name': 'Unofficial YouTube Subtitle API (Heroku)',
            'url': f'https://youtube-subtitles-api.herokuapp.com/api/subtitles/{video_id}',
            'headers': {}
        }
        # AssemblyAI Whisper API 등은 유료이며 API 키가 필요합니다.
    ]
    
    if not services:
        return None

    for i, service in enumerate(services):
        try:
            progress_placeholder.info(f"🔄 대안 API: {service['name']} 시도 중... ({i+1}/{len(services)})")
            
            response = requests.get(service['url'], headers=service.get('headers', {}), timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                transcript_text = None
                
                if isinstance(data, list):
                    transcript_text = ' '.join([
                        item.get('text', '') or item.get('transcript', '') or str(item) 
                        for item in data if isinstance(item, dict)
                    ])
                elif isinstance(data, dict):
                    if 'transcript' in data:
                        if isinstance(data['transcript'], list):
                            transcript_text = ' '.join([item.get('text', '') for item in data['transcript'] if isinstance(item, dict)])
                        else:
                            transcript_text = str(data['transcript'])
                    elif 'subtitles' in data:
                        transcript_text = str(data['subtitles'])
                    elif 'text' in data:
                        transcript_text = str(data['text'])
                
                if transcript_text and len(transcript_text.strip()) > 50: # 최소 길이 기준
                    progress_placeholder.success(f"✅ 대안 API: {service['name']} 성공!")
                    return transcript_text.strip()
                else:
                    log_messages.append(f"⚠️ {service['name']}: 자막 내용이 너무 짧거나 없음 (Status: {response.status_code})")
                    
            else:
                log_messages.append(f"❌ {service['name']}: HTTP {response.status_code}")
                    
        except requests.exceptions.RequestException as e:
            log_messages.append(f"❌ {service['name']}: 네트워크 오류 {str(e)[:50]}...")
        except Exception as e:
            log_messages.append(f"❌ {service['name']}: 일반 오류 {str(e)[:50]}...")
            continue
    
    progress_placeholder.empty()
    if log_messages:
        with st.expander("🔍 대안 API 상세 로그 보기"):
            for msg in log_messages:
                st.write(msg)
    return None

# --- YouTube 직접 스크래핑 (신뢰도 낮음, 최후의 수단) ---
def get_transcript_youtube_direct(video_id):
    """YouTube에서 직접 자막 정보 가져오기 (스크래핑, 신뢰도 낮음)"""
    progress_placeholder = st.empty()
    log_messages = []

    try:
        progress_placeholder.info("🔄 YouTube 직접 스크래핑 시도...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7', # 한국어 우선
        }
        url = f"https://www.youtube.com/watch?v={video_id}"
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            if 'captionTracks' in response.text:
                # 한국어 자막 우선 탐색, 없으면 영어, 없으면 첫번째 자막
                lang_preferences = ['ko', 'en']
                caption_url = None

                # 정규식으로 모든 captionTracks 추출
                caption_tracks_json_match = re.search(r'"captionTracks":(\[.*?\])', response.text)
                if caption_tracks_json_match:
                    caption_tracks_json_str = caption_tracks_json_match.group(1)
                    try:
                        caption_tracks_data = json.loads(caption_tracks_json_str)
                        
                        # 선호 언어 자막 찾기
                        for lang in lang_preferences:
                            for track in caption_tracks_data:
                                if track.get("languageCode") == lang and "baseUrl" in track:
                                    caption_url = track["baseUrl"].replace('\\u0026', '&')
                                    log_messages.append(f"INFO: 직접 스크래핑 - {lang} 자막 URL 발견")
                                    break
                            if caption_url:
                                break
                        
                        # 선호 언어 자막 없으면 첫번째 사용 가능한 자막
                        if not caption_url and caption_tracks_data:
                            for track in caption_tracks_data:
                                if "baseUrl" in track:
                                    caption_url = track["baseUrl"].replace('\\u0026', '&')
                                    log_messages.append(f"INFO: 직접 스크래핑 - 사용 가능한 첫번째 자막 URL ({track.get('languageCode', 'unknown')}) 발견")
                                    break
                    except json.JSONDecodeError:
                        log_messages.append("ERROR: 직접 스크래핑 - captionTracks JSON 파싱 실패")


                if caption_url:
                    caption_response = requests.get(caption_url, headers=headers, timeout=10)
                    if caption_response.status_code == 200:
                        try:
                            root = ET.fromstring(caption_response.content)
                            transcript_parts = [elem.text.strip() for elem in root.findall('.//text') if elem.text]
                            if transcript_parts:
                                full_transcript = ' '.join(transcript_parts)
                                if len(full_transcript) > 50: # 최소 길이 기준
                                    progress_placeholder.success("✅ YouTube 직접 스크래핑 성공!")
                                    return full_transcript
                                else:
                                    log_messages.append("WARNING: 직접 스크래핑 - 자막 내용이 너무 짧음")
                        except ET.ParseError:
                            log_messages.append("ERROR: 직접 스크래핑 - 자막 XML 파싱 실패")
                    else:
                        log_messages.append(f"ERROR: 직접 스크래핑 - 자막 URL 접근 실패 (Status: {caption_response.status_code})")
                else:
                    log_messages.append("WARNING: 직접 스크래핑 - 유효한 자막 URL을 찾지 못함")
            else:
                log_messages.append("WARNING: 직접 스크래핑 - 페이지 내 'captionTracks' 정보 없음")
        else:
            log_messages.append(f"ERROR: 직접 스크래핑 - YouTube 페이지 접근 실패 (Status: {response.status_code})")

    except requests.exceptions.RequestException as e:
        log_messages.append(f"ERROR: 직접 스크래핑 - 네트워크 오류: {str(e)}")
    except Exception as e:
        log_messages.append(f"ERROR: 직접 스크래핑 - 일반 오류: {str(e)}")
    
    progress_placeholder.empty()
    if log_messages:
        with st.expander("🔍 직접 스크래핑 상세 로그 보기"):
            for msg in log_messages:
                st.write(msg)
    return None


# --- 모든 방법 통합 ---
def get_transcript(video_id, preferred_languages=['ko', 'en']):
    """모든 방법을 시도해서 자막 가져오기"""
    
    # 방법 1: youtube-transcript-api (가장 안정적)
    st.info("🔄 방법 1: YouTube API (라이브러리) 시도 중...")
    transcript_text, method = get_transcript_from_youtube_api(video_id, preferred_languages)
    if transcript_text:
        st.success(f"✅ {method} 통해 자막 확보!")
        return transcript_text, method, len(transcript_text)
    
    # 방법 2: YouTube 직접 스크래핑 (덜 안정적)
    st.info("🔄 방법 2: YouTube 직접 스크래핑 시도 중...")
    transcript_text = get_transcript_youtube_direct(video_id)
    if transcript_text:
        st.success("✅ 직접 스크래핑 통해 자막 확보!")
        return transcript_text, "직접 스크래핑", len(transcript_text)

    # 방법 3: 대안 API (매우 불안정, 거의 사용 안함)
    # st.info("🔄 방법 3: 대안 API들 시도 중...")
    # transcript_text = get_transcript_alternative_apis(video_id)
    # if transcript_text:
    #     st.success("✅ 대안 API 통해 자막 확보!")
    #     return transcript_text, "대안 API", len(transcript_text)
    
    return None, None, None

# --- Gemini 요약 ---
def summarize_text(text, api_key):
    """Gemini로 요약 생성 - 개선된 버전"""
    try:
        genai.configure(api_key=api_key)
        
        max_length = 30000  # Gemini 1.5 모델들은 컨텍스트 윈도우가 크지만, 비용과 시간 고려
        if len(text) > max_length:
            text = text[:max_length] + "... (내용이 너무 길어 일부만 요약합니다)"
        
        # 안정적인 모델들을 순서대로 시도 (Flash가 빠르고 저렴, Pro는 더 강력)
        models_to_try = ['gemini-1.5-flash-latest', 'gemini-1.5-pro-latest', 'gemini-pro'] 
        
        for model_name in models_to_try:
            st.info(f"🔄 Gemini 모델 '{model_name}'으로 요약 시도 중...")
            try:
                model = genai.GenerativeModel(
                    model_name,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.3, # 약간의 창의성, 하지만 사실 기반
                        top_p=0.9,       # 다양한 단어 선택
                        top_k=40,        # 상위 40개 단어 고려
                        max_output_tokens=2048, # 충분한 요약 길이
                    ),
                    safety_settings=[ # 안전 설정 완화 (필요시 조절)
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    ]
                )
                
                prompt = f"""당신은 전문적인 YouTube 영상 분석가입니다. 제공된 영상 자막을 바탕으로, 다음 요구사항에 맞춰 한국어로 명확하고 간결하게 요약해주세요.

**영상 자막:**
---
{text}
---

**요약 형식:**

## 📌 영상의 핵심 주제
이 영상이 다루는 주요 주제나 메시지를 한두 문장으로 명료하게 설명해주세요.

## 🔑 주요 내용 포인트 (3-5개)
영상에서 가장 중요하다고 생각되는 핵심 내용들을 번호 목록으로 3개에서 5개 사이로 정리해주세요. 각 항목은 구체적이면서도 이해하기 쉬워야 합니다.
1.  [첫 번째 핵심 내용]
2.  [두 번째 핵심 내용]
3.  [세 번째 핵심 내용]
    (필요에 따라 4번째, 5번째 내용 추가)

## 💡 결론 및 시사점
영상의 결론은 무엇이며, 시청자가 얻을 수 있는 교훈이나 생각해볼 점은 무엇인지 간략히 기술해주세요. 만약 영상이 특정 행동을 촉구한다면 그것도 언급해주세요.

**주의사항:**
- 반드시 한국어로 작성해주세요.
- 원본 자막의 내용을 충실히 반영하되, 창의적으로 재구성하지 마세요.
- 전문 용어는 쉽게 풀어서 설명하거나, 필요한 경우 간략히 부연해주세요.
"""
                
                response = model.generate_content(prompt)
                
                if response.parts:
                    return response.text
                elif response.prompt_feedback and response.prompt_feedback.block_reason:
                    st.error(f"콘텐츠 안전 문제로 Gemini 응답이 차단되었습니다: {response.prompt_feedback.block_reason}")
                    return f"❌ 요약 생성 실패: Gemini API가 콘텐츠 안전 문제로 응답을 차단했습니다 ({response.prompt_feedback.block_reason}). 다른 비디오를 시도해보세요."
                else:
                    st.warning(f"'{model_name}' 모델에서 요약 내용을 받지 못했습니다. 다음 모델을 시도합니다.")
                    continue # 다음 모델 시도
                
            except Exception as model_error:
                error_msg_lower = str(model_error).lower()
                if any(keyword in error_msg_lower for keyword in ['api key not valid', 'permission denied', 'authentication']):
                    st.error("❌ Gemini API 키가 올바르지 않거나 권한이 없습니다. 키를 확인해주세요.")
                    return "❌ API 키 오류: Gemini API 키가 올바르지 않거나 권한이 없습니다."
                elif 'quota' in error_msg_lower or 'limit' in error_msg_lower:
                    st.error(f"API 할당량을 초과했습니다 ({model_name}). 다른 키를 사용하거나 잠시 후 다시 시도해주세요.")
                    # 다음 모델을 시도할 수도 있지만, 할당량 문제면 다른 모델도 마찬가지일 가능성
                    if model_name == models_to_try[-1]: # 마지막 모델 시도였으면
                        return "❌ API 할당량 초과: 사용량이 한도를 초과했습니다."
                    continue
                elif any(keyword in error_msg_lower for keyword in ['model_not_found', 'not found', '404', 'unavailable']):
                    st.warning(f"'{model_name}' 모델을 찾을 수 없거나 현재 사용할 수 없습니다. 다음 모델을 시도합니다.")
                    continue
                else: # 기타 모델 오류
                    st.warning(f"'{model_name}' 모델 요약 중 오류 발생: {str(model_error)[:100]}... 다음 모델을 시도합니다.")
                    continue
        
        st.error("모든 Gemini 모델에서 요약 생성에 실패했습니다.")
        return "❌ 요약 생성 실패: 모든 Gemini 모델에서 요약을 가져오지 못했습니다. API 키, 네트워크 상태를 확인하거나 잠시 후 다시 시도해주세요."
        
    except genai.types.generation_types.BlockedPromptException as bpe: # 콘텐츠 안전 차단
        st.error(f"콘텐츠 안전 문제로 Gemini 응답이 차단되었습니다: {bpe}")
        return f"❌ 요약 생성 실패: Gemini API가 콘텐츠 안전 문제로 요청을 차단했습니다. 다른 비디오를 시도해보세요."
    except Exception as e: # 전반적인 오류 (API 키 설정 실패 등)
        error_msg = str(e).lower()
        if 'api_key' in error_msg:
            st.error("❌ API 키 오류: Gemini API 키 설정 중 문제가 발생했습니다. 키를 확인해주세요.")
            return "❌ API 키 오류: Gemini API 키가 올바르지 않거나 설정에 실패했습니다."
        elif 'quota' in error_msg:
            st.error("❌ 할당량 초과: API 사용량이 한도를 초과했습니다.")
            return "❌ 할당량 초과: API 사용량이 한도를 초과했습니다."
        else:
            st.error(f"❌ 요약 생성 중 알 수 없는 오류 발생: {e}")
            return f"❌ 요약 생성 실패: {e}"

# --- Streamlit UI ---
def main():
    st.set_page_config(
        page_title="YouTube 자막 요약기 (개선판)",
        page_icon="📺✨"
    )
    
    st.title("📺 YouTube 자막 요약기 ✨")
    st.write("YouTube 비디오의 자막을 추출하고 Gemini AI로 요약합니다.")
    st.caption("`youtube-transcript-api` 라이브러리 및 Gemini API 사용")

    with st.sidebar:
        st.header("⚙️ 설정")
        gemini_api_key = st.text_input(
            "🔑 Gemini API Key",
            type="password",
            help="Google AI Studio (Makersuite)에서 발급받은 API 키를 입력하세요."
        )
        if gemini_api_key:
            st.success("API 키가 입력되었습니다.", icon="✅")
        
        st.markdown("[API 키 발급받기 (Google AI Studio)](https://makersuite.google.com/app/apikey)")
        
        st.subheader("자막 언어 설정")
        lang_options = {
            "한국어 우선 (ko -> en)": ['ko', 'en'],
            "영어 우선 (en -> ko)": ['en', 'ko'],
            "한국어만 (ko)": ['ko'],
            "영어만 (en)": ['en'],
        }
        selected_lang_key = st.selectbox(
            "선호 자막 언어 순서:",
            options=list(lang_options.keys()),
            index=0
        )
        preferred_languages = lang_options[selected_lang_key]

    video_input = st.text_input(
        "🎥 YouTube URL 또는 비디오 ID",
        placeholder="예: https://www.youtube.com/watch?v=VIDEO_ID 또는 VIDEO_ID",
        help="YouTube 비디오의 전체 URL 또는 11자리 비디오 ID를 입력하세요."
    )
    
    if st.button("🚀 자막 추출 및 AI 요약", type="primary", use_container_width=True):
        if not gemini_api_key:
            st.error("❌ Gemini API Key를 사이드바에 입력해주세요!")
            return
        
        if not video_input:
            st.error("❌ YouTube URL 또는 비디오 ID를 입력해주세요!")
            return
        
        video_id = extract_video_id(video_input)
        if not video_id:
            st.error("❌ 유효한 YouTube URL 또는 비디오 ID가 아닙니다. 다시 확인해주세요.")
            return
            
        st.info(f"🎯 추출된 비디오 ID: {video_id}")
        
        transcript_text, method, length = None, None, None
        with st.spinner("📄 자막 가져오는 중... 이 작업은 몇 초 정도 소요될 수 있습니다."):
            transcript_text, method, length = get_transcript(video_id, preferred_languages)
        
        if not transcript_text:
            st.error("❌ 자막을 가져올 수 없었습니다. 다음을 확인해주세요:")
            with st.expander("자막 추출 실패 시 확인 사항", expanded=True):
                st.markdown("""
                - 비디오에 자막이 실제로 존재하는지 (특히 선택한 언어로)
                - 비디오가 공개 상태인지 (비공개, 일부 공개, 연령 제한 비디오는 어려울 수 있음)
                - 매우 짧거나 내용이 없는 비디오는 아닌지
                - 드물게 YouTube 자체의 일시적인 문제일 수도 있습니다.
                
                **다른 비디오로 시도해보거나, 잠시 후 다시 시도해주세요.**
                """)
            return
        
        st.success(f"✅ 자막 추출 성공! (방법: {method}, 길이: {length:,}자)")
        
        tab1, tab2 = st.tabs(["📜 **원본 자막**", "🤖 **AI 요약**"])
        
        with tab1:
            st.markdown("### 📜 원본 자막")
            st.text_area(
                "추출된 자막 내용:",
                transcript_text,
                height=300,
                key="transcript_display"
            )
            st.download_button(
                "📥 자막 다운로드 (.txt)",
                transcript_text,
                f"transcript_{video_id}.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        with tab2:
            st.markdown("### 🤖 AI 요약 (Gemini)")
            with st.spinner("🧠 Gemini AI가 요약 생성 중... 잠시만 기다려주세요."):
                summary = summarize_text(transcript_text, gemini_api_key)
            
            if "❌" in summary: # 요약 실패 시
                st.error(summary)
            else:
                st.success("✅ AI 요약 생성 완료!")
                st.markdown(summary)
                st.download_button(
                    "📥 요약 다운로드 (.md)",
                    summary,
                    f"summary_{video_id}.md",
                    mime="text/markdown",
                    use_container_width=True
                )

if __name__ == "__main__":
    main()
