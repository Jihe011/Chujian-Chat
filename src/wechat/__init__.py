"""
初见 - 微信模块
基于 pywechat (pyweixin) 实现
"""

from .adapter import WeChatAdapter, PyWeChatAdapter, get_wechat_adapter

__all__ = ['WeChatAdapter', 'PyWeChatAdapter', 'get_wechat_adapter']