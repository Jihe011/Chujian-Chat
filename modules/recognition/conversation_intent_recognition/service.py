"""
私聊对话意图识别模块

功能：
- 识别用户是否要结束对话（晚安、拜拜等）
- 检测沉默时长，触发主动闲聊
- 判断是否需要等待/思考
- 生成快速回复
"""

import json
import logging
import os
import sys
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from openai import AsyncOpenAI

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.autoupdate.updater import Updater
from data.config import config
from src.utils.logger import log_api_request

logger = logging.getLogger('main')


class ConversationIntent(Enum):
    """对话意图类型"""
    NORMAL = "normal"
    END_GOODNIGHT = "end_goodnight"
    END_BYE = "end_bye"
    NEED_WAIT = "need_wait"
    SILENT_TRIGGER = "silent_trigger"
    QUESTION_PENDING = "question_pending"
    PASSIVE_LISTEN = "passive_listen"


@dataclass
class ConversationIntentResult:
    """识别结果"""
    should_respond: bool
    intent: ConversationIntent
    action: str
    quick_reply: str = ""
    reasoning: str = ""
    confidence: float = 0.0


class ConversationIntentRecognitor:
    """私聊对话意图识别服务"""

    def __init__(self, llm_service=None):
        self.intent_settings = {
            "api_key": config.intent_recognition.api_key,
            "base_url": config.intent_recognition.base_url,
            "model": config.intent_recognition.model,
            "temperature": 0.3
        }

        self.updater = Updater()
        self.client = AsyncOpenAI(
            api_key=self.intent_settings["api_key"],
            base_url=self.intent_settings["base_url"],
            default_headers={
                "Content-Type": "application/json",
                "User-Agent": self.updater.get_version_identifier(),
                "X-Chujian-Version": self.updater.get_current_version()
            }
        )

        self._load_config()

    def _load_config(self):
        """加载配置"""
        self.silent_intervals = {
            "morning_rush": 15,
            "work_time": 30,
            "afternoon": 25,
            "evening": 20,
            "night": 60,
            "late_night": 120
        }

        self.end_patterns = {
            "goodnight": ["晚安", "睡了", "去睡觉", "休息了", "晚安啦", "好梦"],
            "bye": ["拜拜", "不聊了", "先忙", "先走了", "下次聊", "一会聊", "先"],
            "later": ["一会聊", "待会说", "等会说"]
        }

        self.quick_replies = {
            "goodnight": ["晚安~好梦", "晚安早点休息", "好梦~"],
            "bye": ["拜拜~", "嗯嗯拜", "下次见"],
            "wait": ["等一下...", "让我想想", "我查查"],
            "initiative": [
                "在干嘛呢",
                "你今天怎么样",
                "有啥好玩的吗"
            ]
        }

        self.initiative_probability = 0.3
        self.enabled = True

    def _get_current_interval(self) -> int:
        """根据当前时间获取动态间隔"""
        hour = datetime.now().hour

        if 7 <= hour < 9:
            return self.silent_intervals["morning_rush"]
        elif 9 <= hour < 12:
            return self.silent_intervals["work_time"]
        elif 12 <= hour < 18:
            return self.silent_intervals["afternoon"]
        elif 18 <= hour < 22:
            return self.silent_intervals["evening"]
        elif 22 <= hour < 24:
            return self.silent_intervals["night"]
        else:
            return self.silent_intervals["late_night"]

    def _check_end_pattern(self, message: str) -> Optional[str]:
        """检查是否包含结束语"""
        message_lower = message.lower()
        
        for end_type, patterns in self.end_patterns.items():
            for pattern in patterns:
                if pattern in message:
                    return end_type
        return None

    def _get_quick_reply(self, end_type: str) -> str:
        """获取快速回复"""
        if end_type in self.quick_replies:
            replies = self.quick_replies[end_type]
            return random.choice(replies) if replies else ""
        return ""

    async def recognize(
        self,
        user_message: str,
        context: Dict
    ) -> ConversationIntentResult:
        """
        识别对话意图

        Args:
            user_message: 用户最新消息
            context: 对话上下文，包含：
                - last_reply_time: 上次回复时间
                - conversation_history: 对话历史
                - user_online: 用户在线状态

        Returns:
            ConversationIntentResult: 识别结果
        """
        if not self.enabled:
            return ConversationIntentResult(
                should_respond=True,
                intent=ConversationIntent.NORMAL,
                action="normal_reply",
                reasoning="功能未启用"
            )

        # 1. 先检查结束语模式（最快）
        end_type = self._check_end_pattern(user_message)
        if end_type:
            if end_type in ["goodnight", "goodnight"]:
                return ConversationIntentResult(
                    should_respond=True,
                    intent=ConversationIntent.END_GOODNIGHT,
                    action="end_conversation",
                    quick_reply=self._get_quick_reply("goodnight"),
                    reasoning=f"检测到结束语：{user_message}"
                )
            else:
                return ConversationIntentResult(
                    should_respond=True,
                    intent=ConversationIntent.END_BYE,
                    action="end_conversation",
                    quick_reply=self._get_quick_reply("bye"),
                    reasoning=f"检测到结束语：{user_message}"
                )

        # 2. 检查沉默时长
        last_reply_time = context.get("last_reply_time")
        if last_reply_time:
            if isinstance(last_reply_time, str):
                last_reply_time = datetime.fromisoformat(last_reply_time)
            minutes_since_reply = (datetime.now() - last_reply_time).total_seconds() / 60
            threshold = self._get_current_interval()

            if minutes_since_reply >= threshold:
                # 检查是否触发主动闲聊
                if random.random() < self.initiative_probability:
                    initiative_reply = random.choice(self.quick_replies["initiative"])
                    return ConversationIntentResult(
                        should_respond=True,
                        intent=ConversationIntent.SILENT_TRIGGER,
                        action="trigger_initiative",
                        quick_reply=initiative_reply,
                        reasoning=f"沉默{minutes_since_reply:.0f}分钟，触发主动闲聊",
                        confidence=0.7
                    )

        # 3. 使用LLM进行意图识别
        try:
            result = await self._recognize_with_llm(user_message, context)
            return result
        except Exception as e:
            logger.error(f"LLM意图识别失败: {e}")
            return ConversationIntentResult(
                should_respond=True,
                intent=ConversationIntent.NORMAL,
                action="normal_reply",
                reasoning=f"识别失败，默认正常回复: {str(e)}"
            )

    async def _recognize_with_llm(
        self,
        user_message: str,
        context: Dict
    ) -> ConversationIntentResult:
        """使用LLM进行深度意图识别"""

        minutes_since_reply = 0
        last_reply_time = context.get("last_reply_time")
        if last_reply_time:
            if isinstance(last_reply_time, str):
                last_reply_time = datetime.fromisoformat(last_reply_time)
            minutes_since_reply = (datetime.now() - last_reply_time).total_seconds() / 60

        history_text = ""
        history = context.get("conversation_history", [])
        if history:
            recent = history[-3:] if len(history) >= 3 else history
            history_text = "\n".join([
                f"用户: {h.get('content', '')}" if h.get('role') == 'user'
                else f"你: {h.get('content', '')}"
                for h in recent
            ])

        current_time = datetime.now().strftime("%H:%M")
        threshold = self._get_current_interval()

        prompt = f"""你在和用户私聊。请分析当前对话情况，判断应该如何回应。

## 当前情况
- 当前时间：{current_time}
- 距你上次回复已过去：{minutes_since_reply:.1f}分钟
- 沉默触发阈值：{threshold}分钟
- 用户最新消息：{user_message}

## 对话历史（最近3条）
{history_text if history_text else "暂无历史"}

## 判断要求
请以JSON格式输出分析结果：
{{
    "should_respond": true/false,
    "intent": "normal/wait/end_goodnight/end_bye/silence/question_pending",
    "action": "normal_reply/quick_reply/end_conversation/trigger_initiative",
    "quick_reply": "",
    "reasoning": "判断理由"
}}

## 判断标准
1. 用户消息包含"晚安"、"睡了"等 → intent=end_goodnight, action=end_conversation
2. 用户消息包含"拜拜"、"不聊了"等 → intent=end_bye, action=end_conversation  
3. 沉默超过{threshold}分钟且用户没回复 → intent=silence
4. 你需要思考/查资料 → intent=wait, action=quick_reply
5. 用户只是简单回复"嗯"、"好" → 可能不需要追问
6. 其他正常对话 → intent=normal, action=normal_reply

注意：
- 不要过度解读用户的简短回复
- 如果用户明显要结束，不要追问新话题
- 简短回复是真人聊天的正常行为
"""

        try:
            log_api_request(
                service_name="conversation_intent",
                endpoint=str(self.client.base_url),
                request_data={"prompt": prompt[:500]}
            )

            response = await self.client.chat.completions.create(
                model=self.intent_settings["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=self.intent_settings["temperature"],
                max_tokens=500
            )

            content = response.choices[0].message.content

            # 解析JSON结果
            result = self._parse_response(content)
            return result

        except Exception as e:
            logger.error(f"意图识别LLM调用失败: {e}")
            return ConversationIntentResult(
                should_respond=True,
                intent=ConversationIntent.NORMAL,
                action="normal_reply",
                reasoning=f"LLM调用失败: {str(e)}"
            )

    def _parse_response(self, content: str) -> ConversationIntentResult:
        """解析LLM返回的JSON结果"""
        try:
            # 尝试提取JSON
            if "{" in content and "}" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                json_str = content[start:end]
                data = json.loads(json_str)

                should_respond = data.get("should_respond", True)
                intent_str = data.get("intent", "normal")
                action = data.get("action", "normal_reply")
                quick_reply = data.get("quick_reply", "")
                reasoning = data.get("reasoning", "")

                # 映射intent
                intent_map = {
                    "normal": ConversationIntent.NORMAL,
                    "wait": ConversationIntent.NEED_WAIT,
                    "end_goodnight": ConversationIntent.END_GOODNIGHT,
                    "end_bye": ConversationIntent.END_BYE,
                    "silence": ConversationIntent.SILENT_TRIGGER,
                    "question_pending": ConversationIntent.QUESTION_PENDING
                }
                intent = intent_map.get(intent_str, ConversationIntent.NORMAL)

                return ConversationIntentResult(
                    should_respond=should_respond,
                    intent=intent,
                    action=action,
                    quick_reply=quick_reply,
                    reasoning=reasoning,
                    confidence=0.8
                )

        except Exception as e:
            logger.error(f"解析意图识别结果失败: {e}")

        return ConversationIntentResult(
            should_respond=True,
            intent=ConversationIntent.NORMAL,
            action="normal_reply",
            reasoning="解析失败，默认正常"
        )


def get_conversation_intent_recognitor(llm_service=None) -> ConversationIntentRecognitor:
    """获取意图识别器实例"""
    return ConversationIntentRecognitor(llm_service)