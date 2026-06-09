"""
自动发送消息处理模块
负责处理自动发送消息的逻辑，包括:
- 倒计时管理
- 消息发送
- 安静时间控制
- LLM驱动的主动发言决策
"""

import asyncio
import json
import logging
import random
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional

from openai import AsyncOpenAI

logger = logging.getLogger('main')


class AutoSendHandler:
    def __init__(self, message_handler, config, listen_list):
        self.message_handler = message_handler
        self.config = config
        self.listen_list = listen_list
        
        # 计时器相关
        self.countdown_timer = None
        self.is_countdown_running = False
        self.countdown_end_time = None
        self.unanswered_count = 0
        self.last_chat_time = None

        # LLM决策相关
        self._init_llm_client()
        
        # 沉默追踪 {user_id: last_message_time}
        self.silence_tracking = {}
        
        # 决策缓存 {user_id: {"time": datetime, "result": {...}}}
        self.decision_cache = {}
        self.decision_cooldown = 15
        
        # 主动发言历史 [{time, user_id, message, user_response}]
        self.initiative_history = []
        
        # 沉默阈值配置
        self.silent_intervals = {
            "morning_rush": 15,
            "work_time": 30,
            "afternoon": 25,
            "evening": 20,
            "night": 60,
            "late_night": 120
        }

    def _init_llm_client(self):
        """初始化LLM客户端"""
        try:
            from src.autoupdate.updater import Updater
            from data.config import config
            
            intent_config = config.intent_recognition
            self.llm_settings = {
                "api_key": intent_config.api_key,
                "base_url": intent_config.base_url,
                "model": intent_config.model,
                "temperature": 0.5
            }
            
            self.updater = Updater()
            self.llm_client = AsyncOpenAI(
                api_key=self.llm_settings["api_key"],
                base_url=self.llm_settings["base_url"],
                default_headers={
                    "Content-Type": "application/json",
                    "User-Agent": self.updater.get_version_identifier(),
                    "X-Chujian-Version": self.updater.get_current_version()
                }
            )
            logger.info("[AutoSend] LLM客户端已初始化")
        except Exception as e:
            logger.error(f"[AutoSend] LLM客户端初始化失败: {e}")
            self.llm_client = None

    def get_dynamic_threshold(self) -> int:
        """根据当前时间获取动态沉默阈值（分钟）"""
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

    def update_user_message_time(self, user_id: str):
        """更新用户最后消息时间"""
        self.silence_tracking[user_id] = datetime.now()
        logger.debug(f"[AutoSend] 更新用户 {user_id} ��后消息时间")

    def get_user_silence_minutes(self, user_id: str) -> int:
        """获取用户沉默时长（分钟）"""
        if user_id not in self.silence_tracking:
            return 0
        return int((datetime.now() - self.silence_tracking[user_id]).total_seconds() / 60)

    def check_candidate_time(self, user_id: str) -> bool:
        """检查是否是候选触发时机（规则过滤）"""
        threshold = self.get_dynamic_threshold()
        silence_minutes = self.get_user_silence_minutes(user_id)
        
        # 1. 检查是否在冷却期内
        if user_id in self.decision_cache:
            cache_entry = self.decision_cache[user_id]
            cache_age = (datetime.now() - cache_entry["time"]).total_seconds() / 60
            if cache_age < self.decision_cooldown:
                logger.debug(f"[AutoSend] 用户 {user_id} 在冷却期内，跳过")
                return False
        
        # 2. 检查沉默时长是否超过阈值
        if silence_minutes < threshold:
            logger.debug(f"[AutoSend] 用户 {user_id} 沉默{silence_minutes}分钟，未达阈值{threshold}分钟")
            return False
        
        # 3. 检查是否在深夜且沉默超过阈值
        if not self.is_quiet_time() or silence_minutes > threshold * 2:
            return True
        
        return False

    def get_decision_context(self, user_id: str) -> Dict:
        """构造LLM决策所需的上下文"""
        threshold = self.get_dynamic_threshold()
        silence_minutes = self.get_user_silence_minutes(user_id)
        
        # 获取最近3次主动发言及用户反应
        recent_initiatives = [
            i for i in self.initiative_history[-3:]
            if i["user_id"] == user_id
        ]
        
        # 计算用户参与度
        user_responses = [i for i in self.initiative_history if i["user_id"] == user_id]
        reply_rate = 0.0
        if user_responses:
            responded = sum(1 for i in user_responses if i.get("user_response"))
            reply_rate = responded / len(user_responses)
        
        context = {
            "user_id": user_id,
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M %A"),
            "silence_duration_minutes": silence_minutes,
            "threshold_minutes": threshold,
            "recent_initiatives": recent_initiatives,
            "user_reply_rate": reply_rate,
            "unanswered_count": self.unanswered_count,
            "is_quiet_time": self.is_quiet_time()
        }
        
        return context

    async def llm_decide_to_speak(self, context: Dict) -> Dict:
        """LLM决策是否主动发言"""
        if not self.llm_client:
            return {"should_speak": False, "message": "", "reason": "LLM未初始化"}
        
        prompt = f"""你是一个微信聊天机器人，需要判断现在是否应该主动给用户发一条消息。

## 当前情况
- 当前时间：{context['current_time']}
- 用户沉默时长：{context['silence_duration_minutes']}分钟
- 沉默触发阈值：{context['threshold_minutes']}分钟
- 当前是否安静时间：{context['is_quiet_time']}
- 用户未回复次数：{context['unanswered_count']}

## 最近主动发言记录
{json.dumps(context['recent_initiatives'], ensure_ascii=False, indent=2) if context['recent_initiatives'] else "无"}

## 用户历史回复率：{context['user_reply_rate']:.1%}

## 判断规则
1. 如果用户沉默未超过阈值，不要主动发言
2. 如果用户之前连续2次不回复，减少主动发言频率
3. 晚上23点后除非用户刚说话，否则不要主动
4. 如果用户回复率高，可以适当主动

## 输���要��
请以JSON格式输出：
{{
    "should_speak": true/false,
    "reason": "简短解释原因（20字以内）",
    "message": "如果要说话，写一句自然、不突兀的消息（20字以内）"
}}

注意：
- 生成的消息要像真人聊天，不刻意、不尴尬
- 可以是关心、提问、分享日常
- 如果不应发言，message为空字符串
"""
        
        try:
            response = await self.llm_client.chat.completions.create(
                model=self.llm_settings["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=self.llm_settings["temperature"],
                max_tokens=300
            )
            
            content = response.choices[0].message.content
            
            # 解析JSON结果
            return self._parse_decision(content)
            
        except Exception as e:
            logger.error(f"[AutoSend] LLM决策失败: {e}")
            return {"should_speak": False, "message": "", "reason": f"LLM调用失败: {str(e)}"}

    def _parse_decision(self, content: str) -> Dict:
        """解析LLM决策结果"""
        try:
            if "{" in content and "}" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                json_str = content[start:end]
                return json.loads(json_str)
        except Exception as e:
            logger.error(f"[AutoSend] 解析决策结果失败: {e}")
        
        return {"should_speak": False, "message": "", "reason": "解析失败"}

    def update_last_chat_time(self):
        """更新最后一次聊天时间"""
        self.last_chat_time = datetime.now()
        self.unanswered_count = 0
        logger.info(f"更新最后聊天时间: {self.last_chat_time}，重置未回复计数器为0")

    def is_quiet_time(self) -> bool:
        """检查当前是否在安静时间段内"""
        try:
            current_time = datetime.now().time()
            quiet_start = datetime.strptime(self.config.behavior.quiet_time.start, "%H:%M").time()
            quiet_end = datetime.strptime(self.config.behavior.quiet_time.end, "%H:%M").time()
            
            if quiet_start <= quiet_end:
                return quiet_start <= current_time <= quiet_end
            else:
                return current_time >= quiet_start or current_time <= quiet_end
        except Exception as e:
            logger.error(f"检查安静时间出错: {str(e)}")
            return False

    def get_random_countdown_time(self):
        """获取随机倒计时时间"""
        min_seconds = int(self.config.behavior.auto_message.min_hours * 3600)
        max_seconds = int(self.config.behavior.auto_message.max_hours * 3600)
        return random.uniform(min_seconds, max_seconds)

    async def auto_send_message(self):
        """自动发送消息（LLM驱动）"""
        if self.is_quiet_time():
            logger.info("[AutoSend] 当前处于安静时间，跳过自动发送消息")
            self.start_countdown()
            return
        
        if not self.listen_list:
            logger.error("[AutoSend] 没有可用的聊天对象")
            self.start_countdown()
            return
        
        # 遍历监听列表，找候选用户
        candidates = []
        for user_id in self.listen_list:
            if self.check_candidate_time(user_id):
                candidates.append(user_id)
        
        if not candidates:
            logger.debug("[AutoSend] 没有候选用户")
            self.start_countdown()
            return
        
        # 随机选择一个候选用户
        user_id = random.choice(candidates)
        context = self.get_decision_context(user_id)
        
        logger.info(f"[AutoSend] 候选用户: {user_id}, 沉默{context['silence_duration_minutes']}分钟")
        
        # LLM决策
        decision = await self.llm_decide_to_speak(context)
        
        # 缓存决策结果
        self.decision_cache[user_id] = {
            "time": datetime.now(),
            "result": decision
        }
        
        if decision.get("should_speak") and decision.get("message"):
            # 发送消息
            message_content = decision["message"]
            logger.info(f"[AutoSend] 主动发送消息到 {user_id}: {message_content}")
            
            try:
                self.message_handler.add_to_queue(
                    chat_id=user_id,
                    content=message_content,
                    sender_name="System",
                    username="System",
                    is_group=False
                )
                
                # 记录主动发言
                self.initiative_history.append({
                    "time": datetime.now(),
                    "user_id": user_id,
                    "message": message_content,
                    "user_response": None
                })
                
                self.unanswered_count += 1
                
            except Exception as e:
                logger.error(f"[AutoSend] 主动发送消息失败: {str(e)}")
        else:
            logger.info(f"[AutoSend] LLM决策不发言: {decision.get('reason', '未知原因')}")
        
        self.start_countdown()

    async def handle_user_response(self, user_id: str, user_message: str):
        """处理用户对主动发言的回复"""
        # 更新主动发言历史中的回复
        for initiative in reversed(self.initiative_history):
            if initiative["user_id"] == user_id and initiative.get("user_response") is None:
                initiative["user_response"] = user_message
                logger.info(f"[AutoSend] 记录用户回复: {user_message[:20]}")
                break
        
        # 更新用户消息时间
        self.update_user_message_time(user_id)

    def start_countdown(self):
        """开始新的倒计时"""
        if self.countdown_timer:
            self.countdown_timer.cancel()
        
        countdown_seconds = self.get_random_countdown_time()
        self.countdown_end_time = datetime.now() + timedelta(seconds=countdown_seconds)
        logger.info(f"[AutoSend] 开始新的倒计时: {countdown_seconds/3600:.2f}小时")
        
        # 使用线程运行异步函数
        def run_async_in_thread():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.auto_send_message())
                loop.close()
            except Exception as e:
                logger.error(f"[AutoSend] 异步执行失败: {e}")
        
        self.countdown_timer = threading.Timer(countdown_seconds, run_async_in_thread)
        self.countdown_timer.daemon = True
        self.countdown_timer.start()
        self.is_countdown_running = True

    def stop(self):
        """停止自动发送消息"""
        if self.countdown_timer:
            self.countdown_timer.cancel()
            self.countdown_timer = None
        self.is_countdown_running = False
        logger.info("自动发送消息已停止")