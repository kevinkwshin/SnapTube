import streamlit as st
import requests
import google.generativeai as genai
import re
from urllib.parse import urlparse, parse_qs
import json
import xml.etree.ElementTree as ET
import html # HTML 엔티티 처리를 위해 추가

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
    elif re.fullmatch(r"^[a-zA-Z0-9_-]{11}$", url): # 11자리 비디오 ID 직접 입력 (정규식 수정: fullmatch)
        return url
    else:
        return None

# --- 자막 추출 로직 (youtube-transcript-api 사용 최우선) ---
def get_transcript_from_youtube_api(video_id, preferred_languages=['ko', 'en']):
    """youtube-transcript-api 라이브러리를 사용하여 자막 가져오기"""
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # 1. 사용자가 명시적으로 생성한 선호 언어 자막 찾기
        for lang_code in preferred_languages:
            try:
                transcript = transcript_list.find_manually_created_transcript([lang_code])
                fetched_transcript = transcript.fetch()
                st.caption(f"YouTube API: '{lang_code}' 수동 생성 자막 발견.")
                return ' '.join([item['text'] for item in fetched_transcript]), f"YouTube API ({lang_code}, 수동)"
            except NoTranscriptFound:
                continue
        
        # 2. 자동 생성된 선호 언어 자막 찾기
        for lang_code in preferred_languages:
            try:
                transcript = transcript_list.find_generated_transcript([lang_code])
                fetched_transcript = transcript.fetch()
                st.caption(f"YouTube API: '{lang_code}' 자동 생성 자막 발견.")
                return ' '.join([item['text'] for item in fetched_transcript]), f"YouTube API ({lang_code}, 자동)"
            except NoTranscriptFound:
                continue
        
        # 3. 선호 언어가 없으면, 사용 가능한 아무 수동 자막이나
        try:
            for available_transcript in transcript_list:
                if not available_transcript.is_generated:
                    fetched_transcript = available_transcript.fetch()
                    st.caption(f"YouTube API: '{available_transcript.language_code}' 수동 생성 자막 발견 (선호 언어 아님).")
                    return ' '.join([item['text'] for item in fetched_transcript]), f"YouTube API ({available_transcript.language_code}, 수동)"
        except: # 모든 종류의 오류 발생 시 다음 단계로
            pass

        # 4. 정말 아무것도 없으면 첫번째 사용가능한 자동 생성 자막
        try:
            for available_transcript in transcript_list:
                if available_transcript.is_generated:
                    fetched_transcript = available_transcript.fetch()
                    st.caption(f"YouTube API: '{available_transcript.language_code}' 자동 생성 자막 발견 (선호 언어 아님).")
                    return ' '.join([item['text'] for item in fetched_transcript]), f"YouTube API ({available_transcript.language_code}, 자동)"
        except:
             pass


    except TranscriptsDisabled:
        st.warning(f"자막 추출 실패 (YouTube API): [{video_id}] 비디오에 대해 자막이 비활성화되어 있습니다.")
        return None, "자막 비활성화"
    except NoTranscriptFound: # 이 예외는 find_transcript 계열에서 발생. 위 로직으로 인해 거의 발생 안 함.
        st.warning(f"자막 추출 실패 (YouTube API): [{video_id}] 비디오에 대해 어떤 언어의 자막도 찾을 수 없습니다.")
        return None, "자막 없음"
    except Exception as e:
        st.error(f"자막 추출 중 오류 (YouTube API): {e}")
        return None, "API 오류"
    
    st.warning("자막 추출 실패 (YouTube API): 사용 가능한 자막을 찾지 못했습니다.")
    return None, "자막 없음 (API 시도 후)"

# --- YouTube 직접 스크래핑 (신뢰도 낮음, 개선된 버전) ---
def get_transcript_youtube_direct(video_id, preferred_languages=['ko', 'en']):
    """YouTube에서 직접 자막 정보 가져오기 (스크래핑, 신뢰도 낮음)"""
    progress_placeholder = st.empty()
    log_messages = []

    try:
        progress_placeholder.info(f"🔄 YouTube 직접 스크래핑 시도 (선호 언어: {', '.join(preferred_languages)})...")
        
        accept_lang_header_parts = []
        for i, lang_code in enumerate(preferred_languages):
            q = 0.9 - i * 0.1
            accept_lang_header_parts.append(f"{lang_code}-{lang_code.upper()};q={q}")
            accept_lang_header_parts.append(f"{lang_code};q={q-0.05}")
        accept_lang_header_parts.append("en-US;q=0.5,en;q=0.4")
        accept_lang_header = ','.join(accept_lang_header_parts)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36', # 최신 브라우저 버전으로
            'Accept-Language': accept_lang_header,
        }
        # &hl 파라미터로 언어 힌트 제공
        url = f"https://www.youtube.com/watch?v={video_id}&hl={preferred_languages[0] if preferred_languages else 'en'}"
        response = requests.get(url, headers=headers, timeout=20) # 타임아웃 증가
        
        if response.status_code == 200:
            page_content = response.text
            caption_url = None
            source_type = None # 'playerCaptions' or 'captionTracks'

            # 1. playerCaptionsTracklistRenderer (최신 방식일 가능성)
            match_player_captions = re.search(r'"playerCaptionsTracklistRenderer":\s*(\{.*?\})', page_content)
            if match_player_captions:
                source_type = 'playerCaptions'
                try:
                    captions_json_str = match_player_captions.group(1)
                    # JSON 문자열 내 유니코드 이스케이프 시퀀스 처리 (\u0026 -> &)
                    captions_json_str = captions_json_str.encode('utf-8').decode('unicode_escape')
                    captions_data = json.loads(captions_json_str)
                    
                    if "captionTracks" in captions_data:
                        caption_tracks_list = captions_data["captionTracks"]
                        
                        # 선호 언어 자막 찾기 (수동 > 자동)
                        for lang_code in preferred_languages:
                            for track in caption_tracks_list:
                                if track.get("languageCode") == lang_code and "baseUrl" in track and track.get("kind") != "asr": # 수동
                                    caption_url = track["baseUrl"]
                                    log_messages.append(f"INFO ({source_type}): '{lang_code}' 수동 자막 URL 발견")
                                    break
                            if caption_url: break
                        
                        if not caption_url: # 수동 없으면 자동
                            for lang_code in preferred_languages:
                                for track in caption_tracks_list:
                                    if track.get("languageCode") == lang_code and "baseUrl" in track and track.get("kind") == "asr": # 자동
                                        caption_url = track["baseUrl"]
                                        log_messages.append(f"INFO ({source_type}): '{lang_code}' 자동 자막 URL 발견")
                                        break
                                if caption_url: break
                        
                        # 그래도 없으면 사용 가능한 첫 번째 자막 (수동 > 자동)
                        if not caption_url and caption_tracks_list:
                            for track_type_priority in [lambda t: t.get("kind") != "asr", lambda t: t.get("kind") == "asr"]: # 수동 우선
                                for track in caption_tracks_list:
                                    if "baseUrl" in track and track_type_priority(track):
                                        caption_url = track["baseUrl"]
                                        log_messages.append(f"INFO ({source_type}): 첫 사용 가능 자막 ({track.get('languageCode', 'N/A')}, {'수동' if track.get('kind') != 'asr' else '자동'}) URL 발견")
                                        break
                                if caption_url: break
                except json.JSONDecodeError as e:
                    log_messages.append(f"ERROR ({source_type}): JSON 파싱 실패 - {e}")
                except Exception as e:
                    log_messages.append(f"ERROR ({source_type}): 처리 중 오류 - {e}")

            # 2. 기존 captionTracks (위에서 못 찾았을 경우 또는 다른 구조)
            if not caption_url:
                source_type = 'legacyCaptionTracks'
                caption_tracks_match = re.search(r'"captionTracks":(\[.*?\])', page_content)
                if caption_tracks_match:
                    try:
                        caption_tracks_json_str = caption_tracks_match.group(1).encode('utf-8').decode('unicode_escape')
                        caption_tracks_list = json.loads(caption_tracks_json_str)

                        for lang_code in preferred_languages: # 수동
                            for track in caption_tracks_list:
                                if track.get("languageCode") == lang_code and "baseUrl" in track and track.get("kind") != "asr":
                                    caption_url = track["baseUrl"]
                                    log_messages.append(f"INFO ({source_type}): '{lang_code}' 수동 자막 URL 발견")
                                    break
                            if caption_url: break
                        
                        if not caption_url: # 자동
                            for lang_code in preferred_languages:
                                for track in caption_tracks_list:
                                    if track.get("languageCode") == lang_code and "baseUrl" in track and track.get("kind") == "asr":
                                        caption_url = track["baseUrl"]
                                        log_messages.append(f"INFO ({source_type}): '{lang_code}' 자동 자막 URL 발견")
                                        break
                                if caption_url: break
                        
                        if not caption_url and caption_tracks_list: # 첫 사용 가능
                            for track_type_priority in [lambda t: t.get("kind") != "asr", lambda t: t.get("kind") == "asr"]:
                                for track in caption_tracks_list:
                                    if "baseUrl" in track and track_type_priority(track):
                                        caption_url = track["baseUrl"]
                                        log_messages.append(f"INFO ({source_type}): 첫 사용 가능 자막 ({track.get('languageCode', 'N/A')}, {'수동' if track.get('kind') != 'asr' else '자동'}) URL 발견")
                                        break
                                if caption_url: break
                    except json.JSONDecodeError as e:
                        log_messages.append(f"ERROR ({source_type}): JSON 파싱 실패 - {e}")
                    except Exception as e:
                        log_messages.append(f"ERROR ({source_type}): 처리 중 오류 - {e}")
            
            if caption_url:
                # URL에 format=srv3 또는 ttml 등이 누락된 경우 추가 시도 (필수는 아님)
                if 'format=' not in caption_url:
                    caption_url += "&format=srv3" # or "format=ttml" or "format=vtt"

                log_messages.append(f"DEBUG: 최종 자막 URL: {caption_url}")
                caption_response = requests.get(caption_url, headers=headers, timeout=15)
                if caption_response.status_code == 200:
                    try:
                        transcript_text = caption_response.text
                        # XML 형태의 자막에서 텍스트 추출
                        root = ET.fromstring(transcript_text)
                        transcript_parts = []
                        # 다양한 태그 탐색: text, p, s (오래된 형식)
                        for elem_tag in ['text', 'p', 's']: 
                            for elem in root.findall(f'.//{elem_tag}'):
                                if elem.text:
                                    transcript_parts.append(elem.text.strip())
                        
                        if transcript_parts:
                            full_transcript = ' '.join(transcript_parts)
                            full_transcript = html.unescape(full_transcript) # HTML 엔티티 디코딩
                            full_transcript = re.sub(r'\s+', ' ', full_transcript).strip() # 중복 공백 제거
                            
                            if len(full_transcript) > 30: # 최소 길이 기준 완화
                                progress_placeholder.success("✅ YouTube 직접 스크래핑 성공!")
                                return full_transcript
                            else:
                                log_messages.append(f"WARNING: 직접 스크래핑 - 자막 내용이 너무 짧음 ({len(full_transcript)}자)")
                        else:
                            log_messages.append("WARNING: 직접 스크래핑 - XML에서 텍스트 요소 찾기 실패")
                    except ET.ParseError:
                        log_messages.append("ERROR: 직접 스크래핑 - 자막 XML 파싱 실패. 원본 내용 일부:\n" + caption_response.text[:200])
                    except Exception as parse_e:
                        log_messages.append(f"ERROR: 직접 스크래핑 - 자막 파싱 중 예외: {parse_e}")
                else:
                    log_messages.append(f"ERROR: 직접 스크래핑 - 자막 URL ({caption_url}) 접근 실패 (Status: {caption_response.status_code})")
            else:
                log_messages.append("WARNING: 직접 스크래핑 - 유효한 자막 URL을 최종적으로 찾지 못함")
        else:
            log_messages.append(f"ERROR: 직접 스크래핑 - YouTube 페이지 접근 실패 (Status: {response.status_code})")

    except requests.exceptions.Timeout:
        log_messages.append(f"ERROR: 직접 스크래핑 - 요청 시간 초과")
    except requests.exceptions.RequestException as e:
        log_messages.append(f"ERROR: 직접 스크래핑 - 네트워크 오류: {str(e)}")
    except Exception as e:
        log_messages.append(f"ERROR: 직접 스크래핑 - 일반 오류: {str(e)}")
    
    progress_placeholder.empty()
    if log_messages:
        with st.expander("🔍 직접 스크래핑 상세 로그 보기 (신뢰도 낮음)", expanded=False):
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
    
    # 방법 2: YouTube 직접 스크래핑 (덜 안정적, fallback)
    st.warning("⚠️ YouTube API 라이브러리 실패. 직접 스크래핑 시도 중 (신뢰도 낮음)...")
    transcript_text = get_transcript_youtube_direct(video_id, preferred_languages) # preferred_languages 전달
    if transcript_text:
        st.success("✅ 직접 스크래핑 통해 자막 확보!")
        return transcript_text, "직접 스크래핑", len(transcript_text)
    
    return None, None, None

# --- Gemini 요약 ---
def summarize_text(text, api_key):
    """Gemini로 요약 생성 - 개선된 버전"""
    try:
        genai.configure(api_key=api_key)
        
        # Gemini 1.5 Flash는 최대 1M 토큰, Pro는 1M(일반)/2M(특정 요청) 토큰 지원.
        # 하지만 너무 긴 텍스트는 요약 품질 저하 및 비용/시간 증가 우려. 적절히 제한.
        # 한국어는 글자당 토큰 수가 영어보다 많으므로, 글자 수 기준을 영어보다 보수적으로.
        # 예: 1글자 ~ 0.5~1 토큰. 30k 글자면 약 15k~30k 토큰.
        max_chars = 30000 
        if len(text) > max_chars:
            text_to_summarize = text[:max_chars]
            st.caption(f"자막이 너무 길어 앞부분 {max_chars}자만 요약에 사용합니다.")
        else:
            text_to_summarize = text
        
        models_to_try = [
            'gemini-1.5-flash-latest', 
            'gemini-1.5-pro-latest',
            'gemini-pro' # Fallback
        ] 
        
        st.info(f"사용 가능한 Gemini 모델 순서: {', '.join(models_to_try)}")

        for model_name in models_to_try:
            st.info(f"🔄 Gemini 모델 '{model_name}'으로 요약 시도 중...")
            try:
                model = genai.GenerativeModel(
                    model_name,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.2, # 좀 더 사실 기반
                        top_p=0.95,      # 다양한 단어 선택은 유지
                        top_k=64,        # 고려 단어 수 증가 (최신 모델은 더 잘 처리)
                        max_output_tokens=4096, # 요약 결과 최대 토큰 (Flash는 8192, Pro는 8192)
                    ),
                    # 안전 설정은 콘텐츠에 따라 조절. 기본값을 사용하거나 필요시 완화.
                    safety_settings=[ 
                        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    ]
                )
                
                prompt = f"""제공된 YouTube 영상 자막을 바탕으로, 다음 형식에 맞춰 한국어로 명확하고 간결하게 요약해주세요.

**영상 자막:**
---
{text_to_summarize}
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
- 원본 자막의 내용을 충실히 반영하되, 불필요한 반복이나 사견은 배제해주세요.
- 전문 용어는 쉽게 풀어서 설명하거나, 필요한 경우 간략히 부연해주세요.
"""
                
                response = model.generate_content(prompt)
                
                if response.parts:
                    return response.text
                elif response.prompt_feedback and response.prompt_feedback.block_reason:
                    reason = response.prompt_feedback.block_reason
                    st.error(f"콘텐츠 안전 문제로 Gemini 응답이 차단되었습니다 ({model_name}): {reason}")
                    if model_name == models_to_try[-1]: # 마지막 모델 시도였으면
                        return f"❌ 요약 생성 실패: Gemini API가 콘텐츠 안전 문제로 응답을 차단했습니다 ({reason}). 다른 비디오를 시도해보거나, 자막 내용을 확인해주세요."
                    st.warning("다른 모델로 재시도합니다...")
                    continue # 다음 모델 시도
                else:
                    st.warning(f"'{model_name}' 모델에서 요약 내용을 받지 못했습니다 (응답 비어있음). 다음 모델을 시도합니다.")
                    continue 
                
            except Exception as model_error:
                error_msg_lower = str(model_error).lower()
                st.warning(f"'{model_name}' 모델 요약 중 오류 발생: {str(model_error)[:150]}...")
                if any(keyword in error_msg_lower for keyword in ['api key not valid', 'permission denied', 'authentication']):
                    st.error("❌ Gemini API 키가 올바르지 않거나 권한이 없습니다. 키를 확인해주세요.")
                    return "❌ API 키 오류: Gemini API 키가 올바르지 않거나 권한이 없습니다."
                elif 'quota' in error_msg_lower or 'limit' in error_msg_lower or 'resource_exhausted' in error_msg_lower:
                    st.error(f"API 할당량을 초과했거나 리소스가 부족합니다 ({model_name}). 다른 키를 사용하거나 잠시 후 다시 시도해주세요.")
                    if model_name == models_to_try[-1]:
                        return "❌ API 할당량 초과 또는 리소스 부족: 사용량이 한도를 초과했거나 서버 리소스가 일시적으로 부족합니다."
                    continue
                elif any(keyword in error_msg_lower for keyword in ['model_not_found', 'not found', '404', 'unavailable']):
                    st.warning(f"'{model_name}' 모델을 찾을 수 없거나 현재 사용할 수 없습니다.")
                    # 다음 모델 시도
                # 다른 특정 오류들도 여기서 처리 가능
                if model_name == models_to_try[-1]: # 마지막 모델까지 실패
                    st.error(f"모든 모델 시도 후에도 '{model_name}'에서 요약 생성 실패.")
                    break # 루프 종료
                st.warning("다른 모델로 재시도합니다...")
                continue
        
        st.error("모든 Gemini 모델에서 요약 생성에 실패했습니다.")
        return "❌ 요약 생성 실패: 모든 Gemini 모델에서 요약을 가져오지 못했습니다. API 키, 네트워크 상태, 할당량을 확인하거나 잠시 후 다시 시도해주세요."
        
    except genai.types.generation_types.BlockedPromptException as bpe:
        st.error(f"콘텐츠 안전 문제로 Gemini 요청 자체가 차단되었습니다: {bpe}")
        return f"❌ 요약 생성 실패: Gemini API가 콘텐츠 안전 문제로 초기 요청을 차단했습니다. 다른 비디오를 시도해보세요."
    except Exception as e:
        error_msg = str(e).lower()
        if 'api_key' in error_msg:
            st.error("❌ API 키 오류: Gemini API 키 설정 중 문제가 발생했습니다. 키를 확인해주세요.")
            return "❌ API 키 오류: Gemini API 키가 올바르지 않거나 설정에 실패했습니다."
        else:
            st.error(f"❌ 요약 생성 중 알 수 없는 전역 오류 발생: {e}")
            return f"❌ 요약 생성 실패 (전역): {e}"

# --- Streamlit UI ---
def main():
    st.set_page_config(
        page_title="YouTube 자막 요약기 (v2.0)",
        page_icon="📺✨",
        layout="wide"
    )
    
    st.title("📺 YouTube 자막 요약기 ✨")
    st.markdown("YouTube 비디오의 자막을 추출하고 **Gemini AI** (최대 `gemini-1.5-flash-latest`)로 요약합니다.")
    
    with st.sidebar:
        st.header("⚙️ 설정")
        gemini_api_key = st.text_input(
            "🔑 Gemini API Key",
            type="password",
            help="Google AI Studio (Makersuite)에서 발급받은 API 키를 입력하세요."
        )
        if gemini_api_key:
            st.success("API 키가 입력되었습니다.", icon="✅")
        else:
            st.warning("API 키를 입력해주세요.", icon="⚠️")
        
        st.link_button("API 키 발급받기 (Google AI Studio)", "https://makersuite.google.com/app/apikey")
        
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
            index=0,
            help="선택한 순서대로 자막을 탐색합니다. 첫 번째 언어가 없으면 다음 언어를 시도합니다."
        )
        preferred_languages = lang_options[selected_lang_key]

    video_input = st.text_input(
        "🎥 YouTube URL 또는 비디오 ID",
        placeholder="예: https://www.youtube.com/watch?v=dQw4w9WgXcQ 또는 dQw4w9WgXcQ",
        help="YouTube 비디오의 전체 URL 또는 11자리 비디오 ID를 입력하세요."
    )
    
    if st.button("🚀 자막 추출 및 AI 요약", type="primary", use_container_width=True, disabled=(not gemini_api_key)):
        if not gemini_api_key: # 버튼이 disabled되므로 이 경고는 거의 보이지 않음
            st.error("❌ Gemini API Key를 사이드바에 입력해주세요!")
            return
        
        if not video_input:
            st.error("❌ YouTube URL 또는 비디오 ID를 입력해주세요!")
            return
        
        video_id = extract_video_id(video_input)
        if not video_id:
            st.error("❌ 유효한 YouTube URL 또는 비디오 ID 형식이 아닙니다. 다시 확인해주세요.")
            return
            
        st.info(f"🎯 추출된 비디오 ID: {video_id}")
        
        transcript_text, method, length = None, None, None
        with st.spinner("📄 자막 가져오는 중... (최대 30초 소요될 수 있음)"):
            transcript_text, method, length = get_transcript(video_id, preferred_languages)
        
        if not transcript_text:
            st.error("❌ 자막을 가져올 수 없었습니다. 다음을 확인해주세요:")
            with st.expander("자막 추출 실패 시 확인 사항", expanded=True):
                st.markdown("""
                - 비디오에 **자막이 실제로 존재**하는지 (특히 선택한 언어로).
                - 비디오가 **공개 상태**인지 (비공개, 일부 공개, 연령 제한 비디오는 추출이 어려울 수 있음).
                - 매우 짧거나 내용이 없는 비디오는 아닌지.
                - 드물게 YouTube 자체의 일시적인 문제일 수도 있습니다.
                
                **다른 비디오로 시도해보거나, 잠시 후 다시 시도해주세요.**
                """)
            return
        
        st.success(f"✅ 자막 추출 성공! (방법: {method}, 길이: {length:,}자)")
        
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 📜 원본 자막")
            st.text_area(
                "추출된 자막 내용:",
                transcript_text,
                height=400,
                key="transcript_display"
            )
            st.download_button(
                "📥 자막 다운로드 (.txt)",
                transcript_text,
                f"transcript_{video_id}.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        with col2:
            st.markdown("### 🤖 AI 요약 (Gemini)")
            with st.spinner("🧠 Gemini AI가 요약 생성 중... (자막 길이에 따라 몇 초 ~ 몇 분 소요)"):
                summary = summarize_text(transcript_text, gemini_api_key)
            
            if "❌" in summary: # 요약 실패 시
                st.error(summary)
            else:
                st.success("✅ AI 요약 생성 완료!")
                st.markdown(summary) # 마크다운 형식으로 렌더링
                st.download_button(
                    "📥 요약 다운로드 (.md)",
                    summary,
                    f"summary_{video_id}.md",
                    mime="text/markdown", # 마크다운 파일로
                    use_container_width=True
                )

if __name__ == "__main__":
    main()
