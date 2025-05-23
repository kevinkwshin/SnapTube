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
        
        # 텍스트 길이 제한 제거 (필요시 Gemini가 자동 처리)
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
        help="Google AI Studio에서 발급받으세요: https://makersuite.google.com/app/apikey"
    )
    
    # 링크 버튼 추가
    if st.button("🔗 AI Studio에서 API 키 발급받기"):
        st.markdown("[Google AI Studio로 이동하기](https://makersuite.google.com/app/apikey)")
    
    # 비디오 URL 입력
    video_input = st.text_input(
        "🎥 YouTube URL 또는 비디오 ID",
        placeholder="https://www.youtube.com/watch?v=VIDEO_ID",
        help="전체 YouTube URL 또는 11자리 비디오 ID (예: dQw4w9WgXcQ)를 입력하세요. 비디오 ID는 YouTube URL에서 'v=' 뒤의 11자리 문자입니다."
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
            
            # 메인 콘텐츠 영역을 탭으로 구성 (큰 글씨로)
            st.markdown("---")
            st.markdown("## 📄 결과")
            
            # 큰 탭 만들기
            col1, col2 = st.columns(2)
            
            with col1:
                transcript_tab = st.button("📜 원본 자막 보기", use_container_width=True, type="secondary")
            
            with col2:
                summary_tab = st.button("🤖 AI 요약 보기", use_container_width=True, type="primary")
            
            # 세션 상태로 탭 관리
            if 'active_tab' not in st.session_state:
                st.session_state.active_tab = 'summary'  # 기본값을 AI 요약으로
            
            if transcript_tab:
                st.session_state.active_tab = 'transcript'
            elif summary_tab:
                st.session_state.active_tab = 'summary'
            
            # 선택된 탭에 따라 내용 표시
            if st.session_state.active_tab == 'transcript':
                st.markdown("---")
                st.markdown("### 📜 원본 자막")
                if show_transcript:
                    st.text_area(
                        "추출된 자막",
                        transcript,
                        height=400,
                        help="자막 내용을 확인하고 복사할 수 있습니다.",
                        key="transcript_area"
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
            
            elif st.session_state.active_tab == 'summary':
                st.markdown("---")
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

if __name__ == "__main__":
    main()
