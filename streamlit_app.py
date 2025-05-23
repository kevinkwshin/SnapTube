import streamlit as st
import googleapiclient.discovery
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
import google.generativeai as genai
import re
import json
import tempfile
import os
from urllib.parse import urlparse, parse_qs

def extract_video_id(url):
    """YouTube URL에서 비디오 ID 추출"""
    if "youtube.com/watch" in url:
        parsed_url = urlparse(url)
        return parse_qs(parsed_url.query)['v'][0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    elif "youtube.com/embed/" in url:
        return url.split("embed/")[1].split("?")[0]
    else:
        return url.strip()

def get_oauth2_config():
    """Streamlit Secrets에서 OAuth2 설정 가져오기"""
    try:
        return {
            "web": {
                "client_id": st.secrets["GOOGLE_CLIENT_ID"],
                "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8501"]
            }
        }
    except KeyError:
        return None

def create_oauth_flow():
    """OAuth 2.0 Flow 생성"""
    oauth_config = get_oauth2_config()
    if not oauth_config:
        return None
    
    # 임시 파일에 클라이언트 시크릿 저장
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(oauth_config, f)
        temp_file = f.name
    
    try:
        flow = Flow.from_client_secrets_file(
            temp_file,
            scopes=['https://www.googleapis.com/auth/youtube.force-ssl'],
            redirect_uri='http://localhost:8501'
        )
        return flow, temp_file
    except Exception as e:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise e

def parse_srt_content(srt_content):
    """SRT 내용에서 텍스트만 추출"""
    text = re.sub(r'\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n', '', srt_content)
    text = re.sub(r'\n\d+\n', '\n', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

def get_transcript_with_oauth(video_id, credentials):
    """OAuth 2.0 인증으로 자막 가져오기"""
    try:
        # OAuth 2.0 인증된 YouTube API 클라이언트 생성
        youtube = googleapiclient.discovery.build(
            "youtube", "v3", 
            credentials=credentials
        )
        
        st.info("📋 자막 목록 확인 중...")
        
        # 자막 목록 가져오기
        captions_response = youtube.captions().list(
            part="snippet",
            videoId=video_id
        ).execute()
        
        if not captions_response.get("items"):
            return None, "이 비디오에는 사용 가능한 자막이 없습니다."
        
        st.success(f"✅ {len(captions_response['items'])}개의 자막을 찾았습니다!")
        
        # 최적의 자막 선택
        caption_id = None
        selected_caption = None
        
        # 우선순위: 수동 영어 > 자동 영어 > 수동 기타 > 자동 기타
        priorities = [
            ('manual', 'en'),
            ('auto', 'en'),
            ('manual', 'other'),
            ('auto', 'other')
        ]
        
        for priority_type, lang_pref in priorities:
            for caption in captions_response["items"]:
                snippet = caption["snippet"]
                is_auto = snippet.get("trackKind") == "ASR"
                language = snippet["language"]
                
                if priority_type == 'manual' and not is_auto:
                    if lang_pref == 'en' and language.startswith('en'):
                        caption_id = caption["id"]
                        selected_caption = snippet
                        break
                    elif lang_pref == 'other':
                        caption_id = caption["id"]
                        selected_caption = snippet
                        break
                elif priority_type == 'auto' and is_auto:
                    if lang_pref == 'en' and language.startswith('en'):
                        caption_id = caption["id"]
                        selected_caption = snippet
                        break
                    elif lang_pref == 'other':
                        caption_id = caption["id"]
                        selected_caption = snippet
                        break
            
            if caption_id:
                break
        
        if not caption_id:
            return None, "적합한 자막을 찾을 수 없습니다."
        
        # 선택된 자막 정보 표시
        caption_type = "자동 생성" if selected_caption.get("trackKind") == "ASR" else "수동 작성"
        st.info(f"🎯 사용할 자막: {selected_caption['language']} ({caption_type})")
        
        # OAuth 2.0으로 자막 다운로드
        st.info("📥 자막 다운로드 중...")
        caption_response = youtube.captions().download(
            id=caption_id,
            tfmt="srt"
        ).execute()
        
        # SRT 내용을 텍스트로 변환
        srt_content = caption_response.decode('utf-8')
        clean_text = parse_srt_content(srt_content)
        
        return clean_text, selected_caption['language'], len(clean_text)
        
    except Exception as e:
        return None, f"YouTube API 오류: {str(e)}"

def summarize_text(text, api_key):
    """Gemini 2.5 Flash로 요약 생성"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
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
        return response.text
        
    except Exception as e:
        return f"요약 생성 실패: {str(e)}"

def main():
    st.set_page_config(
        page_title="YouTube 자막 요약기 (OAuth 2.0)",
        page_icon="📺",
        layout="wide"
    )
    
    st.title("📺 YouTube 자막 요약기")
    st.write("**OAuth 2.0 인증 버전** - YouTube 자막 다운로드 완벽 지원!")
    
    # OAuth 2.0 설정 확인
    oauth_config = get_oauth2_config()
    if not oauth_config:
        st.error("❌ OAuth 2.0 설정이 되지 않았습니다")
        
        with st.expander("🔧 개발자용 - OAuth 2.0 설정 방법", expanded=True):
            st.markdown("""
            ### 1단계: Google Cloud Console 설정
            1. [Google Cloud Console](https://console.cloud.google.com/) 접속
            2. 프로젝트 생성 또는 선택
            3. **YouTube Data API v3** 활성화
            4. **OAuth 2.0 클라이언트 ID** 생성:
               - 사용자 인증 정보 → OAuth 2.0 클라이언트 ID
               - 애플리케이션 유형: **웹 애플리케이션**
               - 이름: 원하는 이름 입력
               - 승인된 리디렉션 URI: `http://localhost:8501`
            5. 클라이언트 ID와 클라이언트 보안 비밀번호 복사
            
            ### 2단계: Streamlit Secrets 설정
            
            **Streamlit Community Cloud:**
            앱 설정 → Secrets 탭에서 입력:
            ```toml
            GOOGLE_CLIENT_ID = "your-client-id.apps.googleusercontent.com"
            GOOGLE_CLIENT_SECRET = "your-client-secret"
            ```
            
            **로컬 개발:**
            `.streamlit/secrets.toml` 파일 생성:
            ```toml
            GOOGLE_CLIENT_ID = "your-client-id.apps.googleusercontent.com"
            GOOGLE_CLIENT_SECRET = "your-client-secret"
            ```
            
            ### 3단계: .gitignore 설정
            ```
            .streamlit/secrets.toml
            ```
            
            ### 왜 OAuth 2.0가 필요한가요?
            - YouTube 자막 **다운로드**는 OAuth 2.0 인증 필요
            - API 키만으로는 자막 **목록만** 조회 가능
            - 사용자 인증을 통한 보안 강화
            """)
        return
    
    # 세션 상태 초기화
    if 'credentials' not in st.session_state:
        st.session_state.credentials = None
    if 'temp_file' not in st.session_state:
        st.session_state.temp_file = None
    
    # OAuth 2.0 인증 섹션
    st.subheader("🔐 Google 계정 인증")
    
    if st.session_state.credentials is None:
        st.info("YouTube 자막에 접근하려면 Google 계정으로 로그인해야 합니다.")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if st.button("🔑 Google 로그인 시작", type="primary"):
                try:
                    flow, temp_file = create_oauth_flow()
                    st.session_state.temp_file = temp_file
                    
                    auth_url, _ = flow.authorization_url(prompt='consent')
                    st.session_state.flow = flow
                    
                    st.markdown(f"### 👆 [Google 로그인하러 가기]({auth_url})")
                    st.info("위 링크를 클릭하여 Google 로그인을 완료한 후, 나타나는 인증 코드를 아래에 입력하세요.")
                    
                except Exception as e:
                    st.error(f"인증 URL 생성 실패: {str(e)}")
        
        with col2:
            auth_code = st.text_input(
                "인증 코드 입력",
                help="Google 로그인 후 받은 인증 코드를 여기에 붙여넣으세요",
                placeholder="4/0Adeu5BW..."
            )
            
            if auth_code and st.button("✅ 인증 완료"):
                try:
                    if 'flow' not in st.session_state:
                        st.error("먼저 'Google 로그인 시작' 버튼을 클릭하세요.")
                        return
                    
                    flow = st.session_state.flow
                    flow.fetch_token(code=auth_code)
                    
                    st.session_state.credentials = flow.credentials
                    
                    # 임시 파일 정리
                    if st.session_state.temp_file and os.path.exists(st.session_state.temp_file):
                        os.remove(st.session_state.temp_file)
                    
                    st.success("✅ Google 인증 성공!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"인증 실패: {str(e)}")
    
    else:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.success("✅ Google 계정 인증 완료!")
        with col2:
            if st.button("🚪 로그아웃"):
                st.session_state.credentials = None
                if 'flow' in st.session_state:
                    del st.session_state.flow
                st.rerun()
    
    # 인증이 완료된 경우에만 메인 앱 표시
    if st.session_state.credentials:
        st.markdown("---")
        
        # Gemini API 키 입력
        col1, col2 = st.columns([3, 1])
        
        with col1:
            gemini_api_key = st.text_input(
                "🔑 Gemini API Key",
                type="password",
                help="Google AI Studio에서 무료로 발급받으세요"
            )
        
        with col2:
            st.write("")  # 정렬용
            if st.button("🔗 API 키 발급"):
                st.markdown("[Google AI Studio →](https://makersuite.google.com/app/apikey)")
        
        # 비디오 URL 입력
        video_input = st.text_input(
            "🎥 YouTube URL 또는 비디오 ID",
            placeholder="https://www.youtube.com/watch?v=VIDEO_ID",
            help="YouTube URL 전체 또는 11자리 비디오 ID를 입력하세요"
        )
        
        # 처리 버튼
        if st.button("🚀 자막 추출 및 AI 요약", type="primary", use_container_width=True):
            if not gemini_api_key:
                st.error("❌ Gemini API Key를 입력해주세요!")
                return
            
            if not video_input:
                st.error("❌ YouTube URL을 입력해주세요!")
                return
            
            # 비디오 ID 추출
            video_id = extract_video_id(video_input)
            st.info(f"🎯 비디오 ID: {video_id}")
            
            # OAuth 2.0으로 자막 가져오기
            with st.spinner("📄 OAuth 2.0 인증으로 자막 가져오는 중..."):
                result = get_transcript_with_oauth(video_id, st.session_state.credentials)
                
                if result[0] is None:  # 실패
                    st.error(f"❌ 자막 가져오기 실패: {result[1]}")
                    return
                
                # 성공
                transcript, language, length = result
                st.success(f"✅ 자막 추출 성공! ({language} 언어, {length:,}자)")
            
            # 결과를 탭으로 표시
            tab1, tab2 = st.tabs(["🤖 **AI 요약**", "📜 **원본 자막**"])
            
            with tab1:
                with st.spinner("🤖 Gemini 2.5 Flash로 요약 생성 중..."):
                    summary = summarize_text(transcript, gemini_api_key)
                
                st.markdown("### 🤖 AI 요약")
                st.markdown(summary)
                
                # 요약 다운로드
                st.download_button(
                    "📥 요약 다운로드",
                    summary,
                    f"youtube_summary_{video_id}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with tab2:
                st.markdown("### 📜 원본 자막")
                st.text_area(
                    "추출된 자막",
                    transcript,
                    height=400,
                    help="자막 내용을 확인하고 복사할 수 있습니다"
                )
                
                # 자막 다운로드
                st.download_button(
                    "📥 자막 다운로드",
                    transcript,
                    f"youtube_transcript_{video_id}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
    
    # 사용법 안내
    with st.expander("💡 OAuth 2.0 버전의 장점"):
        st.markdown("""
        ### ✅ 완벽한 해결책
        - **IP 차단 없음**: 공식 OAuth 2.0 인증
        - **100% 자막 접근**: 모든 YouTube 자막 다운로드 가능
        - **높은 보안**: Google 표준 인증 프로토콜
        - **안정적 성능**: API 키 제한 없이 사용
        
        ### 📦 필요한 라이브러리
        ```txt
        google-api-python-client
        google-auth-oauthlib
        google-generativeai
        streamlit
        ```
        
        ### 🔐 보안 장점
        - 클라이언트 시크릿은 Streamlit Secrets로 안전 보관
        - 사용자별 개별 인증으로 보안 강화
        - GitHub에 민감한 정보 노출 없음
        """)

if __name__ == "__main__":
    main()
