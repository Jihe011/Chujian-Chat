"""
阿里云TTS客户端
封装阿里云DashScope TTS API调用
"""

import os
import json
import logging
import requests
from typing import Optional, Dict, List, Any
from pathlib import Path
import sys

# 添加项目根目录到sys.path以便导入logger
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from src.utils.logger import log_api_request

try:
    import dashscope
    from dashscope.audio.qwen_tts import SpeechSynthesizer
except ImportError:
    dashscope = None
    SpeechSynthesizer = None

from .voice_data import (
    ALIYUN_VOICE_DESCRIPTIONS,
    get_voice_description,
    get_voices_by_gender,
    get_voices_by_style,
    search_voices,
    get_all_voices,
    SUPPORTED_LANGUAGES,
    SUPPORTED_MODELS
)

logger = logging.getLogger(__name__)


class AliyunTTSClient:
    """阿里云TTS客户端"""

    def __init__(self, api_key: str, model: str = "qwen3-tts-flash"):
        """
        初始化阿里云TTS客户端

        Args:
            api_key: 阿里云DashScope API密钥
            model: TTS模型名称 (qwen3-tts-flash / qwen-tts)
        """
        if dashscope is None or SpeechSynthesizer is None:
            raise ImportError(
                "dashscope package is not installed. "
                "Please install it with: pip install dashscope"
            )

        self.api_key = api_key
        self.model = model

        # 设置API基础URL（北京地域）
        dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

        logger.info(f"阿里云TTS客户端初始化完成，模型: {model}")

    def synthesize(
        self,
        text: str,
        voice: str = "Cherry",
        language_type: str = "Chinese",
        stream: bool = False,
        output_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        生成TTS音频

        Args:
            text: 要合成的文本
            voice: 音色名称（可以是英文或中文）
            language_type: 语种 (Chinese/English/German/Italian/Portuguese/Spanish/Japanese/Korean/French/Russian/Auto)
            stream: 是否使用流式输出（当前版本不支持流式输出）
            output_dir: 输出目录，如果为None则返回音频数据

        Returns:
            如果output_dir不为None，返回音频文件路径；否则返回音频数据
        """
        try:
            # 验证参数
            if not self.api_key:
                raise ValueError("API密钥未配置")

            # 将音色名称映射为英文API名称
            from .voice_data import get_voice_api_name
            voice = get_voice_api_name(voice)

            if self.model not in SUPPORTED_MODELS:
                raise ValueError(f"不支持的模型: {self.model}，支持的模型: {SUPPORTED_MODELS}")

            if language_type not in SUPPORTED_LANGUAGES:
                raise ValueError(f"不支持的语种: {language_type}，支持的语种: {SUPPORTED_LANGUAGES}")

            # 调用阿里云TTS API
            logger.info(f"调用阿里云TTS API: model={self.model}, voice={voice}, text={text[:50]}...")
            
            # 记录API请求
            request_data = {
                "model": self.model,
                "text": text[:100] + ("..." if len(text) > 100 else ""),
                "voice": voice,
                "language_type": language_type,
                "stream": stream
            }
            log_api_request(service_name="aliyun_tts", endpoint="https://dashscope.aliyuncs.com/api/v1", request_data=request_data)
            
            response = SpeechSynthesizer.call(
                model=self.model,
                text=text,
                api_key=self.api_key,
                voice=voice,
                language_type=language_type,
                stream=stream
            )

            logger.info(f"API响应状态码: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"TTS请求失败: {response.code} - {response.message}")
                return None

            # 验证API响应
            if not self._validate_api_response(response):
                logger.error("API响应验证失败")
                return None

            # 检查音频数据是否在data字段中
            audio_data = response.output.audio.get('data')
            audio_url = response.output.audio.get('url')

            if audio_data:
                # 音频数据直接返回（base64编码）
                logger.info(f"获取到音频数据，长度: {len(audio_data)}")
            elif audio_url:
                # 音频数据在URL中，需要下载
                logger.info(f"音频数据在URL中，开始下载: {audio_url}")
                try:
                    audio_data = self._download_audio_from_url(audio_url)
                    if not audio_data:
                        logger.error("从URL下载音频失败")
                        return None
                    logger.info(f"从URL下载音频成功，长度: {len(audio_data)}")
                except Exception as e:
                    logger.error(f"下载音频文件失败: {str(e)}", exc_info=True)
                    return None
            else:
                logger.error("API响应中既没有音频数据也没有URL")
                return None

            if output_dir:
                # 保存到文件 - 非流式输出为WAV格式
                output_path = self._save_audio_to_file(audio_data, output_dir, voice, is_pcm=False)
                logger.info(f"音频已保存到: {output_path}")
                return output_path
            else:
                return audio_data

        except Exception as e:
            logger.error(f"TTS合成失败: {str(e)}", exc_info=True)
            return None

    def _download_audio_from_url(self, url: str) -> Optional[str]:
        """从URL下载音频数据

        Args:
            url: 音频文件的URL

        Returns:
            Base64编码的音频数据，失败则返回None
        """
        try:
            logger.info(f"开始从URL下载音频: {url}")
            
            # 记录API请求
            log_api_request(service_name="audio_download", endpoint=url, request_data={"method": "GET", "url": url})
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # 检查响应内容
            if not response.content:
                logger.error("下载的音频文件内容为空")
                return None

            # 将音频数据转换为base64编码
            import base64
            audio_data = base64.b64encode(response.content).decode('utf-8')
            logger.info(f"从URL下载音频成功，原始大小: {len(response.content)} 字节，base64编码后: {len(audio_data)} 字节")

            return audio_data

        except Exception as e:
            logger.error(f"从URL下载音频失败: {str(e)}", exc_info=True)
            return None

    def _save_audio_to_file(self, audio_data: str, output_dir: str, voice: str, is_pcm: bool = False) -> str:
        """保存音频数据到文件

        Args:
            audio_data: Base64编码的音频数据
            output_dir: 输出目录
            voice: 音色名称
            is_pcm: 是否为PCM格式数据（流式输出时为True）
        """
        import base64
        import struct

        # 验证输入数据
        if not audio_data:
            logger.error("音频数据为空")
            raise ValueError("音频数据为空")

        # 确保输出目录存在
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        import time
        timestamp = int(time.time())
        filename = f"aliyun_tts_{voice}_{timestamp}.wav"
        filepath = output_path / filename

        # 解码Base64音频数据
        try:
            logger.info(f"开始解码Base64音频数据，原始长度: {len(audio_data)}")
            audio_bytes = base64.b64decode(audio_data)
            logger.info(f"解码后的音频数据长度: {len(audio_bytes)}")

            if len(audio_bytes) == 0:
                logger.error("解码后的音频数据为空")
                raise ValueError("解码后的音频数据为空")

            if is_pcm:
                # PCM格式需要生成WAV文件头
                # WAV文件头结构：RIFF头 + fmt块 + data块
                sample_rate = 24000  # 阿里云TTS默认采样率
                channels = 1  # 单声道
                bits_per_sample = 16  # 16-bit

                # 计算数据大小
                data_size = len(audio_bytes)

                # 生成WAV文件头
                wav_header = bytearray()

                # RIFF头
                wav_header.extend(b'RIFF')
                wav_header.extend(struct.pack('<I', 36 + data_size))  # 文件总大小
                wav_header.extend(b'WAVE')

                # fmt块
                wav_header.extend(b'fmt ')
                wav_header.extend(struct.pack('<I', 16))  # fmt块大小
                wav_header.extend(struct.pack('<H', 1))   # 音频格式（PCM）
                wav_header.extend(struct.pack('<H', channels))  # 声道数
                wav_header.extend(struct.pack('<I', sample_rate))  # 采样率
                wav_header.extend(struct.pack('<I', sample_rate * channels * bits_per_sample // 8))  # 字节率
                wav_header.extend(struct.pack('<H', channels * bits_per_sample // 8))  # 块对齐
                wav_header.extend(struct.pack('<H', bits_per_sample))  # 位深度

                # data块
                wav_header.extend(b'data')
                wav_header.extend(struct.pack('<I', data_size))  # 数据大小

                # 合并WAV文件头和音频数据
                audio_bytes = bytes(wav_header) + audio_bytes
                logger.info(f"生成WAV文件头，总长度: {len(audio_bytes)}")

            # 保存到文件
            logger.info(f"开始保存音频文件到: {filepath}")
            with open(filepath, 'wb') as f:
                f.write(audio_bytes)

            # 验证文件大小
            file_size = os.path.getsize(filepath)
            logger.info(f"音频文件已保存，文件大小: {file_size} 字节")

            if file_size == 0:
                logger.error("保存的音频文件大小为0")
                raise ValueError("保存的音频文件大小为0")

            return str(filepath)
        except Exception as e:
            logger.error(f"保存音频文件失败: {str(e)}", exc_info=True)
            raise

    def _validate_api_response(self, response) -> bool:
        """验证API响应是否有效

        Args:
            response: API响应对象

        Returns:
            bool: 是否有效
        """
        try:
            # 检查状态码
            if response.status_code != 200:
                logger.error(f"API响应状态码异常: {response.status_code}")
                return False

            # 检查输出
            if not hasattr(response, 'output') or response.output is None:
                logger.error("API响应缺少output属性或为None")
                return False

            # 检查音频
            if not hasattr(response.output, 'audio') or response.output.audio is None:
                logger.error("API响应缺少audio属性或为None")
                return False

            # 检查音频数据或URL（至少有一个存在）
            has_data = 'data' in response.output.audio and response.output.audio['data'] is not None
            has_url = 'url' in response.output.audio and response.output.audio['url'] is not None

            if not has_data and not has_url:
                logger.error("API响应中既没有音频数据也没有URL")
                return False

            # 如果有数据，检查数据长度
            if has_data and not response.output.audio['data']:
                logger.warning("API响应音频数据为空，但存在URL，将尝试从URL下载")
                # 不返回False，因为URL可能有效

            return True
        except Exception as e:
            logger.error(f"验证API响应时出错: {str(e)}", exc_info=True)
            return False

    def get_voice_descriptions(self) -> Dict[str, Dict[str, Any]]:
        """获取所有音色的描述信息"""
        return ALIYUN_VOICE_DESCRIPTIONS.copy()

    def get_voice_description(self, voice_name: str) -> Dict[str, Any]:
        """获取指定音色的描述信息"""
        return get_voice_description(voice_name)

    def get_voices_by_gender(self, gender: str) -> List[str]:
        """按性别获取音色列表"""
        return get_voices_by_gender(gender)

    def get_voices_by_style(self, style: str) -> List[str]:
        """按风格获取音色列表"""
        return get_voices_by_style(style)

    def search_voices(self, keyword: str) -> List[Dict[str, Any]]:
        """搜索音色"""
        return search_voices(keyword)

    def get_all_voices(self) -> List[Dict[str, Any]]:
        """获取所有音色信息"""
        return get_all_voices()

    def generate_preview(
        self,
        voice: str,
        text: str = "你好，这是一个音色预览。",
        language_type: str = "Chinese",
        output_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        生成音色预览音频

        Args:
            voice: 音色名称
            text: 预览文本
            language_type: 语种
            output_dir: 输出目录

        Returns:
            预览音频文件路径
        """
        return self.synthesize(
            text=text,
            voice=voice,
            language_type=language_type,
            stream=False,
            output_dir=output_dir
        )

    def validate_api_key(self) -> bool:
        """验证API密钥是否有效"""
        try:
            # 尝试获取音色列表来验证API密钥
            response = SpeechSynthesizer.call(
                model=self.model,
                text="测试",
                api_key=self.api_key,
                voice="Cherry",
                language_type="Chinese",
                stream=False
            )

            if response.status_code == 200:
                return True
            else:
                logger.warning(f"API密钥验证失败: {response.code} - {response.message}")
                return False
        except Exception as e:
            logger.error(f"API密钥验证异常: {str(e)}")
            return False
