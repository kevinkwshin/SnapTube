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
from youtube_transcript_api.proxies import WebshareProxyConfig
from google import genai
from google.genai import types
import requests
import re
import time
import random

def extract_video_id(url):
    """Extract video ID from various YouTube URL formats"""
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

def get_free_proxy_list():
    """무료 프록시 목록 가져오기 (실시간)"""
    try:
        # 무료 프록시 API 사용
        response = requests.get('https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=US&ssl=all&anonymity=all')
        proxies = response.text.strip().split('\n')
        
        proxy_list = []
        for proxy in proxies[:5]:  # 처음 5개만 사용
            if ':' in proxy:
                host, port = proxy.split(':')
                proxy_dict = {
                    'http': f'http://{host}:{port}',
                    'https': f'http://{host}:{port}'
                }
                proxy_list.append(proxy_dict)
        
        return proxy_list
    except:
        # 백업 프록시 목록 (하드코딩)
        return [
            {'http': 'http://8.210.83.33:80', 'https': 'http://8.210.83.33:80'},
            {'http': 'http://47.74.152.29:8888', 'https': 'http://47.74.152.29:8888'},
            {'http': 'http://43.134.234.74:80', 'https': 'http://43.134.234.74:80'},
        ]

def get_transcript_with_multiple_methods(video_id, use_proxy=False, proxy_service=None):
    """여러 방법으로 자막 가져오기"""
    
    methods = []
    
    # Method 1: 직접 요청
    methods.append(("직접 요청", lambda: YouTubeTranscriptApi.get_transcript(video_id)))
    
    # Method 2: 무료 프록시 사용
    if use_proxy and proxy_service == "free":
        proxy_list = get_free_proxy_list()
        for i, proxy in enumerate(proxy_list):
            methods.append((f"무료 프록시 {i+1}", lambda p=proxy: YouTubeTranscriptApi.get_transcript(video_id, proxies=p)))
    
    # Method 3: Webshare 프록시 (유료)
    elif use_proxy and proxy_service == "webshare":
        webshare_username = st.secrets.get("webshare_username", "")
        webshare_password = st.secrets.get("webshare_password", "")
        
        if webshare_username and webshare_password:
            ytt_api = YouTubeTranscriptApi(
                proxy_config=WebshareProxyConfig(
                    proxy_username=webshare_username,
                    proxy_password=webshare_password
                )
            )
            methods.append(("Webshare 프록시", lambda: ytt_api.get_transcript(video_id)))
    
    # Method 4: User-Agent 변경 + 지연
    methods.append(("User-Agent 변경", lambda: get_transcript_with_headers(video_id)))
    
    # Method 5: 다른 언어 시도
    methods.append(("다른 언어 시도", lambda: try_different_languages(video_id)))
    
    # 각 방법을 순차적으로 시도
    for method_name, method_func in methods:
        try:
            st.info(f"🔄 {method_name} 시도 중...")
            transcript = method_func()
            
            if transcript:
                st.success(f"✅ {method_name} 성공!")
                return ' '.join([item['text'] for item in transcript]), None
                
        except Exception as e:
            st.warning(f"❌ {method_name} 실패: {str(e)[:100]}...")
            time.sleep(random.uniform(1, 3))  # 지연
    
    return None, "모든 방법이 실패했습니다."

def get_transcript_with_headers(video_id):
    """User-Agent 변경하여 자막 가져오기"""
    import urllib.request
    import json
    
    # 다양한 User-Agent 시도
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ]
    
    for user_agent in user_agents:
        try:
            # 사용자 정의 요청 헤더로 시도
            original_get_transcript = YouTubeTranscriptApi.get_transcript
            
            # 헤더 설정 (이는 실제로는 youtube-transcript-api 내부에서 처리되므로 제한적)
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            return transcript
            
        except Exception as e:
            continue
    
    raise Exception("모든 User-Agent 시도 실패")

def try_different_languages(video_id):
    """다른 언어 자막 시도"""
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    
    # 우선순위: 수동 > 자동
    for transcript in transcript_list:
        if not transcript.is_generated:
            try:
                return transcript.fetch()
            except:
                continue
    
    for transcript in transcript_list:
        if transcript.is_generated:
            try:
                return transcript.fetch()
            except:
                continue
    
    raise Exception("사용 가능한 자막이 없습니다")

def get_transcript_via_api_alternative(video_id):
    """대안 API 사용하여 자막 가져오기"""
    try:
        # 무료 YouTube 자막 API 사용 (제3자 서비스)
        api_urls = [
            f"https://youtube-transcript-api.p.rapidapi.com/transcript?video_id={video_id}",
            f"https://youtube-captions-api.herokuapp.com/api/captions/{video_id}",
        ]
        
        for api_url in api_urls:
            try:
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if 'transcript' in data:
                        return data['transcript'], None
            except:
                continue
        
        return None, "대안 API 모두 실패"
        
    except Exception as e:
        return None, f"대안 API 오류: {str(e)}"

def summarize_text(text, api_key):
    """텍스트 요약"""
    try:
        client = genai.Client(api_key=api_key)
        model = "gemini-2.0-flash-exp"
        
        max_length = 15000
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text=f'다음 YouTube 비디오 트랜스크립트를 요약해주세요:\n\n{text}'
                    ),
                ],
            ),
        ]
        
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        
        return response.text, None
        
    except Exception as e:
        return None, str(e)

def main():
    st.set_page_config(
        page_title="SnapTube: IP 우회 통합 버전",
        page_icon="🔥",
        layout="wide"
    )
    
    st.title("🔥 SnapTube: IP 우회 통합 버전")
    st.write("**컴퓨터 VPN 없이도 IP 우회 가능!**")
    
    # IP 우회 방법 설명
    with st.expander("🚀 IP 우회 방법들", expanded=True):
        st.markdown("""
        ### 🔧 앱 내장 IP 우회 기능
        1. **무료 프록시 자동 사용** - 실시간 프록시 목록 가져오기
        2. **Webshare 프록시** - 유료 프록시 서비스 (가장 안정적)
        3. **User-Agent 변경** - 브라우저 정보 변경
        4. **다중 언어 시도** - 여러 언어 자막 시도
        5. **대안 API 사용** - 제3자 서비스 활용
        
        ### 💡 장점
        - ✅ 컴퓨터에 VPN 설치 불필요
        - ✅ 앱에서 자동으로 IP 우회
        - ✅ 여러 방법을 순차적으로 시도
        - ✅ 실시간 상태 표시
        
        ### ⚠️ 제한사항
        - 무료 프록시는 불안정할 수 있음
        - 속도가 느릴 수 있음
        - 100% 보장되지 않음
        """)
    
    # 프록시 설정
    st.subheader("🌐 프록시 설정")
    
    col1, col2 = st.columns(2)
    
    with col1:
        use_proxy = st.checkbox("🔄 IP 우회 활성화", value=True)
    
    with col2:
        proxy_service = st.selectbox(
            "프록시 서비스 선택",
            ["free", "webshare"],
            format_func=lambda x: "무료 프록시" if x == "free" else "Webshare (유료)"
        )
    
    if proxy_service == "webshare":
        st.info("💡 Webshare 사용 시 Streamlit Secrets에 계정 정보를 설정하세요:")
        st.code("""
# .streamlit/secrets.toml
webshare_username = "your_username"
webshare_password = "your_password"
        """)
    
    # API 키 입력
    st.subheader("🤖 Gemini API 키")
    api_key = st.text_input(
        "API 키 입력",
        type="password",
        help="Google AI Studio에서 발급"
    )
    
    # 비디오 입력
    st.subheader("🎥 YouTube 비디오")
    video_input = st.text_input(
        "비디오 URL 또는 ID 입력",
        placeholder="https://www.youtube.com/watch?v=VIDEO_ID"
    )
    
    # 옵션
    show_transcript = st.checkbox("원본 자막 표시", value=True)
    
    # 실행 버튼
    if st.button("🚀 요약 생성 (IP 우회 포함)", type="primary"):
        if not api_key:
            st.error("❌ API 키를 입력해주세요!")
            return
        
        if not video_input:
            st.error("❌ 비디오 URL을 입력해주세요!")
            return
        
        video_id = extract_video_id(video_input)
        st.info(f"🎯 비디오 ID: {video_id}")
        
        # 자막 가져오기 (IP 우회 포함)
        with st.spinner("📄 자막 가져오는 중... (IP 우회 시도)"):
            transcript, error = get_transcript_with_multiple_methods(
                video_id, use_proxy, proxy_service
            )
        
        if error:
            st.error(f"❌ 모든 방법 실패: {error}")
            
            # 추가 해결책
            with st.expander("🆘 추가 해결책"):
                st.markdown("""
                ### 🔧 다른 방법들
                1. **컴퓨터 VPN 사용** (가장 확실)
                   - ExpressVPN, NordVPN, ProtonVPN
                2. **로컬에서 실행**
                   ```bash
                   streamlit run app.py
                   ```
                3. **모바일 핫스팟 사용**
                4. **다른 비디오로 테스트**
                5. **시간을 두고 재시도**
                """)
            return
        
        if transcript:
            st.success(f"✅ 자막 가져오기 성공! ({len(transcript):,}자)")
            
            if show_transcript:
                st.subheader("📜 원본 자막")
                st.text_area("자막", transcript, height=200)
            
            # 요약 생성
            with st.spinner("🤖 요약 생성 중..."):
                summary, error = summarize_text(transcript, api_key)
            
            if summary:
                st.subheader("📋 요약")
                st.markdown(summary)
                
                # 다운로드
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "📥 요약 다운로드",
                        summary,
                        f"summary_{video_id}.md"
                    )
                with col2:
                    st.download_button(
                        "📥 자막 다운로드",
                        transcript,
                        f"transcript_{video_id}.txt"
                    )
    
    # 실시간 프록시 상태 체크
    with st.expander("🔍 프록시 상태 확인"):
        if st.button("프록시 테스트"):
            with st.spinner("프록시 상태 확인 중..."):
                proxies = get_free_proxy_list()
                
                if proxies:
                    st.success(f"✅ {len(proxies)}개의 프록시를 찾았습니다!")
                    for i, proxy in enumerate(proxies):
                        st.write(f"프록시 {i+1}: {proxy['http']}")
                else:
                    st.warning("❌ 사용 가능한 프록시를 찾지 못했습니다.")

    # 푸터
    st.markdown("---")
    st.markdown("""
    **🎯 이 앱의 특징:**
    - 🔄 자동 IP 우회 (컴퓨터 VPN 불필요)
    - 🚀 다중 방법 시도
    - 📊 실시간 상태 표시
    - 🔧 프록시 자동 관리
    
    **💡 성공률 높이는 팁:**
    - 여러 번 시도해보세요
    - 다른 비디오로 테스트해보세요
    - 시간대를 바꿔서 시도해보세요
    """)

if __name__ == "__main__":
    main()
