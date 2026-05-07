"""Internationalization (i18n) support for multiple languages."""

import streamlit as st

# Translation dictionary: key -> {language_code: translated_text}
TRANSLATIONS = {
    # Sidebar labels
    "THEME": {
        "en": "THEME",
        "zh": "主题",
    },
    "PROVIDER": {
        "en": "PROVIDER",
        "zh": "服务提供商",
    },
    "STYLE": {
        "en": "STYLE",
        "zh": "摘要风格",
    },
    "LANGUAGE": {
        "en": "LANGUAGE",
        "zh": "语言",
    },
    "TRANSCRIPTION_METHOD": {
        "en": "TRANSCRIPTION METHOD",
        "zh": "转录方式",
    },
    "WHISPER_MODEL": {
        "en": "WHISPER MODEL",
        "zh": "Whisper 模型",
    },
    "ADVANCED_SETTINGS": {
        "en": "ADVANCED SETTINGS",
        "zh": "高级设置",
    },
    "CHUNK_SIZE": {
        "en": "CHUNK SIZE",
        "zh": "分块大小",
    },
    "PARALLEL_CALLS": {
        "en": "PARALLEL CALLS",
        "zh": "并行调用数",
    },
    "MAX_TOKENS": {
        "en": "MAX TOKENS",
        "zh": "最大令牌数",
    },
    "AUDIO_SPEED": {
        "en": "AUDIO SPEED",
        "zh": "音频速度",
    },
    "SAVE": {
        "en": "SAVE",
        "zh": "保存",
    },
    "RELOAD": {
        "en": "RELOAD",
        "zh": "重新加载",
    },
    "EDIT_YAML": {
        "en": "EDIT YAML",
        "zh": "编辑 YAML",
    },
    
    # Main panel labels
    "URL_INPUT": {
        "en": "Video URL",
        "zh": "视频 URL",
    },
    "SUMMARIZE_URL": {
        "en": "SUMMARIZE URL",
        "zh": "总结 URL",
    },
    "FILE_UPLOAD": {
        "en": "FILE UPLOAD",
        "zh": "上传文件",
    },
    "CLEAR_FILE": {
        "en": "CLEAR FILE",
        "zh": "清除文件",
    },
    "RUN": {
        "en": "RUN",
        "zh": "运行",
    },
    "CLOSE": {
        "en": "CLOSE",
        "zh": "关闭",
    },
    
    # Status messages
    "PROCESSING": {
        "en": "Processing...",
        "zh": "处理中...",
    },
    "SUCCESS": {
        "en": "✅ Summary generated successfully!",
        "zh": "✅ 摘要生成成功！",
    },
    "ERROR": {
        "en": "❌ Error occurred during processing",
        "zh": "❌ 处理过程中出错",
    },
    "LOADING": {
        "en": "Loading...",
        "zh": "加载中...",
    },
    
    # Tabs
    "URL_TAB": {
        "en": "📺 URL",
        "zh": "📺 URL",
    },
    "FILE_TAB": {
        "en": "📁 FILE",
        "zh": "📁 文件",
    },
    
    # Buttons
    "COPY": {
        "en": "Copy to Clipboard",
        "zh": "复制到剪贴板",
    },
    "DOWNLOAD": {
        "en": "Download",
        "zh": "下载",
    },
    "REFRESH": {
        "en": "Refresh",
        "zh": "刷新",
    },
    
    # Messages
    "ENTER_URL": {
        "en": "Enter video URL (YouTube, TikTok, Instagram, etc.)",
        "zh": "输入视频 URL (YouTube, TikTok, Instagram 等)",
    },
    "UPLOAD_HINT": {
        "en": "Upload a video or audio file, or text transcript",
        "zh": "上传视频、音频文件或文本转录",
    },
    "NO_URL": {
        "en": "⚠️ Please enter a video URL",
        "zh": "⚠️ 请输入视频 URL",
    },
    "NO_FILE": {
        "en": "⚠️ Please upload a file",
        "zh": "⚠️ 请上传文件",
    },
    "HISTORY": {
        "en": "📜 HISTORY",
        "zh": "📜 历史记录",
    },
    "SUMMARY": {
        "en": "Summary",
        "zh": "摘要",
    },
    "TITLE": {
        "en": "🎬 Video Summarizer",
        "zh": "🎬 视频摘要生成器",
    },
    "SUBTITLE": {
        "en": "AI-powered video transcription and summarization",
        "zh": "AI 驱动的视频转录和摘要",
    },
}


def get_text(key: str, language: str = None) -> str:
    """Get translated text for a given key.
    
    Args:
        key: Translation key
        language: Language code ('en' or 'zh'). If None, uses session state.
    
    Returns:
        Translated text or the key itself if not found
    """
    if language is None:
        language = st.session_state.get("app_language", "en")
    
    if key not in TRANSLATIONS:
        return key
    
    return TRANSLATIONS[key].get(language, TRANSLATIONS[key].get("en", key))


def init_i18n():
    """Initialize language preference in session state."""
    if "app_language" not in st.session_state:
        st.session_state.app_language = "en"


def get_language_selector():
    """Create and return language selector for sidebar.
    
    Returns:
        Selected language code ('en' or 'zh')
    """
    lang_options = {
        "English": "en",
        "中文 (Chinese)": "zh",
    }
    
    current_lang = st.session_state.get("app_language", "en")
    current_idx = 0 if current_lang == "en" else 1
    
    selected_display = st.radio(
        "🌐 LANGUAGE / 语言",
        options=list(lang_options.keys()),
        index=current_idx,
        horizontal=True,
        key="language_selector",
    )
    
    selected_lang = lang_options[selected_display]
    if selected_lang != current_lang:
        st.session_state.app_language = selected_lang
        st.rerun()
    
    return selected_lang
