# import streamlit as st
# from openai import OpenAI

# # Show title and description.
# st.title("📄 Document question answering")
# st.write(
#     "Upload a document below and ask a question about it – GPT will answer! "
#     "To use this app, you need to provide an OpenAI API key, which you can get [here](https://platform.openai.com/account/api-keys). "
# )

# # Ask user for their OpenAI API key via `st.text_input`.
# # Alternatively, you can store the API key in `./.streamlit/secrets.toml` and access it
# # via `st.secrets`, see https://docs.streamlit.io/develop/concepts/connections/secrets-management
# openai_api_key = st.text_input("OpenAI API Key", type="password")
# if not openai_api_key:
#     st.info("Please add your OpenAI API key to continue.", icon="🗝️")
# else:

#     # Create an OpenAI client.
#     client = OpenAI(api_key=openai_api_key)

#     # Let the user upload a file via `st.file_uploader`.
#     uploaded_file = st.file_uploader(
#         "Upload a document (.txt or .md)", type=("txt", "md")
#     )

#     # Ask the user for a question via `st.text_area`.
#     question = st.text_area(
#         "Now ask a question about the document!",
#         placeholder="Can you give me a short summary?",
#         disabled=not uploaded_file,
#     )

#     if uploaded_file and question:

#         # Process the uploaded file and question.
#         document = uploaded_file.read().decode()
#         messages = [
#             {
#                 "role": "user",
#                 "content": f"Here's a document: {document} \n\n---\n\n {question}",
#             }
#         ]

#         # Generate an answer using the OpenAI API.
#         stream = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=messages,
#             stream=True,
#         )

#         # Stream the response to the app using `st.write_stream`.
#         st.write_stream(stream)

# import streamlit as st

# st.title("🎈 My new app")
# st.write(
#     "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
# )


# import streamlit as st
# from youtube_transcript_api import YouTubeTranscriptApi
# from google import genai
# from google.genai import types
# import re

# def extract_video_id(url):
#     # Extract video ID from various YouTube URL formats
#     patterns = [
#         r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
#         r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
#         r'(?:embed\/)([0-9A-Za-z_-]{11})'
#     ]
    
#     for pattern in patterns:
#         match = re.search(pattern, url)
#         if match:
#             return match.group(1)
#     return url  # If no pattern matches, assume the input is already a video ID

# def get_transcript(video_id):
#     try:
#         ytt_api = YouTubeTranscriptApi()
#         transcript_list = ytt_api.list(video_id)
        
#         fetched = None
#         non_generated_found = False
        
#         # First try to find non-generated transcripts
#         for transcript in transcript_list:
#             if transcript.is_generated == 0:  # get youtube subtitle
#                 fetched = transcript.fetch()
#                 non_generated_found = True
#                 break
        
#         # If no non-generated transcript found, use generated one
#         if not non_generated_found:
#             for transcript in transcript_list:
#                 if transcript.is_generated == 1:
#                     fetched = transcript.fetch()
#                     break
        
#         if fetched is None:
#             return None, "No transcripts available for this video."
            
#         output = ' '.join([f.text for f in fetched])
#         return output, None
        
#     except Exception as e:
#         return None, str(e)

# def summarize_text(text, api_key):
#     try:
#         client = genai.Client(api_key=api_key)
#         model = "gemini-2.5-flash-preview-05-20"
        
#         contents = [
#             types.Content(
#                 role="user",
#                 parts=[
#                     types.Part.from_text(
#                         text=f'Summarize and Write the good readability Report with numberings of text below in their language as Markdown.\n {text}'
#                     ),
#                 ],
#             ),
#         ]
        
#         generate_content_config = types.GenerateContentConfig(
#             response_mime_type="text/plain",
#             system_instruction='You are a Professional writer.',
#             temperature=0.1
#         )
        
#         response = client.models.generate_content(
#             model=model,
#             contents=contents,
#             config=generate_content_config,
#         )
        
#         return response.text, None
        
#     except Exception as e:
#         return None, str(e)

# def main():
#     st.title("SnapTube : Youtube Transcript Summarizer")
#     st.write("Enter your Google API key and YouTube video URL to get a summary of the video's transcript.")
    
#     # API Key input
#     api_key = st.text_input("Enter your Google API Key", type="password")
    
#     # Video URL/ID input
#     video_input = st.text_input("Enter YouTube Video URL or Video ID")
    
#     if st.button("Generate Summary"):
#         if not api_key:
#             st.error("Please enter your Google API Key")
#             return
            
#         if not video_input:
#             st.error("Please enter a YouTube video URL or Video ID")
#             return
            
#         # Extract video ID
#         video_id = extract_video_id(video_input)
        
#         with st.spinner("Fetching transcript..."):
#             transcript, error = get_transcript(video_id)
#             if error:
#                 st.error(f"Error fetching transcript: {error}")
#                 return
                
#             if transcript:
#                 st.subheader("Original Transcript")
#                 st.text_area("Transcript", transcript, height=200)
                
#                 with st.spinner("Generating summary..."):
#                     summary, error = summarize_text(transcript, api_key)
#                     if error:
#                         st.error(f"Error generating summary: {error}")
#                         return
                        
#                     if summary:
#                         st.subheader("Summary")
#                         st.markdown(summary)

# if __name__ == "__main__":
#     main() 

# import streamlit as st
# from youtube_transcript_api import YouTubeTranscriptApi
# from youtube_transcript_api.formatters import TextFormatter
# from google import genai
# from google.genai import types
# import re
# import time
# import random
# import requests
# from urllib.parse import urlparse, parse_qs

# def extract_video_id(url):
#     """Extract video ID from various YouTube URL formats"""
#     if "youtube.com/watch" in url:
#         parsed_url = urlparse(url)
#         return parse_qs(parsed_url.query)['v'][0]
#     elif "youtu.be/" in url:
#         return url.split("youtu.be/")[1].split("?")[0]
#     elif "youtube.com/embed/" in url:
#         return url.split("embed/")[1].split("?")[0]
#     else:
#         # Assume it's already a video ID
#         return url.strip()

# def get_free_proxies():
#     """Get a list of free proxies (you should replace with your own proxy service)"""
#     # 실제 사용시에는 유료 프록시 서비스를 사용하는 것이 좋습니다
#     return [
#         # 예시 - 실제 프록시로 교체하세요
#         # {'http': 'http://proxy1:port', 'https': 'https://proxy1:port'},
#         # {'http': 'http://proxy2:port', 'https': 'https://proxy2:port'},
#     ]

# def get_transcript_with_retry(video_id, max_retries=3, use_proxy=False):
#     """Get transcript with multiple retry strategies"""
    
#     # Strategy 1: Direct request with retry
#     for attempt in range(max_retries):
#         try:
#             st.info(f"시도 {attempt + 1}: 직접 요청...")
#             transcript = YouTubeTranscriptApi.get_transcript(video_id)
#             st.success("✅ 직접 요청 성공!")
#             return transcript, None
#         except Exception as e:
#             st.warning(f"직접 요청 실패 (시도 {attempt + 1}): {str(e)}")
#             if attempt < max_retries - 1:
#                 wait_time = random.uniform(2, 5)
#                 time.sleep(wait_time)
    
#     # Strategy 2: Try with different languages
#     try:
#         st.info("다른 언어 자막으로 시도 중...")
#         transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
#         # Try manual transcripts first
#         for transcript in transcript_list:
#             if not transcript.is_generated:
#                 try:
#                     return transcript.fetch(), None
#                 except:
#                     continue
        
#         # Then try generated transcripts
#         for transcript in transcript_list:
#             if transcript.is_generated:
#                 try:
#                     return transcript.fetch(), None
#                 except:
#                     continue
                    
#     except Exception as e:
#         st.warning(f"언어별 시도 실패: {str(e)}")
    
#     # Strategy 3: Try with proxies if enabled
#     if use_proxy:
#         proxies = get_free_proxies()
#         for i, proxy in enumerate(proxies):
#             try:
#                 st.info(f"프록시 {i+1} 시도 중...")
#                 transcript = YouTubeTranscriptApi.get_transcript(video_id, proxies=proxy)
#                 st.success(f"✅ 프록시 {i+1} 성공!")
#                 return transcript, None
#             except Exception as e:
#                 st.warning(f"프록시 {i+1} 실패: {str(e)}")
#                 continue
    
#     # Strategy 4: Alternative method using direct API call
#     try:
#         st.info("대안 방법 시도 중...")
#         transcript_text, error = get_transcript_alternative(video_id)
#         if transcript_text:
#             # Convert to transcript format
#             transcript = [{'text': transcript_text, 'start': 0, 'duration': 0}]
#             return transcript, None
#     except Exception as e:
#         st.warning(f"대안 방법 실패: {str(e)}")
    
#     return None, "모든 방법이 실패했습니다. 아래 해결 방법을 참고하세요."

# def get_transcript_alternative(video_id):
#     """Alternative method to get transcript"""
#     try:
#         # Try to get auto-generated captions directly
#         url = f"https://www.youtube.com/api/timedtext?lang=en&v={video_id}"
#         response = requests.get(url, timeout=10)
        
#         if response.status_code == 200:
#             import xml.etree.ElementTree as ET
#             root = ET.fromstring(response.content)
#             text_parts = []
            
#             for text_elem in root.findall('.//text'):
#                 if text_elem.text:
#                     text_parts.append(text_elem.text)
            
#             return ' '.join(text_parts), None
#         else:
#             return None, "자동 생성 자막을 가져올 수 없습니다"
    
#     except Exception as e:
#         return None, f"대안 방법 오류: {str(e)}"

# def get_transcript(video_id, use_proxy=False):
#     """Main transcript fetching function"""
#     try:
#         transcript_data, error = get_transcript_with_retry(video_id, use_proxy=use_proxy)
        
#         if error:
#             return None, error
            
#         if transcript_data:
#             # Format transcript text
#             if isinstance(transcript_data, list):
#                 transcript_text = ' '.join([item['text'] for item in transcript_data])
#             else:
#                 transcript_text = transcript_data
                
#             return transcript_text, None
#         else:
#             return None, "트랜스크립트를 가져올 수 없습니다"
            
#     except Exception as e:
#         return None, str(e)

# def summarize_text(text, api_key):
#     """Summarize text using Google Gemini API"""
#     try:
#         client = genai.Client(api_key=api_key)
#         model = "gemini-2.0-flash-exp"  # Updated model name
        
#         contents = [
#             types.Content(
#                 role="user",
#                 parts=[
#                     types.Part.from_text(
#                         text=f'''다음 YouTube 비디오 트랜스크립트를 분석하여 포괄적인 요약을 작성해주세요:

# {text[:8000]}  # Token limit 고려

# 다음 형식으로 구성해주세요:
# 1. **주요 주제/테마**
# 2. **핵심 포인트** (3-5개 요점)
# 3. **중요한 세부사항 또는 예시**
# 4. **결론/시사점**

# 읽기 쉽게 마크다운 형식으로 작성하고, 번호를 매겨주세요.'''
#                     ),
#                 ],
#             ),
#         ]
        
#         generate_content_config = types.GenerateContentConfig(
#             response_mime_type="text/plain",
#             system_instruction='당신은 전문적인 콘텐츠 요약 작가입니다. 명확하고 구조화된 요약을 제공하세요.',
#             temperature=0.1
#         )
        
#         response = client.models.generate_content(
#             model=model,
#             contents=contents,
#             config=generate_content_config,
#         )
        
#         return response.text, None
        
#     except Exception as e:
#         return None, str(e)

# def main():
#     st.set_page_config(
#         page_title="SnapTube: YouTube Transcript Summarizer", 
#         page_icon="📺",
#         layout="wide"
#     )
    
#     st.title("📺 SnapTube: YouTube Transcript Summarizer")
#     st.write("Google API 키와 YouTube 비디오 URL을 입력하여 비디오 트랜스크립트 요약을 받아보세요.")
    
#     # Sidebar configuration
#     with st.sidebar:
#         st.header("⚙️ 설정")
#         use_proxy = st.checkbox(
#             "프록시 사용 (IP 차단시)", 
#             help="IP가 차단된 경우 활성화하세요. 프록시 설정이 필요합니다."
#         )
        
#         show_transcript = st.checkbox("원본 트랜스크립트 표시", value=True)
        
#         st.markdown("---")
#         st.markdown("### 💡 문제 해결 팁")
#         st.markdown("- VPN 사용")
#         st.markdown("- 다른 비디오로 테스트")
#         st.markdown("- 잠시 후 다시 시도")
#         st.markdown("- 클라우드가 아닌 로컬에서 실행")
    
#     # Main inputs
#     col1, col2 = st.columns([2, 1])
    
#     with col1:
#         api_key = st.text_input(
#             "🔑 Google API Key를 입력하세요", 
#             type="password",
#             help="Google AI Studio에서 발급받을 수 있습니다"
#         )
    
#     with col2:
#         st.write("") # spacing
#         if st.button("🔗 API 키 발급받기"):
#             st.markdown("[Google AI Studio로 이동](https://makersuite.google.com/app/apikey)")
    
#     video_input = st.text_input(
#         "🎥 YouTube 비디오 URL 또는 비디오 ID를 입력하세요",
#         placeholder="https://www.youtube.com/watch?v=VIDEO_ID"
#     )
    
#     if st.button("🚀 요약 생성", type="primary", use_container_width=True):
#         if not api_key:
#             st.error("❌ Google API Key를 입력해주세요")
#             return
            
#         if not video_input:
#             st.error("❌ YouTube 비디오 URL 또는 비디오 ID를 입력해주세요")
#             return
        
#         try:
#             # Extract video ID
#             video_id = extract_video_id(video_input)
#             st.info(f"🎯 처리 중인 비디오 ID: {video_id}")
            
#             # Get transcript
#             with st.spinner("📄 트랜스크립트 가져오는 중..."):
#                 transcript, error = get_transcript(video_id, use_proxy=use_proxy)
            
#             if error:
#                 st.error(f"❌ 트랜스크립트 가져오기 실패: {error}")
                
#                 # Show troubleshooting guide
#                 with st.expander("🔧 문제 해결 가이드"):
#                     st.markdown("""
#                     ### 주요 원인:
#                     1. **IP 차단**: 클라우드 플랫폼(AWS, GCP, Azure)에서 접근
#                     2. **너무 많은 요청**: 같은 IP에서 반복 요청
#                     3. **지역 제한**: 특정 지역에서 차단
                    
#                     ### 해결 방법:
#                     1. ✅ **VPN 사용** (가장 효과적)
#                     2. 🔄 **프록시 활성화** (사이드바에서)
#                     3. ⏰ **잠시 후 재시도**
#                     4. 🏠 **로컬 환경에서 실행**
#                     5. 📺 **다른 비디오로 테스트**
                    
#                     ### YouTube Data API v3 사용:
#                     더 안정적인 대안으로 YouTube Data API v3를 사용할 수 있습니다.
#                     """)
#                 return
                
#             if transcript:
#                 st.success(f"✅ 트랜스크립트 성공적으로 가져옴! ({len(transcript)}자)")
                
#                 # Show original transcript if enabled
#                 if show_transcript:
#                     with st.expander("📜 원본 트랜스크립트 보기"):
#                         st.text_area("Full Transcript", transcript, height=200)
                
#                 # Generate summary
#                 with st.spinner("🤖 요약 생성 중..."):
#                     summary, error = summarize_text(transcript, api_key)
                
#                 if error:
#                     st.error(f"❌ 요약 생성 실패: {error}")
#                     return
                    
#                 if summary:
#                     st.subheader("📋 요약")
#                     st.markdown(summary)
                    
#                     # Download button
#                     st.download_button(
#                         label="📥 요약 다운로드",
#                         data=summary,
#                         file_name=f"youtube_summary_{video_id}.md",
#                         mime="text/markdown"
#                     )
#                 else:
#                     st.error("요약을 생성할 수 없습니다.")
#             else:
#                 st.error("트랜스크립트를 가져올 수 없습니다.")
                
#         except Exception as e:
#             st.error(f"❌ 오류가 발생했습니다: {str(e)}")

# if __name__ == "__main__":
#     main()

import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import re

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

def get_transcript(video_id):
    """자막 가져오기 - 수동 자막 우선, 없으면 자동 생성 자막"""
    try:
        ytt_api = YouTubeTranscriptApi()
        
        # 사용 가능한 자막 목록 가져오기 (로그 최소화)
        transcript_list = ytt_api.list(video_id)
        
        fetched = None
        successful_transcript = None
        errors = []
        transcript_info = []
        
        # 사용 가능한 자막 정보 수집
        for transcript in transcript_list:
            transcript_type = "수동 작성" if transcript.is_generated == 0 else "자동 생성"
            transcript_info.append(f"{transcript.language} ({transcript.language_code}) - {transcript_type}")
        
        # 1단계: 수동 작성된 자막 찾기 (is_generated == 0)
        for transcript in transcript_list:
            if transcript.is_generated == 0:  # 수동 자막
                try:
                    fetched = transcript.fetch()
                    successful_transcript = transcript
                    break
                except Exception as e:
                    errors.append(f"수동 자막 {transcript.language} 실패: {str(e)}")
                    continue
        
        # 2단계: 수동 자막이 없으면 자동 생성 자막 사용 (is_generated == 1)
        if fetched is None:
            for transcript in transcript_list:
                if transcript.is_generated == 1:  # 자동 생성 자막
                    try:
                        fetched = transcript.fetch()
                        successful_transcript = transcript
                        break
                    except Exception as e:
                        errors.append(f"자동 자막 {transcript.language} 실패: {str(e)}")
                        continue
        
        # 자막이 없는 경우
        if fetched is None:
            detailed_error = f"모든 자막 가져오기 실패.\n\n사용 가능한 자막:\n" + "\n".join(transcript_info) + "\n\n세부 오류:\n" + "\n".join(errors)
            return None, detailed_error, None
        
        # 자막 텍스트 합치기 (작은따옴표 제거)
        output = ''
        for f in fetched:
            text = f.text.replace("'", "").replace('"', '')  # 작은따옴표, 큰따옴표 제거
            output += text + ' '
        
        # 성공 정보 반환
        success_info = {
            'language': successful_transcript.language,
            'language_code': successful_transcript.language_code,
            'type': '수동 작성' if successful_transcript.is_generated == 0 else '자동 생성',
            'segments': len(fetched),
            'total_chars': len(output.strip()),
            'available_transcripts': transcript_info
        }
        
        return output.strip(), None, success_info
        
    except Exception as e:
        detailed_error = f"자막 목록 가져오기 실패: {str(e)}\n\n가능한 원인:\n1. 잘못된 비디오 ID\n2. 비공개/삭제된 비디오\n3. IP 차단\n4. 네트워크 오류"
        return None, detailed_error, None

def summarize_text(text, api_key):
    """Gemini를 사용한 텍스트 요약"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # 텍스트 길이 제한
        max_length = 20000
        if len(text) > max_length:
            text = text[:max_length] + "..."
            st.warning(f"⚠️ 텍스트가 너무 길어서 {max_length}자로 제한했습니다.")
        
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
        return response.text, None
        
    except Exception as e:
        return None, str(e)

def main():
    st.set_page_config(
        page_title="YouTube 자막 요약기",
        page_icon="📺"
    )
    
    st.title("📺 YouTube 자막 요약기")
    st.write("YouTube 비디오의 자막을 추출하고 AI로 요약합니다.")
    
    # 사용법 안내
    with st.expander("💡 사용법 및 주의사항"):
        st.markdown("""
        ### 사용법
        1. Gemini API 키 입력
        2. YouTube 비디오 URL 입력
        3. 요약 생성 버튼 클릭
        
        ### 자막 우선순위
        1. **수동 작성 자막** (사람이 직접 작성) - 가장 정확
        2. **자동 생성 자막** (YouTube AI 생성) - 차선책
        
        ### IP 차단 문제
        - 클라우드 환경에서는 IP 차단될 수 있음
        - **해결법**: VPN 사용 또는 로컬에서 실행
        """)
    
    # API 키 입력
    api_key = st.text_input(
        "🔑 Gemini API Key",
        type="password",
        help="Google AI Studio에서 발급받으세요"
    )
    
    # 비디오 URL 입력
    video_input = st.text_input(
        "🎥 YouTube URL 또는 비디오 ID",
        placeholder="https://www.youtube.com/watch?v=VIDEO_ID"
    )
    
    # 옵션
    show_transcript = st.checkbox("📜 원본 자막 표시", value=True)
    
    # 처리 버튼
    if st.button("🚀 자막 추출 및 요약", type="primary"):
        if not api_key:
            st.error("❌ Gemini API Key를 입력해주세요!")
            return
        
        if not video_input:
            st.error("❌ YouTube URL을 입력해주세요!")
            return
        
        # 비디오 ID 추출
        video_id = extract_video_id(video_input)
        st.info(f"🎯 비디오 ID: {video_id}")
        
        # 자막 가져오기
        with st.spinner("📄 자막 가져오는 중..."):
            transcript, error, info = get_transcript(video_id)
        
        if error:
            st.error(f"❌ 자막 가져오기 실패")
            
            # 세부 오류는 expander로 접기
            with st.expander("🔍 세부 오류 정보"):
                st.text(error)
            
            # 해결책 제시
            with st.expander("🔧 해결 방법"):
                st.markdown("""
                ### 주요 원인
                1. **IP 차단**: 클라우드 환경에서 YouTube 접근 제한
                2. **자막 없음**: 해당 비디오에 자막이 없음
                3. **비공개 비디오**: 접근 권한 없음
                
                ### 해결책
                1. **VPN 사용** - 가장 효과적
                2. **로컬에서 실행** - 100% 안정적
                3. **다른 비디오 시도** - 자막이 있는 공개 비디오
                4. **모바일 핫스팟 사용**
                """)
            return
        
        if transcript and info:
            # 성공 메시지를 간결하게 표시
            st.success(f"✅ 자막 추출 성공! ({info['type']}, {info['total_chars']:,}자)")
            
            # 세부 정보는 expander로 접기
            with st.expander("📊 자막 상세 정보"):
                st.write(f"**사용된 자막**: {info['language']} ({info['language_code']}) - {info['type']}")
                st.write(f"**세그먼트 수**: {info['segments']:,}개")
                st.write(f"**총 글자 수**: {info['total_chars']:,}자")
                st.write("**사용 가능한 자막**:")
                for transcript_info in info['available_transcripts']:
                    st.write(f"- {transcript_info}")
            
            # 메인 콘텐츠 영역을 탭으로 구성
            tab1, tab2 = st.tabs(["📜 원본 자막", "🤖 AI 요약"])
            
            with tab1:
                st.markdown("### 📜 원본 자막")
                if show_transcript:
                    st.text_area(
                        "추출된 자막",
                        transcript,
                        height=400,
                        help="자막 내용을 확인하고 복사할 수 있습니다."
                    )
                    
                    # 다운로드 버튼
                    st.download_button(
                        "📥 자막 다운로드",
                        transcript,
                        f"youtube_transcript_{video_id}.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                else:
                    st.info("📜 원본 자막 표시를 체크하면 여기에 표시됩니다.")
            
            with tab2:
                st.markdown("### 🤖 AI 요약")
                
                # 요약 생성
                with st.spinner("🤖 AI 요약 생성 중..."):
                    summary, summary_error = summarize_text(transcript, api_key)
                
                if summary_error:
                    st.error(f"❌ 요약 생성 실패")
                    with st.expander("🔍 오류 세부사항"):
                        st.text(summary_error)
                    return
                
                if summary:
                    # 요약 내용 표시
                    st.markdown(summary)
                    
                    # 요약 다운로드 버튼
                    st.download_button(
                        "📥 요약 다운로드",
                        summary,
                        f"youtube_summary_{video_id}.md",
                        mime="text/markdown",
                        use_container_width=True
                    )

    # 테스트 비디오
    st.markdown("---")
    st.subheader("🧪 테스트용 비디오")
    
    test_videos = [
        ("TED Talk", "UF8uR6Z6KLc", "How to speak so that people want to listen"),
        ("교육 영상", "kjBOesZCoqc", "Khan Academy - Intro to Economics"),
        ("인기 영상", "dNVtMmLlnoE", "Crash Course World History")
    ]
    
    cols = st.columns(3)
    for i, (category, vid_id, title) in enumerate(test_videos):
        with cols[i]:
            st.write(f"**{category}**")
            st.write(title)
            if st.button(f"테스트", key=f"test_{i}"):
                st.info(f"비디오 ID `{vid_id}`를 위에 입력하고 실행해보세요!")

if __name__ == "__main__":
    main()
