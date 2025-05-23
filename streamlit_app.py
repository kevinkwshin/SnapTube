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
from google import genai
from google.genai import types
import re
from urllib.parse import urlparse, parse_qs

# YouTube Data API Key (여기에 본인의 API 키를 입력하세요)
YOUTUBE_API_KEY = "YOUR_YOUTUBE_DATA_API_KEY_HERE"

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
        # Assume it's already a video ID
        return url.strip()

def parse_srt_content(srt_content):
    """Parse SRT content and extract clean text"""
    # Remove SRT formatting (timestamps, sequence numbers)
    text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', srt_content)
    # Remove sequence numbers at the beginning of blocks
    text = re.sub(r'\n\d+\n', '\n', text)
    # Clean up multiple newlines
    text = re.sub(r'\n+', ' ', text)
    # Remove HTML tags if any
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

def get_transcript(video_id):
    """Get transcript using YouTube Data API v3"""
    try:
        # Build YouTube service
        youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        
        # Get caption tracks
        st.info("📋 자막 트랙 목록 가져오는 중...")
        captions_response = youtube.captions().list(
            part="snippet",
            videoId=video_id
        ).execute()
        
        if not captions_response.get("items"):
            return None, "이 비디오에는 사용 가능한 자막이 없습니다."
        
        st.success(f"✅ {len(captions_response['items'])}개의 자막 트랙을 찾았습니다!")
        
        # Find the best caption (prefer manual over auto-generated, English over others)
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
        
        # Download caption
        st.info("📥 자막 다운로드 중...")
        caption_response = youtube.captions().download(
            id=caption_id,
            tfmt="srt"  # SubRip format
        ).execute()
        
        caption_text = caption_response.decode('utf-8')
        
        # Parse SRT content to extract just the text
        clean_text = parse_srt_content(caption_text)
        
        return clean_text, None
        
    except Exception as e:
        return None, f"YouTube Data API 오류: {str(e)}"

def summarize_text(text, api_key):
    """Summarize text using Google Gemini API"""
    try:
        client = genai.Client(api_key=api_key)
        model = "gemini-2.0-flash-exp"
        
        # Limit text length to avoid token limits
        max_length = 15000
        if len(text) > max_length:
            text = text[:max_length] + "..."
            st.info(f"⚠️ 텍스트가 너무 길어서 처음 {max_length}자로 제한했습니다.")
        
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=f'다음 YouTube 비디오 트랜스크립트를 분석하여 포괄적인 요약을 작성해주세요:\n\n{text}\n\n다음 형식으로 구성해주세요:\n## 📌 주요 주제\n[비디오의 메인 주제나 테마]\n\n## 🔑 핵심 포인트\n1. [첫 번째 주요 포인트]\n2. [두 번째 주요 포인트]\n3. [세 번째 주요 포인트]\n4. [네 번째 주요 포인트]\n5. [다섯 번째 주요 포인트]\n\n## 📋 중요한 세부사항\n[구체적인 예시, 데이터, 또는 언급된 중요한 정보들]\n\n## 💡 결론 및 시사점\n[비디오의 주요 메시지나 시청자가 얻을 수 있는 교훈]\n\n명확하고 읽기 쉽게 한국어로 작성해주세요.'
                    ),
                ],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
            system_instruction='당신은 전문적인 콘텐츠 요약 전문가입니다. 명확하고 구조화된 요약을 제공하며, 독자가 쉽게 이해할 수 있도록 작성합니다.',
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
    st.write("**YouTube Data API v3 버전** - IP 차단 문제 해결!")
    
    # API Key 확인
    if YOUTUBE_API_KEY == "YOUR_YOUTUBE_DATA_API_KEY_HERE":
        st.error("⚠️ 개발자: YouTube Data API 키를 설정해주세요!")
        st.code("YOUTUBE_API_KEY = 'your_actual_api_key_here'")
        return
    
    # Gemini API Key input
    st.subheader("🔑 Gemini API 키 입력")
    api_key = st.text_input(
        "Gemini API Key를 입력하세요", 
        type="password",
        help="Google AI Studio에서 발급받으세요: https://makersuite.google.com/app/apikey"
    )
    
    # Video URL/ID input
    st.subheader("🎥 YouTube 비디오")
    video_input = st.text_input(
        "YouTube 비디오 URL 또는 비디오 ID를 입력하세요",
        placeholder="https://www.youtube.com/watch?v=VIDEO_ID"
    )
    
    # Options
    col1, col2 = st.columns(2)
    with col1:
        show_transcript = st.checkbox("원본 자막 표시", value=True)
    with col2:
        st.write("")  # spacing
    
    # Generate Summary button
    if st.button("🚀 요약 생성", type="primary", use_container_width=True):
        if not api_key:
            st.error("❌ Gemini API Key를 입력해주세요!")
            return
            
        if not video_input:
            st.error("❌ YouTube 비디오 URL 또는 비디오 ID를 입력해주세요!")
            return
        
        try:
            # Extract video ID
            video_id = extract_video_id(video_input)
            st.info(f"🎯 처리 중인 비디오 ID: `{video_id}`")
            
            # Get transcript
            with st.spinner("📄 자막 가져오는 중..."):
                transcript, error = get_transcript(video_id)
            
            if error:
                st.error(f"❌ 자막 가져오기 실패: {error}")
                
                # Show troubleshooting guide
                with st.expander("🔧 문제 해결 가이드"):
                    st.markdown("""
                    ### 가능한 원인:
                    1. **자막이 없는 비디오**: 일부 비디오는 자막이 제공되지 않습니다
                    2. **비공개/제한된 비디오**: 접근할 수 없는 비디오입니다
                    3. **API 할당량 초과**: YouTube Data API 일일 한도를 초과했습니다
                    4. **잘못된 비디오 ID**: URL이나 ID를 다시 확인해주세요
                    
                    ### 해결 방법:
                    1. ✅ **다른 비디오로 테스트** (자막이 있는 공개 비디오)
                    2. 📺 **TED Talks나 교육 비디오** 시도 (자막이 잘 제공됨)
                    3. ⏰ **잠시 후 다시 시도** (API 할당량 리셋 대기)
                    4. 🔑 **YouTube Data API 키 확인** (올바른 키이고 활성화되었는지)
                    
                    ### API 키 발급 방법:
                    1. [Google Cloud Console](https://console.cloud.google.com/) 접속
                    2. 프로젝트 생성 또는 선택
                    3. YouTube Data API v3 활성화
                    4. 자격 증명 → API 키 생성
                    """)
                return
                
            if transcript:
                st.success(f"✅ 자막을 성공적으로 가져왔습니다! ({len(transcript):,}자)")
                
                # Show original transcript if enabled
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
                    col3, col4 = st.columns(2)
                    with col3:
                        st.download_button(
                            label="📥 요약 다운로드 (Markdown)",
                            data=summary,
                            file_name=f"youtube_summary_{video_id}.md",
                            mime="text/markdown"
                        )
                    
                    with col4:
                        st.download_button(
                            label="📥 원본 자막 다운로드",
                            data=transcript,
                            file_name=f"youtube_transcript_{video_id}.txt",
                            mime="text/plain"
                        )
                else:
                    st.error("요약을 생성할 수 없습니다.")
                
        except Exception as e:
            st.error(f"❌ 예상치 못한 오류가 발생했습니다: {str(e)}")
            st.info("문제가 지속되면 다른 비디오로 시도해보세요.")

    # Instructions
    with st.expander("📋 사용 방법 및 API 키 발급 가이드"):
        st.markdown("""
        ### 🔑 Gemini API 키 발급
        1. [Google AI Studio](https://makersuite.google.com/app/apikey)에서 무료로 발급
        2. Google 계정으로 로그인
        3. "Create API Key" 클릭
        4. 생성된 키를 복사해서 위에 입력
        
        ### 🎯 사용법
        1. Gemini API 키 입력
        2. YouTube 비디오 URL 입력 (전체 URL 또는 비디오 ID만)
        3. 요약 생성 버튼 클릭
        4. 결과 확인 및 다운로드
        
        ### 📺 추천 테스트 비디오
        - TED Talks (자막이 항상 제공됨)
        - 교육 채널 영상들 (Khan Academy, Crash Course 등)
        - 인기 있는 공개 비디오들
        
        ### ⚠️ 주의사항
        - YouTube Data API 일일 할당량: 10,000 쿼터
        - 일부 비디오는 자막이 없을 수 있습니다
        - 비공개 또는 제한된 비디오는 접근 불가
        """)

    # Footer
    st.markdown("---")
    st.markdown("""
    **💡 이 버전의 장점:**
    - ✅ IP 차단 문제 완전 해결
    - ✅ 공식 YouTube Data API v3 사용
    - ✅ 안정적이고 신뢰할 수 있음
    - ✅ 자막 품질 선택 (수동 > 자동생성)
    - ✅ 다양한 언어 지원
    """)

if __name__ == "__main__":
    main()
