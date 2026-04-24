"""
视频理解服务
使用阿里云 Qwen-Omni 模型理解视频内容（包括视频中的音频）
"""

import os
import base64
import logging
from typing import Optional

logger = logging.getLogger('main')


class OmniService:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """初始化 OpenAI 客户端"""
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"OmniService 初始化完成，使用模型: {self.model}")
        except Exception as e:
            self.client = None
            logger.error(f"初始化 OmniService 失败: {e}")
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        result = self.client is not None and bool(self.api_key)
        logger.info(f"OmniService.is_available: client={self.client is not None}, api_key={'已设置' if self.api_key else '未设置'}, result={result}")
        return result
    
    def understand_video(self, video_path: str, prompt: str = None) -> str:
        """使用 Qwen-Omni 理解视频（含音频）
        
        Args:
            video_path: 视频文件本地路径
            prompt: 提示词（可选）
            
        Returns:
            视频内容的文本描述
        """
        if not self.is_available():
            logger.warning("OmniService 不可用，请检查 API Key 配置")
            return "[视频理解服务未启用或未配置]"
        
        if not os.path.exists(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            return "[视频文件不存在]"
        
        # 默认提示词 - 使用结构化 Prompt（参考全模态.txt文档）
        if not prompt:
            prompt = """请详细描述这个视频，必须包含以下三部分：
1. 按时间顺序描述故事情节（所有视听细节，包括人物、动作、环境、对话）
2. 可见文字列表（带时间戳的文字内容）
3. 语音转文字（说话人、语气、内容、时间戳）
请特别注意视频中的音频内容，包括对话和背景声音。"""
        
        try:
            # 读取视频文件并转为 Base64
            with open(video_path, 'rb') as f:
                video_data = f.read()
            video_base64 = base64.b64encode(video_data).decode('utf-8')
            
            logger.info(f"开始理解视频: {video_path}")
            
            # 构建请求
            # Qwen-Omni 支持视频文件形式（可理解视频中的音频）
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "video",
                            "video": f"data:video/mp4;base64,{video_base64}"
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
            
            # 调用 API（必须使用 stream=True）
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True}
            )
            
            # 收集响应文本
            response_text = ""
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    response_text += chunk.choices[0].delta.content
            
            logger.info(f"视频理解完成，返回文本长度: {len(response_text)}")
            return response_text
            
        except Exception as e:
            logger.error(f"视频理解失败: {e}")
            return f"[视频理解失败: {str(e)}]"
    
    def understand_video_url(self, video_url: str, prompt: str = None) -> str:
        """使用视频 URL 理解视频内容
        
        Args:
            video_url: 视频的公网 URL
            prompt: 提示词（可选）
            
        Returns:
            视频内容的文本描述
        """
        if not self.is_available():
            logger.warning("OmniService 不可用，请检查 API Key 配置")
            return "[视频理解服务未启用或未配置]"
        
        # 默认提示词
        if not prompt:
            prompt = "请详细描述这个视频的内容，包括画面和音频信息"
        
        try:
            logger.info(f"开始理解视频（URL）: {video_url}")
            
            # 使用 video_url 形式
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "video_url",
                            "video_url": {
                                "url": video_url
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
            
            # 调用 API
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True}
            )
            
            # 收集响应文本
            response_text = ""
            for chunk in completion:
                if chunk.choices and chunk.choices[0].delta.content:
                    response_text += chunk.choices[0].delta.content
            
            logger.info(f"视频理解（URL）完成，返回文本长度: {len(response_text)}")
            return response_text
            
        except Exception as e:
            logger.error(f"视频理解（URL）失败: {e}")
            return f"[视频理解失败: {str(e)}]"