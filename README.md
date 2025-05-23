# 📄 SnapTube

이 Streamlit 앱은 YouTube 동영상의 자막을 가져와서 Gemini AI를 사용하여 요약해주는 도구입니다.

## 기능

- YouTube 동영상 URL 또는 비디오 ID를 입력하여 자막 추출
- Gemini AI를 사용한 자막 요약
- 원본 자막과 요약본 동시 표시
- 마크다운 형식의 가독성 좋은 요약 보고서

## 설치 방법

1. 저장소를 클론합니다:
```bash
git clone <repository-url>
cd <repository-directory>
```

2. 필요한 패키지를 설치합니다:
```bash
pip install -r requirements.txt
```

## 사용 방법

1. Google AI Studio에서 API 키를 발급받습니다 (https://makersuite.google.com/app/apikey)

2. 앱을 실행합니다:
```bash
streamlit run app.py
```

3. 웹 브라우저에서 앱이 열리면:
   - Google API 키를 입력합니다
   - YouTube 동영상 URL 또는 비디오 ID를 입력합니다
   - "Generate Summary" 버튼을 클릭합니다

## 주의사항

- API 키는 안전하게 보관하세요
- 일부 동영상은 자막이 없거나 비공개일 수 있습니다
- 긴 동영상의 경우 요약 생성에 시간이 걸릴 수 있습니다 
