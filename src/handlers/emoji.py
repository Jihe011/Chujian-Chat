"""
表情包处理模块
负责处理表情包相关功能，包括:
- 表情标签识别
- 表情包选择
- 文件管理
- 表情频率控制
"""

import os
import random
import logging
from typing import Optional, Dict
from datetime import datetime
import pyautogui
import time
from src.wechat import get_wechat_adapter
from data.config import config

logger = logging.getLogger('main')

class EmojiHandler:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.emoji_dir = os.path.join(root_dir, config.behavior.context.avatar_dir, "emojis")

        self.user_conversation_count: Dict[str, int] = {}
        self.emoji_interval = 6

        self.emotion_types = [
            'happy', 'sad', 'angry', 'neutral', 'loved', 'funny', 'cute', 'bored', 'shy',
            'embarrassed', 'sleepy', 'lonely', 'hungry', 'comfort', 'surprise', 'confused',
            'playful', 'excited', 'tease', 'hot', 'speechless', 'scared', 'emo_1',
            'emo_2', 'emo_3', 'emo_4', 'emo_5', 'afraid', 'amused', 'anxious',
            'confident', 'cold', 'suspicious', 'loving', 'curious', 'envious',
            'jealous', 'miserable', 'stupid', 'sick', 'ashamed', 'withdrawn',
            'indifferent', 'sorry', 'determined', 'crazy', 'bashful', 'depressed',
            'enraged', 'frightened', 'interested', 'hopeful', 'regretful', 'stubborn',
            'thirsty', 'guilty', 'nervous', 'disgusted', 'proud', 'ecstatic',
            'frustrated', 'hurt', 'tired', 'smug', 'thoughtful', 'pained', 'optimistic',
            'relieved', 'puzzled', 'shocked', 'joyful', 'skeptical', 'bad', 'worried',
            'surprised', 'tired', 'reminded', 'evasive']

        self.screenshot_dir = os.path.join(root_dir, 'screenshot')

    def extract_emotion_tags(self, text: str) -> list:
        tags = []
        start = 0
        while True:
            start = text.find('[', start)
            if start == -1:
                break
            end = text.find(']', start)
            if end == -1:
                break
            tag = text[start+1:end].lower()
            if tag in self.emotion_types:
                tags.append(tag)
                logger.info(f"检测到表情标签: {tag}")
            start = end + 1
        return tags

    def update_conversation_count(self, user_id: str) -> None:
        if user_id not in self.user_conversation_count:
            self.user_conversation_count[user_id] = 0
        self.user_conversation_count[user_id] += 1

    def can_send_emoji(self, user_id: str) -> bool:
        count = self.user_conversation_count.get(user_id, 0)
        return count > 0 and count % self.emoji_interval == 0

    def get_emoji_for_emotion(self, emotion_type: str, user_id: str = None) -> Optional[str]:
        if user_id and not self.can_send_emoji(user_id):
            logger.debug(f"用户 {user_id} 当前对话轮数: {self.user_conversation_count.get(user_id, 0)}，跳过表情发送")
            return None
        try:
            target_dir = os.path.join(self.emoji_dir, emotion_type)
            logger.info(f"查找表情包目录: {target_dir}")

            if not os.path.exists(target_dir):
                logger.warning(f"情感目录不存在: {target_dir}")
                return None

            emoji_files = [f for f in os.listdir(target_dir)
                          if f.lower().endswith(('.gif', '.jpg', '.png', '.jpeg'))]

            if not emoji_files:
                logger.warning(f"目录中未找到表情包: {target_dir}")
                return None

            selected = random.choice(emoji_files)
            emoji_path = os.path.join(target_dir, selected)
            logger.info(f"已选择 {emotion_type} 表情包: {emoji_path}")
            return emoji_path

        except Exception as e:
            logger.error(f"获取表情包失败: {str(e)}")
            return None

    def capture_and_save_screenshot(self, who: str) -> Optional[str]:
        try:
            os.makedirs(self.screenshot_dir, exist_ok=True)

            screenshot_path = os.path.join(
                self.screenshot_dir,
                f'{who}_{datetime.now().strftime("%Y%m%d%H%M%S")}.png'
            )

            wx_chat = get_wechat_adapter()
            wx_chat.chat_with(who)
            chat_window = pyautogui.getWindowsWithTitle(who)[0]

            if not chat_window.isActive:
                chat_window.activate()
            if not chat_window.isMaximized:
                chat_window.maximize()

            x, y, width, height = chat_window.left, chat_window.top, chat_window.width, chat_window.height

            time.sleep(1)

            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            screenshot.save(screenshot_path)
            logger.info(f'已保存截图: {screenshot_path}')
            return screenshot_path

        except Exception as e:
            logger.error(f'截取或保存截图失败: {str(e)}')
            return None

    def cleanup_screenshot_dir(self):
        try:
            if os.path.exists(self.screenshot_dir):
                for file in os.listdir(self.screenshot_dir):
                    file_path = os.path.join(self.screenshot_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    except Exception as e:
                        logger.error(f"删除截图失败 {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"清理截图目录失败: {str(e)}")