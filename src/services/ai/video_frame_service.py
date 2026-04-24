"""
视频抽帧理解服务
使用DashScope SDK本地文件路径方式理解视频
"""

import os
import logging

logger = logging.getLogger(__name__)


class VideoFrameService:
    """视频抽帧理解服务 - 使用本地文件路径方式"""
    
    def __init__(self, api_key: str, base_url: str = "https://dashscope.aliyuncs.com/api/v1", 
                 model: str = "qwen3.5-plus-2026-02-15", fps: float = 2.0, max_frames: int = 500):
        """
        初始化视频抽帧服务
        
        Args:
            api_key: API密钥
            base_url: DashScope API地址
            model: 模型名称
            fps: 抽帧频率
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.fps = fps
        self.max_frames = max_frames
        
        # 设置DashScope配置
        try:
            import dashscope
            dashscope.base_http_api_url = base_url
            self._available = True
        except ImportError:
            logger.warning("dashscope 未安装，将使用fallback方式")
            self._available = False
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._available and bool(self.api_key)
    
    def understand_video(self, video_path: str, prompt: str = None) -> str:
        """
        理解视频内容
        
        Args:
            video_path: 本地视频文件路径
            prompt: 提示词
            
        Returns:
            视频描述文本
        """
        if not self.is_available():
            logger.error("VideoFrameService 不可用")
            return "[视频理解服务不可用]"
        
        if not os.path.exists(video_path):
            logger.error(f"视频文件不存在: {video_path}")
            return "[视频文件不存在]"
        
        # 默认提示词
        if not prompt:
            prompt = "请详细描述这个视频的内容，包括画面和音频信息"
        
        try:
            return self._call_dashscope_sdk(video_path, prompt)
        except Exception as e:
            logger.error(f"视频理解失败: {e}")
            return f"[视频理解失败: {str(e)}]"
    
    def _call_dashscope_sdk(self, video_path: str, prompt: str) -> str:
        """调用DashScope SDK"""
        try:
            import dashscope
            from dashscope import MultiModalConversation
            
            # 确保API Key已设置
            dashscope.api_key = self.api_key
            
            # 转换本地路径为file://格式
            video_url = f"file://{os.path.abspath(video_path)}"
            
            logger.info(f"使用本地路径方式理解视频: {video_url}")
            logger.info(f"FPS: {self.fps}, Max_frames: {self.max_frames}, Model: {self.model}")
            
            video_content = {'video': video_url, 'fps': self.fps}
            if self.max_frames:
                video_content['max_frames'] = self.max_frames
            
            messages = [{
                'role': 'user',
                'content': [
                    video_content,
                    {'text': prompt}
                ]
            }]
            
            response = MultiModalConversation.call(
                model=self.model,
                messages=messages
            )
            
            # 解析响应
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                if content and len(content) > 0:
                    result = content[0].get('text', '')
                    logger.info(f"视频理解成功: {result[:100]}...")
                    return result
                else:
                    logger.warning("视频理解返回空结果")
                    return "[视频理解返回空结果]"
            else:
                error_msg = response.message or f"错误码: {response.status_code}"
                logger.error(f"视频理解API错误: {error_msg}")
                return f"[视频理解失败: {error_msg}]"
                
        except Exception as e:
            logger.error(f"DashScope SDK调用失败: {e}")
            raise


def create_video_frame_service(config: dict) -> VideoFrameService:
    """
    根据配置创建视频抽帧服务
    
    Args:
        config: video_omni 配置字典
        
    Returns:
        VideoFrameService实例
    """
    return VideoFrameService(
        api_key=config.get('api_key', ''),
        base_url=config.get('base_url', 'https://dashscope.aliyuncs.com/api/v1'),
        model=config.get('model', 'qwen3.5-plus-2026-02-15'),
        fps=float(config.get('fps', 2.0))
    )