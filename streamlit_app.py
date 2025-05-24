# --- Gemini 요약 ---
def summarize_text(text, api_key):
    """Gemini로 요약 생성 - 개선된 버전"""
    try:
        genai.configure(api_key=api_key)
        
        max_length = 30000 
        if len(text) > max_length:
            text = text[:max_length] + "... (내용이 너무 길어 일부만 요약합니다)"
        
        # Gemini 1.5 Flash를 최우선으로 시도
        models_to_try = [
            'gemini-1.5-flash-latest', # Gemini 1.5 Flash (최신 버전)
            'gemini-1.5-pro-latest',   # Gemini 1.5 Pro (더 강력한 모델, Flash 실패 시 대안)
            'gemini-pro'               # 이전 세대 Pro 모델 (최후의 대안)
        ] 
        
        st.info(f"사용 가능한 Gemini 모델: {', '.join(models_to_try)}")

        for model_name in models_to_try:
            # ... (이하 로직은 동일)
