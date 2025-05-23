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
import googleapiclient.discovery
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.genai import types
from google import genai
import re
import json
import tempfile
import os
from urllib.parse import urlparse, parse_qs

# Streamlit Secrets에서 OAuth2 설정 가져오기
def get_client_secrets():
    """Streamlit secrets에서 OAuth2 클라이언트 정보 가져오기"""
    try:
        return {
            "web": {
                "client_id": st.secrets["google_oauth"]["client_id"],
                "client_secret": st.secrets["google_oauth"]["client_secret"],
                "redirect_uris": ["http://localhost:8501"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }
    except KeyError:
        return None

SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

def extract_video_id(url):
    """Extract video ID from various YouTube URL formats"""
    if "youtube.com/watch" in url:
        parsed_url = urlparse(url)
        return parse_qs(parsed_url.query)['v'][0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    elif "youtube.com/embed/" in url:
        return url.split("embed/")[1].split("?")[0]
    else:
        return url.strip()

def get_oauth2_url():
    """Generate OAuth2 authorization URL"""
    client_secrets = get_client_secrets()
    if not client_secrets:
        raise Exception("OAuth2 클라이언트 정보가 설정되지 않았습니다")
    
    # Create temporary file for client secrets
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(client_secrets, f)
        temp_file = f.name
    
    try:
        flow = Flow.from_client_secrets_file(
            temp_file,
            scopes=SCOPES,
            redirect_uri='http://localhost:8501'
        )
        
        auth_url, _ = flow.authorization_url(prompt='consent')
        return auth_url, flow
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file):
            os.remove(temp_file)

def exchange_code_for_token(auth_code):
    """Exchange authorization code for access token"""
    client_secrets = get_client_secrets()
    if not client_secrets:
        raise Exception("OAuth2 클라이언트 정보가 설정되지 않았습니다")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(client_secrets, f)
        temp_file = f.name
    
    try:
        flow = Flow.from_client_secrets_file(
            temp_file,
            scopes=SCOPES,
            redirect_uri='http://localhost:8501'
        )
        
        flow.fetch_token(code=auth_code)
        return flow.credentials
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

def parse_srt_content(srt_content):
    """Parse SRT content and extract clean text"""
    text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', srt_content)
    text = re.sub(r'\n\d+\n', '\n', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

def get_transcript_with_oauth(video_id, credentials):
    """Get transcript using OAuth2 authenticated YouTube API"""
    try:
        # Build YouTube service with OAuth2 credentials
        youtube = googleapiclient.discovery.build(
            "youtube", "v3", 
            credentials=credentials
        )
        
        # Get caption tracks
        st.info("📋 자막 트랙 목록 가져오는 중...")
        captions_response = youtube.captions().list(
            part="snippet",
            videoId=video_id
        ).execute()
        
        if not captions_response.get("items"):
            return None, "이 비디오에는 사용 가능한 자막이 없습니다."
        
        st.success(f"✅ {len(captions_response['items'])}개의 자막 트랙을 찾았습니다!")
        
        # Find the best caption
        caption_id = None
        caption_language = None
        caption_type = None
        
        # Priority: Manual English > Auto English > Manual other > Auto other
        for priority in ['manual_en', 'auto_en', 'manual_other', 'auto_other']:
            for caption in captions_response["items"]:
                snippet = caption["snippet"]
                is_auto = snippet.get("trackKind") == "ASR"
                language = snippet["language"]
                
                if priority == 'manual_en' and not is_auto and language.startswith('en'):
                    caption_id = caption["id"]
                    caption_language = language
                    caption_type = "수동 작성"
                    break
                elif priority == 'auto_en' and is_auto and language.startswith('en'):
                    caption_id = caption["id"]
                    caption_language = language
                    caption_type = "자동 생성"
                    break
                elif priority == 'manual_other' and not is_auto:
                    caption_id = caption["id"]
                    caption_language = language
                    caption_type = "수동 작성"
                    break
                elif priority == 'auto_other' and is_auto:
                    caption_id = caption["id"]
                    caption_language = language
                    caption_type = "자동 생성"
                    break
            
            if caption_id:
                break
        
        if not caption_id:
            return None, "적합한 자막을 찾을 수 없습니다."
        
        st.info(f"🎯 사용할 자막: {caption_language} ({caption_type})")
        
        # Download caption with OAuth2
        st.info("📥 자막 다운로드 중...")
        caption_response = youtube.captions().download(
            id=caption_id,
            tfmt="srt"
        ).execute()
        
        caption_text = caption_response.decode('utf-8')
        clean_text = parse_srt_content(caption_text)
        
        return clean_text, None
        
    except Exception as e:
        return None, f"YouTube Data API 오류: {str(e)}"

def summarize_text(text, api_key):
    """Summarize text using Google Gemini API"""
    try:
        client = genai.Client(api_key=api_key)
        model = "gemini-2.0-flash-exp"
        
        max_length = 15000
        if len(text) > max_length:
            text = text[:max_length] + "..."
            st.info(f"⚠️ 텍스트가 너무 길어서 처음 {max_length}자로 제한했습니다.")
        
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=f'다음 YouTube 비디오 트랜스크립트를 분석하여 포괄적인 요약을 작성해주세요:\n\n{text}\n\nMarkdown 형식으로 구조화해서 작성해주세요.'
                    ),
                ],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
            system_instruction='당신은 전문적인 콘텐츠 요약 전문가입니다.',
            temperature=0.1
        )
        
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        
        return response.text, None
        
    except Exception as e:
        return None, str(e)

def main():
    st.set_page_config(
        page_title="SnapTube: YouTube Transcript Summarizer",
        page_icon="📺",
        layout="wide"
    )
    
    st.title("📺 SnapTube: YouTube Transcript Summarizer")
    st.write("**Streamlit Secrets 버전** - 안전한 OAuth2 인증!")
    
    # Check if secrets are configured
    client_secrets = get_client_secrets()
    if not client_secrets:
        st.error("⚠️ OAuth2 클라이언트 정보가 설정되지 않았습니다!")
        
        with st.expander("🔧 Streamlit Secrets 설정 방법", expanded=True):
            st.markdown("""
            ### 로컬 개발 환경
            1. `.streamlit/secrets.toml` 파일 생성:
            ```toml
            [google_oauth]
            client_id = "your-client-id.apps.googleusercontent.com"
            client_secret = "your-client-secret"
            ```
            
            ### Streamlit Community Cloud
            1. GitHub 리포지토리에 앱 배포
            2. Streamlit Community Cloud에서 앱 설정 → **Secrets** 탭
            3. 다음 내용 입력:
            ```toml
            [google_oauth]
            client_id = "your-client-id.apps.googleusercontent.com"
            client_secret = "your-client-secret"
            ```
            
            ### OAuth2 클라이언트 ID 생성
            1. [Google Cloud Console](https://console.cloud.google.com/) 접속
            2. 프로젝트 생성 → YouTube Data API v3 활성화
            3. 사용자 인증 정보 → OAuth 2.0 클라이언트 ID 생성
            4. 웹 애플리케이션 → 리디렉션 URI: `http://localhost:8501`
            
            ### 🔒 보안 장점
            - GitHub에 민감한 정보가 노출되지 않음
            - Streamlit이 안전하게 관리
            - 배포 환경에서도 동일하게 작동
            """)
        return
    
    # Check if user is authenticated
    if 'credentials' not in st.session_state:
        st.session_state.credentials = None
    
    # Authentication section
    st.subheader("🔐 YouTube 인증")
    
    if st.session_state.credentials is None:
        st.info("YouTube 자막에 접근하려면 Google 계정으로 로그인해야 합니다.")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if st.button("🔑 Google 로그인", type="primary"):
                try:
                    auth_url, flow = get_oauth2_url()
                    st.session_state.flow = flow
                    st.markdown(f"👆 [여기를 클릭해서 Google 로그인하세요]({auth_url})")
                    st.info("로그인 후 나타나는 인증 코드를 아래에 입력하세요.")
                except Exception as e:
                    st.error(f"인증 URL 생성 실패: {str(e)}")
        
        with col2:
            auth_code = st.text_input(
                "인증 코드 입력",
                help="Google 로그인 후 받은 코드를 여기에 붙여넣으세요"
            )
            
            if auth_code and st.button("인증 완료"):
                try:
                    credentials = exchange_code_for_token(auth_code)
                    st.session_state.credentials = credentials
                    st.success("✅ 인증 성공!")
                    st.rerun()
                except Exception as e:
                    st.error(f"인증 실패: {str(e)}")
    
    else:
        st.success("✅ YouTube 인증 완료!")
        if st.button("🚪 로그아웃"):
            st.session_state.credentials = None
            st.rerun()
    
    # Only show main app if authenticated
    if st.session_state.credentials:
        # Gemini API Key input
        st.subheader("🤖 Gemini API 키")
        api_key = st.text_input(
            "Gemini API Key를 입력하세요", 
            type="password",
            help="Google AI Studio에서 발급: https://makersuite.google.com/app/apikey"
        )
        
        # Video input
        st.subheader("🎥 YouTube 비디오")
        video_input = st.text_input(
            "YouTube 비디오 URL 또는 비디오 ID를 입력하세요",
            placeholder="https://www.youtube.com/watch?v=VIDEO_ID"
        )
        
        show_transcript = st.checkbox("원본 자막 표시", value=True)
        
        # Generate Summary button
        if st.button("🚀 요약 생성", type="primary", use_container_width=True):
            if not api_key:
                st.error("❌ Gemini API Key를 입력해주세요!")
                return
                
            if not video_input:
                st.error("❌ YouTube 비디오 URL을 입력해주세요!")
                return
            
            try:
                video_id = extract_video_id(video_input)
                st.info(f"🎯 처리 중인 비디오 ID: `{video_id}`")
                
                # Get transcript with OAuth2
                with st.spinner("📄 자막 가져오는 중..."):
                    transcript, error = get_transcript_with_oauth(video_id, st.session_state.credentials)
                
                if error:
                    st.error(f"❌ 자막 가져오기 실패: {error}")
                    return
                    
                if transcript:
                    st.success(f"✅ 자막을 성공적으로 가져왔습니다! ({len(transcript):,}자)")
                    
                    if show_transcript:
                        st.subheader("📜 원본 자막")
                        st.text_area("전체 자막", transcript, height=200)
                    
                    # Generate summary
                    with st.spinner("🤖 AI 요약 생성 중..."):
                        summary, error = summarize_text(transcript, api_key)
                    
                    if error:
                        st.error(f"❌ 요약 생성 실패: {error}")
                        return
                        
                    if summary:
                        st.subheader("📋 비디오 요약")
                        st.markdown(summary)
                        
                        # Download options
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="📥 요약 다운로드",
                                data=summary,
                                file_name=f"summary_{video_id}.md",
                                mime="text/markdown"
                            )
                        
                        with col2:
                            st.download_button(
                                label="📥 자막 다운로드",
                                data=transcript,
                                file_name=f"transcript_{video_id}.txt",
                                mime="text/plain"
                            )
                
            except Exception as e:
                st.error(f"❌ 오류: {str(e)}")

    # Footer
    st.markdown("---")
    st.markdown("""
    **🔒 보안 정보:**
    - OAuth2 클라이언트 정보는 Streamlit Secrets로 안전하게 관리
    - GitHub에 민감한 정보가 노출되지 않음
    - 프로덕션 환경에서 권장되는 방법
    """)

if __name__ == "__main__":
    main()
