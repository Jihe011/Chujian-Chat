"""
语音处理模块
负责处理语音相关功能，包括:
- 语音请求识别
- TTS语音生成
- 语音文件管理
- 清理临时文件
"""

import os
import logging
import re
import emoji
import sys
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from data.config import config

# 修改logger获取方式，确保与main模块一致
logger = logging.getLogger('main')


class TTSProvider(Enum):
    """TTS服务提供商"""
    FISH_AUDIO = "fish_audio"
    ALIYUN = "aliyun"


class TTSService:
    """TTS服务类，支持多提供商"""

    def __init__(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
        self.voice_dir = os.path.join(self.root_dir, "data", "voices")

        # 获取TTS配置
        self.tts_provider = config.media.text_to_speech.tts_provider
        self.tts_api_key = config.media.text_to_speech.tts_api_key
        self.tts_model_id = config.media.text_to_speech.tts_model_id

        # 阿里云TTS配置
        self.aliyun_tts_api_key = config.media.text_to_speech.aliyun_tts_api_key
        self.aliyun_tts_model = config.media.text_to_speech.aliyun_tts_model
        self.aliyun_voice = config.media.text_to_speech.aliyun_voice
        self.aliyun_language_type = config.media.text_to_speech.aliyun_language_type

        # 确保语音目录存在
        os.makedirs(self.voice_dir, exist_ok=True)

        # 初始化阿里云客户端（如果使用阿里云）
        self.aliyun_client = None
        if self.tts_provider == TTSProvider.ALIYUN.value:
            try:
                from .aliyun_client import AliyunTTSClient
                self.aliyun_client = AliyunTTSClient(
                    api_key=self.aliyun_tts_api_key,
                    model=self.aliyun_tts_model
                )
                logger.info(f"TTS服务初始化完成，提供商: {self.tts_provider}")
            except Exception as e:
                logger.error(f"初始化阿里云TTS客户端失败: {str(e)}")
                self.aliyun_client = None
        else:
            logger.info(f"TTS服务初始化完成，提供商: {self.tts_provider}")

    def _clear_tts_text(self, text: str) -> str:
        """用于清洗回复,使得其适合进行TTS"""
        # 完全移除emoji表情符号
        try:
            # 将emoji转换为空字符串
            text = emoji.replace_emoji(text, replace='')
        except Exception:
            pass

        text = text.replace('$',',').replace('\r\n', '\n').replace('\r', '\n').replace('\n',',')
        text = re.sub(r'\[.*?\]','', text)
        return text.strip()

    def _generate_audio_file_fish_audio(self, text: str) -> Optional[str]:
        """使用Fish Audio SDK生成语音"""
        try:
            from fish_audio_sdk import Session, TTSRequest

            # 确保语音目录存在
            if not os.path.exists(self.voice_dir):
                os.makedirs(self.voice_dir)

            # 生成唯一的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            voice_path = os.path.join(self.voice_dir, f"voice_{timestamp}.mp3")

            # 调用TTS API
            with open(voice_path, "wb") as f:
                for chunk in Session(self.tts_api_key).tts(TTSRequest(
                    reference_id=self.tts_model_id,
                    text=text
                )):
                    f.write(chunk)

            return voice_path

        except Exception as e:
            logger.error(f"Fish Audio TTS生成失败: {str(e)}")
            return None

    def _generate_audio_file_aliyun(self, text: str) -> Optional[str]:
        """使用阿里云TTS生成语音"""
        try:
            if self.aliyun_client is None:
                logger.error("阿里云TTS客户端未初始化")
                return None

            # 生成唯一的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            voice_path = os.path.join(self.voice_dir, f"voice_{timestamp}.wav")

            # 调用阿里云TTS
            result = self.aliyun_client.synthesize(
                text=text,
                voice=self.aliyun_voice,
                language_type=self.aliyun_language_type,
                stream=False,
                output_dir=self.voice_dir
            )

            if result:
                return result

            return None

        except Exception as e:
            logger.error(f"阿里云TTS生成失败: {str(e)}")
            return None

    def _generate_audio_file(self, text: str) -> Optional[str]:
        """调用TTS API生成语音（根据提供商自动选择）"""
        try:
            if self.tts_provider == TTSProvider.ALIYUN.value:
                return self._generate_audio_file_aliyun(text)
            else:
                return self._generate_audio_file_fish_audio(text)
        except Exception as e:
            logger.error(f"TTS生成失败: {str(e)}")
            return None

    def _del_audio_file(self, audio_file_path: str):
        """清理语音目录中的旧文件"""
        try:
            if os.path.isfile(audio_file_path):
                os.remove(audio_file_path)
                logger.info(f"清理语音文件: {audio_file_path}")
        except Exception as e:
            logger.error(f"清理语音文件失败 {audio_file_path}: {str(e)}")

    def get_voice_descriptions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有音色的描述信息（仅阿里云支持）"""
        if self.tts_provider == TTSProvider.ALIYUN.value and self.aliyun_client:
            return self.aliyun_client.get_voice_descriptions()
        return {}

    def get_voice_description(self, voice_name: str) -> Dict[str, Any]:
        """获取指定音色的描述信息（仅阿里云支持）"""
        if self.tts_provider == TTSProvider.ALIYUN.value and self.aliyun_client:
            return self.aliyun_client.get_voice_description(voice_name)
        return {}

    def get_voices_by_gender(self, gender: str) -> List[str]:
        """按性别获取音色列表（仅阿里云支持）"""
        if self.tts_provider == TTSProvider.ALIYUN.value and self.aliyun_client:
            return self.aliyun_client.get_voices_by_gender(gender)
        return []

    def get_voices_by_style(self, style: str) -> List[str]:
        """按风格获取音色列表（仅阿里云支持）"""
        if self.tts_provider == TTSProvider.ALIYUN.value and self.aliyun_client:
            return self.aliyun_client.get_voices_by_style(style)
        return []

    def search_voices(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索音色（仅阿里云支持）"""
        if self.tts_provider == TTSProvider.ALIYUN.value and self.aliyun_client:
            return self.aliyun_client.search_voices(keyword)
        return []

    def get_all_voices(self) -> List[Dict[str, Any]]:
        """获取所有音色信息（仅阿里云支持）"""
        if self.tts_provider == TTSProvider.ALIYUN.value and self.aliyun_client:
            return self.aliyun_client.get_all_voices()
        return []

    def generate_preview(self, voice: str, text: str = "你好，这是一个音色预览。") -> Optional[str]:
        """生成音色预览音频（仅阿里云支持）"""
        if self.tts_provider == TTSProvider.ALIYUN.value and self.aliyun_client:
            return self.aliyun_client.generate_preview(
                voice=voice,
                text=text,
                language_type=self.aliyun_language_type,
                output_dir=self.voice_dir
            )
        return None

    def validate_api_key(self) -> bool:
        """验证API密钥是否有效"""
        if self.tts_provider == TTSProvider.ALIYUN.value and self.aliyun_client:
            return self.aliyun_client.validate_api_key()
        # Fish Audio的验证需要实际调用，这里返回True作为默认
        return True

    def get_current_provider(self) -> str:
        """获取当前使用的TTS提供商"""
        return self.tts_provider

    def get_current_config(self) -> Dict[str, Any]:
        """获取当前TTS配置"""
        config_dict = {
            "provider": self.tts_provider,
            "voice_dir": self.voice_dir
        }

        if self.tts_provider == TTSProvider.ALIYUN.value:
            config_dict.update({
                "aliyun_model": self.aliyun_tts_model,
                "aliyun_voice": self.aliyun_voice,
                "aliyun_language_type": self.aliyun_language_type
            })
        else:
            config_dict.update({
                "fish_audio_model": self.tts_model_id
            })

        return config_dict


tts = TTSService()