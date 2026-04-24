"""
TTS 模块
"""
from .service import TTSService, TTSProvider
from .aliyun_client import AliyunTTSClient
from .voice_data import (
    ALIYUN_VOICE_DESCRIPTIONS,
    get_voice_description,
    get_voices_by_gender,
    get_voices_by_style,
    search_voices,
    get_all_voices,
    get_voice_api_name,
    SUPPORTED_LANGUAGES,
    SUPPORTED_MODELS
)

__all__ = [
    'TTSService',
    'TTSProvider',
    'AliyunTTSClient',
    'ALIYUN_VOICE_DESCRIPTIONS',
    'get_voice_description',
    'get_voices_by_gender',
    'get_voices_by_style',
    'search_voices',
    'get_all_voices',
    'get_voice_api_name',
    'SUPPORTED_LANGUAGES',
    'SUPPORTED_MODELS'
]