"""
图像识别 AI 服务模块
提供与图像识别 API 的交互功能，包括:
- 图像识别
- 文本生成
- API请求处理
- 错误处理
"""

import base64
import logging
import requests
from typing import Optional
import os
import time

# 修改logger获取方式确保与main模块一致
logger = logging.getLogger('main')

class ImageRecognitionService:
    def __init__(self, api_key: str, base_url: str, temperature: float, model: str):
        self.api_key = api_key
        self.base_url = base_url
        # 确保 temperature 在有效范围内
        self.temperature = min(max(0.0, temperature), 1.0)  # 限制在 0-1 之间
        self.model = model

        # 使用 Updater 获取版本信息并设置请求头
        from src.autoupdate.updater import Updater
        updater = Updater()
        version = updater.get_current_version()
        version_identifier = updater.get_version_identifier()

        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'User-Agent': version_identifier,
            'X-KouriChat-Version': version
        }

        if temperature > 1.0:
            logger.warning(f"Temperature值 {temperature} 超出范围，已自动调整为 1.0")

    def recognize_image(self, image_path: str, is_emoji: bool = False) -> str:
        """使用 Moonshot AI 识别图片内容并返回文本"""
        try:
            # 验证图片路径
            if not os.path.exists(image_path):
                logger.error(f"图片文件不存在: {image_path}")
                return "抱歉，图片文件不存在"

            # 验证文件大小
            file_size = os.path.getsize(image_path) / (1024 * 1024)  # 转换为MB
            if file_size > 100:  # API限制为100MB
                logger.error(f"图片文件过大 ({file_size:.2f}MB): {image_path}")
                return "抱歉，图片文件太大了"

            # 读取并编码图片
            try:
                with open(image_path, 'rb') as img_file:
                    image_content = base64.b64encode(img_file.read()).decode('utf-8')
            except Exception as e:
                logger.error(f"读取图片文件失败: {str(e)}")
                return "抱歉，读取图片时出现错误"

            # 设置提示词
            text_prompt = "请描述这个图片" if not is_emoji else "这是一张微信聊天的图片截图，请描述这个聊天窗口左边的聊天用户用户发送的最后一张表情，不要去识别聊天用户的头像"

            # 准备请求数据
            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_content}"
                                }
                            },
                            {
                                "type": "text",
                                "text": text_prompt
                            }
                        ]
                    }
                ],
                "temperature": self.temperature
            }

            # 发送请求
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=data,
                    timeout=30  # 添加超时设置
                )

                # 检查响应状态
                if response.status_code != 200:
                    logger.error(f"API请求失败 - 状态码: {response.status_code}, 响应: {response.text}")
                    return "抱歉，图片识别服务暂时不可用"

                # 处理响应
                result = response.json()
                if 'choices' not in result or not result['choices']:
                    logger.error(f"API响应格式异常: {result}")
                    return "抱歉，无法解析图片内容"

                recognized_text = result['choices'][0]['message']['content']

                # 处理表情包识别结果
                if is_emoji:
                    if "最后一张表情包是" in recognized_text:
                        recognized_text = recognized_text.split("最后一张表情包是", 1)[1].strip()
                    recognized_text = "用户发送了一张表情包，表情包的内容是：：" + recognized_text
                else:
                    recognized_text = "用户发送了一张照片，照片的内容是：" + recognized_text

                logger.info(f"Moonshot AI图片识别结果: {recognized_text}")
                return recognized_text

            except requests.exceptions.Timeout:
                logger.error("API请求超时")
                return "抱歉，图片识别服务响应超时"
            except requests.exceptions.RequestException as e:
                logger.error(f"API请求异常: {str(e)}")
                return "抱歉，图片识别服务出现错误"
            except Exception as e:
                logger.error(f"处理API响应失败: {str(e)}")
                return "抱歉，处理图片识别结果时出现错误"

        except Exception as e:
            logger.error(f"图片识别过程失败: {str(e)}", exc_info=True)
            return "抱歉，图片识别过程出现错误"

    def understand_video(self, video_path: str) -> str:
        """使用 Qwen-Omni 理解视频内容"""
        try:
            from data.config import config
            
            video_config = getattr(config.media, 'video_omni', None)
            if not video_config or not video_config.get('enabled', False):
                logger.info("视频理解服务未启用")
                return ""
            
            # 检查视频文件是否存在
            if not os.path.exists(video_path):
                logger.error(f"视频文件不存在: {video_path}")
                return ""
            
            # 复制视频到本地视频服务器目录
            import shutil
            import hashlib
            
            filename = os.path.basename(video_path)
            ext = os.path.splitext(filename)[1] or ".mp4"
            timestamp = int(time.time() * 1000)
            random_hash = hashlib.md5(str(timestamp).encode()).hexdigest()[:8]
            new_filename = f"video_{timestamp}_{random_hash}{ext}"
            
            video_server_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "videos")
            os.makedirs(video_server_dir, exist_ok=True)
            dest_path = os.path.join(video_server_dir, new_filename)
            
            shutil.copy2(video_path, dest_path)
            logger.info(f"视频已复制到: {dest_path}")
            
            api_key = video_config.get('api_key', '')
            base_url = video_config.get('base_url', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
            model = video_config.get('model', 'qwen3.5-omni-plus')
            method = video_config.get('method', 'vision')
            fps = float(video_config.get('fps', 2.0))
            prompt = video_config.get('prompt', '请详细描述这个视频的内容，包括画面和音频信息')
            
            if not api_key:
                logger.error("视频理解 API Key 未配置")
                return ""
            
            # 根据配置选择视频理解方式
            if method == 'vision':
                # 视觉理解方式 - 使用本地文件路径
                logger.info("使用视觉理解方式（本地文件路径）")
                
                # 使用图像识别相同的模型
                vision_model = self.model
                
                from src.services.ai.video_frame_service import VideoFrameService
                # 不传 base_url，使用默认值 api/v1
                frame_service = VideoFrameService(api_key, model=vision_model, fps=fps, max_frames=500)
                
                if not frame_service.is_available():
                    logger.error("VideoFrameService 不可用")
                    return ""
                
                result = frame_service.understand_video(dest_path, prompt)
                
                if result and not result.startswith("["):
                    logger.info(f"视频理解成功: {result[:100]}...")
                    return f"用户发送了一段视频，视频的内容是：{result}"
                else:
                    logger.warning(f"视频理解失败或未返回结果: {result}")
                    return ""
            else:
                # 全模态方式 - 使用公网URL
                logger.info("使用全模态方式（公网URL）")
                
                public_url_base = video_config.get('public_url', 'https://video.geiniyigmmp.dpdns.org/videos/')
                # 确保 URL 以 / 结尾
                if not public_url_base.endswith('/'):
                    public_url_base += '/'
                public_url = f"{public_url_base}{new_filename}"
                logger.info(f"公网URL: {public_url}")
                
                from src.services.ai.omni_service import OmniService
                omni_service = OmniService(api_key, base_url, model)
                
                if not omni_service.is_available():
                    logger.error("OmniService 不可用")
                    return ""
                
                result = omni_service.understand_video_url(public_url, prompt)
                
                if result and not result.startswith("["):
                    logger.info(f"视频理解成功: {result[:100]}...")
                    return f"用户发送了一段视频，视频的内容是：{result}"
                else:
                    logger.warning(f"视频理解失败或未返回结果: {result}")
                    return ""
                    
        except Exception as e:
            logger.error(f"视频理解失败: {str(e)}")
            return ""

    def chat_completion(self, messages: list, **kwargs) -> Optional[str]:
        """发送聊天请求到 Moonshot AI"""
        try:
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": kwargs.get('temperature', self.temperature)
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data
            )
            response.raise_for_status()

            result = response.json()
            return result['choices'][0]['message']['content']

        except Exception as e:
            logger.error(f"图像识别服务请求失败: {str(e)}")
            return None