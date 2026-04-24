import logging
import random
from datetime import datetime, timedelta
import threading
import time
import os
import shutil
from src.utils.console import print_status

try:
    from src.autoupdate.core.manager import initialize_system
    initialize_system()
    print_status("网络适配器初始化成功", "success", "CHECK")
except Exception as e:
    print_status(f"网络适配器初始化失败: {str(e)}", "error", "CROSS")

from data.config import config, DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL, MAX_TOKEN, TEMPERATURE, MAX_GROUPS
from src.wechat import get_wechat_adapter
import re
from src.handlers.emoji import EmojiHandler
from src.handlers.image import ImageHandler
from src.handlers.message import MessageHandler
from src.services.ai.llm_service import LLMService
from src.services.ai.image_recognition_service import ImageRecognitionService
from modules.memory.memory_service import MemoryService
from modules.memory.content_generator import ContentGenerator
from src.utils.logger import LoggerConfig
from colorama import init, Style
from src.handlers.autosend import AutoSendHandler
import queue
from collections import defaultdict

stop_event = threading.Event()

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

config_path = os.path.join(root_dir, 'src', 'config', 'config.json')
config_template_path = os.path.join(root_dir, 'src', 'config', 'config.json.template')

if not os.path.exists(config_path) and os.path.exists(config_template_path):
    logger = logging.getLogger('main')
    logger.info("配置文件不存在正在从模板创建...")
    shutil.copy2(config_template_path, config_path)
    logger.info(f"已从模板创建配置文件: {config_path}")

init()

logger = None
listen_list = []

def initialize_logging():
    global logger, listen_list

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logger_config = LoggerConfig(root_dir)
    logger = logger_config.setup_logger('main')
    listen_list = config.user.listen_list
    
    logging.getLogger("autoupdate").setLevel(logging.DEBUG)
    logging.getLogger("autoupdate.core").setLevel(logging.DEBUG)
    logging.getLogger("autoupdate.interceptor").setLevel(logging.DEBUG)
    logging.getLogger("autoupdate.network_optimizer").setLevel(logging.DEBUG)

wait = 1

private_message_queue = queue.Queue()
group_message_queue = queue.Queue()

class PrivateChatBot:
    def __init__(self, message_handler, image_recognition_service, auto_sender, emoji_handler):
        self.message_handler = message_handler
        self.image_recognition_service = image_recognition_service
        self.auto_sender = auto_sender
        self.emoji_handler = emoji_handler
        self.wx = get_wechat_adapter()
        self.robot_name = self.wx.get_robot_name()
        logger.info(f"私聊机器人初始化完成 - 机器人名称: {self.robot_name}")
        
        from data.config import config
        default_avatar_path = config.behavior.context.avatar_dir
        self.current_avatar = os.path.basename(default_avatar_path)
        logger.info(f"私聊机器人使用默认人设: {self.current_avatar}")

    def handle_private_message(self, msg, chat_name):
        try:
            username = msg.sender
            content = getattr(msg, 'content', None) or getattr(msg, 'text', None)

            self.auto_sender.start_countdown()

            logger.info(f"[私聊] 收到消息 - 来自: {username}")
            logger.debug(f"[私聊] 消息内容: {content}")

            img_path = None
            is_emoji = False
            is_image_recognition = False
            video_data = None

            if content and "[视频]" in content:
                logger.info("检测到视频消息，尝试获取视频...")
                video_path = getattr(msg, 'path', None) or getattr(msg, 'file_path', None)
                if not video_path:
                    video_path = getattr(msg, 'file', None)
                
                if not video_path or not os.path.exists(video_path):
                    search_dirs = [
                        os.path.join(root_dir, "wxauto文件"),
                        os.path.join(os.path.expanduser("~"), "Documents", "WeChat Files"),
                        os.path.join(os.path.expanduser("~"), "Documents", "WeChat Files", "WeChat Files"),
                    ]
                    
                    video_path = None
                    latest_time = 0
                    
                    for search_dir in search_dirs:
                        if not os.path.exists(search_dir):
                            continue
                        try:
                            for root, dirs, files in os.walk(search_dir):
                                for f in files:
                                    if f.endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                                        full_path = os.path.join(root, f)
                                        mtime = os.path.getmtime(full_path)
                                        if mtime > latest_time:
                                            latest_time = mtime
                                            video_path = full_path
                                            logger.info(f"找到视频: {full_path}, 时间: {mtime}")
                        except Exception as e:
                            logger.warning(f"搜索目录失败 {search_dir}: {e}")
                
                if video_path and os.path.exists(video_path):
                    logger.info(f"视频文件路径: {video_path}")
                    
                    import hashlib
                    
                    video_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "videos")
                    video_dir = os.path.normpath(video_dir)
                    os.makedirs(video_dir, exist_ok=True)
                    
                    filename = os.path.basename(video_path)
                    ext = os.path.splitext(filename)[1] or ".mp4"
                    timestamp = int(time.time() * 1000)
                    random_hash = hashlib.md5(str(timestamp).encode()).hexdigest()[:8]
                    new_filename = f"video_{timestamp}_{random_hash}{ext}"
                    dest_path = os.path.join(video_dir, new_filename)
                    
                    shutil.copy2(video_path, dest_path)
                    logger.info(f"视频已保存到: {dest_path}")
                    
                    video_description = self.image_recognition_service.understand_video(dest_path)
                    logger.info(f"视频理解结果: {video_description[:100]}..." if video_description else "无结果")
                    content = video_description if video_description else content
                    is_image_recognition = True
                else:
                    logger.warning(f"视频文件路径不存在: {video_path}, content: {content}")

            if content and content.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                img_path = content
                is_emoji = False
                content = None

            if content and content.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                video_path = content
                logger.info(f"检测到视频文件: {video_path}")
                try:
                    if os.path.exists(video_path):
                        video_description = self.image_recognition_service.understand_video(video_path)
                        logger.info(f"视频理解结果: {video_description[:100]}..." if video_description else "无结果")
                        content = video_description if video_description else content
                        is_image_recognition = True
                    else:
                        logger.warning(f"视频文件不存在: {video_path}")
                except Exception as e:
                    logger.error(f"视频理解失败: {e}")

            if content and "[动画表情]" in content:
                img_path = self.emoji_handler.capture_and_save_screenshot(username)
                is_emoji = True
                content = None

            if img_path:
                recognized_text = self.image_recognition_service.recognize_image(img_path, is_emoji)
                content = recognized_text if content is None else f"{content} {recognized_text}"
                is_image_recognition = True

            if content or video_data:
                self.message_handler.handle_user_message(
                    content=content,
                    chat_id=chat_name,
                    sender_name=username,
                    username=username,
                    is_group=False,
                    is_image_recognition=is_image_recognition,
                    video_data=video_data
                )

        except Exception as e:
            logger.error(f"[私聊] 消息处理失败: {str(e)}")

class GroupChatBot:
    def __init__(self, message_handler_class, base_config, auto_sender, emoji_handler, image_recognition_service):
        self.message_handlers = {}
        self.message_handler_class = message_handler_class
        self.base_config = base_config
        self.auto_sender = auto_sender
        self.emoji_handler = emoji_handler
        self.image_recognition_service = image_recognition_service
        self.wx = get_wechat_adapter()
        self.robot_name = self.wx.get_robot_name()
        logger.info(f"群聊机器人初始化完成 - 机器人名称: {self.robot_name}")

    def get_group_handler(self, group_name, group_config=None):
        if group_name not in self.message_handlers:
            avatar_path = group_config.avatar if group_config and group_config.avatar else self.base_config.behavior.context.avatar_dir
            
            full_avatar_path = os.path.join(root_dir, avatar_path)
            prompt_path = os.path.join(full_avatar_path, "avatar.md")
            group_prompt_content = ""
            
            if os.path.exists(prompt_path):
                with open(prompt_path, "r", encoding="utf-8") as file:
                    group_prompt_content = file.read()
            else:
                logger.error(f"群聊人设文件不存在: {prompt_path}")
                group_prompt_content = prompt_content
            
            handler = self.message_handler_class(
                root_dir=root_dir,
                api_key=self.base_config.llm.api_key,
                base_url=self.base_config.llm.base_url,
                model=self.base_config.llm.model,
                max_token=self.base_config.llm.max_tokens,
                temperature=self.base_config.llm.temperature,
                max_groups=self.base_config.behavior.context.max_groups,
                robot_name=self.robot_name,
                prompt_content=group_prompt_content,
                image_handler=image_handler,
                emoji_handler=self.emoji_handler,
                memory_service=memory_service,
                content_generator=content_generator
            )
            
            handler.current_avatar = os.path.basename(full_avatar_path)
            handler.avatar_real_names = handler._extract_avatar_names(full_avatar_path)
            
            self.message_handlers[group_name] = handler
            logger.info(f"[群聊] 为群聊 '{group_name}' 创建专用处理器，使用人设: {handler.current_avatar}, 识别名字: {handler.avatar_real_names}")
        
        return self.message_handlers[group_name]

    def handle_group_message(self, msg, group_name, group_config=None):
        try:
            username = msg.sender
            content = getattr(msg, 'content', None) or getattr(msg, 'text', None)

            logger.info(f"[群聊] 收到消息 - 群聊: {group_name}, 发送者: {username}")
            logger.debug(f"[群聊] 消息内容: {content}")

            handler = self.get_group_handler(group_name, group_config)

            img_path = None
            is_emoji = False
            is_image_recognition = False

            if self.robot_name and content:
                content = re.sub(f'@{self.robot_name}\u2005', '', content).strip()

            if content and content.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                img_path = content
                is_emoji = False
                content = None

            if content and "[动画表情]" in content:
                img_path = self.emoji_handler.capture_and_save_screenshot(username)
                is_emoji = True
                content = None

            if img_path:
                recognized_text = self.image_recognition_service.recognize_image(img_path, is_emoji)
                content = recognized_text if content is None else f"{content} {recognized_text}"
                is_image_recognition = True

            if content:
                handler.handle_user_message(
                    content=content,
                    chat_id=group_name,
                    sender_name=username,
                    username=username,
                    is_group=True,
                    is_image_recognition=is_image_recognition
                )

        except Exception as e:
            logger.error(f"[群聊] 消息处理失败: {str(e)}")

def private_message_processor():
    logger.info("私聊消息处理线程启动")
    
    while not stop_event.is_set():
        try:
            msg_data = private_message_queue.get(timeout=1)
            if msg_data is None:
                break
                
            msg, chat_name = msg_data
            private_chat_bot.handle_private_message(msg, chat_name)
            private_message_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"私聊消息处理线程出错: {str(e)}")

def group_message_processor():
    logger.info("群聊消息处理线程启动")
    
    while not stop_event.is_set():
        try:
            msg_data = group_message_queue.get(timeout=1)
            if msg_data is None:
                break
                
            msg, group_name, group_config = msg_data
            group_chat_bot.handle_group_message(msg, group_name, group_config)
            group_message_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"群聊消息处理线程出错: {str(e)}")

prompt_content = ""
emoji_handler = None
image_handler = None
memory_service = None
content_generator = None
message_handler = None
image_recognition_service = None
auto_sender = None
private_chat_bot = None
group_chat_bot = None
ROBOT_WX_NAME = ""
processed_messages = set()
last_processed_content = {}

def initialize_services():
    global prompt_content, emoji_handler, image_handler, memory_service, content_generator
    global message_handler, image_recognition_service, auto_sender, private_chat_bot, group_chat_bot, ROBOT_WX_NAME

    try:
        from src.autoupdate.core.manager import get_manager
        try:
            status = get_manager().get_status()
            if status:
                print_status(f"热更新模块已就绪", "success", "CHECK")
            else:
                print_status("热更新模块状态异常", "warning", "CROSS")
                
        except Exception as e:
            print_status(f"检查热更新模块状态时出现异常: {e}", "error", "ERROR")
            
    except Exception as e:
        print_status(f"检查热更新模块状态时出现异常: {e}", "error", "ERROR")

    avatar_dir = os.path.join(root_dir, config.behavior.context.avatar_dir)
    prompt_path = os.path.join(avatar_dir, "avatar.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as file:
            prompt_content = file.read()
    else:
        raise FileNotFoundError(f"avatar.md 文件不存在: {prompt_path}")

    emoji_handler = EmojiHandler(root_dir)
    image_handler = ImageHandler(
        root_dir=root_dir,
        api_key=config.llm.api_key,
        base_url=config.llm.base_url,
        image_model=config.media.image_generation.model
    )
    memory_service = MemoryService(
        root_dir=root_dir,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model=MODEL,
        max_token=MAX_TOKEN,
        temperature=TEMPERATURE,
        max_groups=MAX_GROUPS
    )

    content_generator = ContentGenerator(
        root_dir=root_dir,
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL,
        model=MODEL,
        max_token=MAX_TOKEN,
        temperature=TEMPERATURE
    )

    image_recognition_service = ImageRecognitionService(
        api_key=config.media.image_recognition.api_key,
        base_url=config.media.image_recognition.base_url,
        temperature=config.media.image_recognition.temperature,
        model=config.media.image_recognition.model
    )

    try:
        wx = get_wechat_adapter()
        ROBOT_WX_NAME = wx.get_robot_name()
        logger.info(f"获取到机器人名称: {ROBOT_WX_NAME}")
    except Exception as e:
        logger.warning(f"获取机器人名称失败: {str(e)}")
        ROBOT_WX_NAME = ""

    message_handler = MessageHandler(
        root_dir=root_dir,
        api_key=config.llm.api_key,
        base_url=config.llm.base_url,
        model=config.llm.model,
        max_token=config.llm.max_tokens,
        temperature=config.llm.temperature,
        max_groups=config.behavior.context.max_groups,
        robot_name=ROBOT_WX_NAME,
        prompt_content=prompt_content,
        image_handler=image_handler,
        emoji_handler=emoji_handler,
        memory_service=memory_service,
        content_generator=content_generator
    )

    auto_sender = AutoSendHandler(message_handler, config, listen_list)

    private_chat_bot = PrivateChatBot(message_handler, image_recognition_service, auto_sender, emoji_handler)
    group_chat_bot = GroupChatBot(MessageHandler, config, auto_sender, emoji_handler, image_recognition_service)

    auto_sender.start_countdown()

def message_dispatcher():
    global ROBOT_WX_NAME, logger, wait, processed_messages, last_processed_content

    wx = None
    last_window_check = 0
    check_interval = 600
    first_run = True  # 首次运行标记，用于跳过启动前的历史消息
    startup_time = datetime.now()  # 记录程序启动时间

    logger.info("消息分发器启动")

    while not stop_event.is_set():
        try:
            current_time = time.time()

            if wx is None or (current_time - last_window_check > check_interval):
                wx = get_wechat_adapter()
                wx._ensure_main_window()
                if not wx.get_session_list():
                    time.sleep(5)
                    continue
                last_window_check = current_time

            # 使用新的 get_new_messages 方法检测新消息
            for who in listen_list:
                try:
                    wx._current_chat = who
                    new_messages = wx.get_new_messages(who=who, max_new_minutes=60)
                    
                    if not new_messages:
                        # 如果没有新消息，且是首次运行，仍然保持首次运行状态
                        if first_run:
                            continue
                    
                    if not new_messages:
                        continue
                    
                    logger.info(f"[{who}] 检测到 {len(new_messages)} 条新消息")
                    
                    # 首次运行检测是否完成
                    filter_completed = False
                    
                    for msg in new_messages:
                        content = msg.get('content', '')
                        sender = msg.get('sender', '')
                        msg_type = msg.get('type', 'text')
                        msg_time = msg.get('time', '')  # 如 "11:07"
                        
                        # 首次运行：对比消息时间和启动时间
                        if first_run and not filter_completed:
                            if msg_time:
                                try:
                                    tm = re.match(r'^(\d{1,2}):(\d{2})$', msg_time)
                                    if tm:
                                        msg_hour = int(tm.group(1))
                                        msg_minute = int(tm.group(2))
                                        msg_dt = startup_time.replace(hour=msg_hour, minute=msg_minute, second=0)
                                        if msg_dt < startup_time:
                                            logger.info(f"[{who}] 首次运行，跳过历史消息: {msg_time}")
                                            continue
                                except Exception as e:
                                    logger.debug(f"时间解析失败: {e}")
                            # 如果没有时间信息或时间解析失败，安全起见也跳过
                            else:
                                logger.info(f"[{who}] 首次运行，跳过无时间消息")
                                continue
                            
                            # 该消息需要处理，标记首次过滤完成
                            filter_completed = True
                        
                        # 过滤自己发送的消息
                        if sender == 'self':
                            logger.debug(f"跳过自己发送的消息: {content[:20]}...")
                            continue
                        
                        # 处理图片和视频消息
                        if msg_type in ('image', 'video'):
                            logger.info(f"[{who}] 检测到 {msg_type} 消息，尝试保存...")
                            try:
                                save_folder = os.path.join(root_dir, 'vx文件保存', msg_type == 'image' and '图片' or '视频')
                                os.makedirs(save_folder, exist_ok=True)
                                media_path = wx.save_media(who, target_folder=save_folder)
                                if media_path and os.path.exists(media_path):
                                    logger.info(f"媒体已保存: {media_path}")
                                    # 调用图像识别服务理解内容
                                    if msg_type == 'image':
                                        from src.services.ai.image_recognition_service import ImageRecognitionService
                                        img_service = ImageRecognitionService(
                                            api_key=config.media.image_recognition.api_key,
                                            base_url=config.media.image_recognition.base_url,
                                            temperature=config.media.image_recognition.temperature,
                                            model=config.media.image_recognition.model
                                        )
                                        content = img_service.recognize_image(media_path, is_emoji=False)
                                        logger.info(f"图片识别结果: {content[:50]}...")
                                    elif msg_type == 'video':
                                        from src.services.ai.image_recognition_service import ImageRecognitionService
                                        img_service = ImageRecognitionService(
                                            api_key=config.media.image_recognition.api_key,
                                            base_url=config.media.image_recognition.base_url,
                                            temperature=config.media.image_recognition.temperature,
                                            model=config.media.image_recognition.model
                                        )
                                        content = img_service.understand_video(media_path)
                                        logger.info(f"视频理解结果: {content[:50]}...")
                            except Exception as e:
                                logger.error(f"保存/理解媒体失败: {e}")
                        
                        if not content:
                            continue
                        
                        msg_id = f"{who}_{content[:20]}_{msg.get('time', '')}"
                        
                        if msg_id in processed_messages:
                            logger.debug(f"跳过已处理的消息ID: {msg_id}")
                            continue
                        
                        processed_messages.add(msg_id)
                        last_processed_content[who] = content
                        
                        # 创建兼容消息对象
                        chat_msg = type('Msg', (), {
                            'who': who,
                            'sender': msg.get('sender', who),
                            'content': content,
                            'id': msg_id,
                            'type': msg.get('type', 'text')
                        })()
                        
                        logger.debug(f"[分发] 私聊消息 -> 私聊队列: {who}, 内容: {content[:30]}")
                        private_message_queue.put((chat_msg, who))
                        
                except Exception as e:
                    logger.debug(f"处理 {who} 消息失败: {str(e)}")
                    continue
            else:
                # 首次运行完成后，设置为 False
                if first_run:
                    first_run = False
                    logger.info("首次运行结束，已跳过所有历史消息")

        except Exception as e:
            logger.debug(f"消息分发出错: {str(e)}")
            wx = None
            time.sleep(wait)
            continue
        
        time.sleep(1)

def initialize_wx_listener():
    global listen_list, logger

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            wx = get_wechat_adapter()
            if not wx.get_session_list():
                logger.error("未检测到微信会话列表，请确保微信已登录")
                time.sleep(retry_delay)
                continue

            for chat_name in listen_list:
                try:
                    wx.add_listen_chat(who=chat_name, savepic=True, savevoice=True, savefile=True)
                    logger.info(f"成功添加监听: {chat_name}")
                    time.sleep(0.5)
                except Exception as e:
                    logger.error(f"添加监听失败 {chat_name}: {str(e)}")
                    continue

            return wx

        except Exception as e:
            logger.error(f"初始化微信失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                raise Exception("微信初始化失败，请检查微信是否正常运行")

    return None

def main():
    dispatcher_thread = None
    private_thread = None
    group_thread = None
    video_server_thread = None

    try:
        initialize_logging()
        initialize_services()

        video_omni_config = getattr(config.media, 'video_omni', None)
        video_method = video_omni_config.get('method', 'vision') if video_omni_config else 'vision'
        
        if video_method == 'full_modal':
            from src.services.video_server import start_video_server
            video_server_thread = start_video_server()
            if video_server_thread:
                print_status("视频服务器已启动", "success", "CHECK")
        else:
            print_status("抽帧模式：跳过视频服务器启动", "info", "INFO")

        automation_log_dir = os.path.join(root_dir, "logs", "automation")
        if not os.path.exists(automation_log_dir):
            os.makedirs(automation_log_dir)
        os.environ["WXAUTO_LOG_PATH"] = os.path.join(automation_log_dir, "AutomationLog.txt")

        print_status("初始化微信监听...", "info", "BOT")
        wx = initialize_wx_listener()
        if not wx:
            print_status("微信初始化失败，请确保微信已登录并保持在前台运行!", "error", "CROSS")
            return
        print_status("微信监听初始化完成", "success", "CHECK")

        print_status("验证角色记忆存储路径...", "info", "FILE")
        avatar_dir = os.path.join(root_dir, config.behavior.context.avatar_dir)
        avatar_name = os.path.basename(avatar_dir)
        memory_dir = os.path.join(avatar_dir, "memory")
        if not os.path.exists(memory_dir):
            os.makedirs(memory_dir)
            print_status(f"创建角色记忆目录: {memory_dir}", "success", "CHECK")

        print_status("初始化记忆文件...", "info", "FILE")

        for user_name in listen_list:
            print_status(f"为用户 '{user_name}' 创建独立记忆...", "info", "USER")
            memory_service.initialize_memory_files(avatar_name, user_id=user_name)
            print_status(f"用户 '{user_name}' 记忆初始化完成", "success", "CHECK")

        avatar_dir = os.path.join(root_dir, config.behavior.context.avatar_dir)
        prompt_path = os.path.join(avatar_dir, "avatar.md")
        if not os.path.exists(prompt_path):
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write("# 核心人格\n[默认内容]")
            print_status(f"创建人设提示文件", "warning", "WARNING")
        
        print_status("启动并行消息处理系统...", "info", "ANTENNA")
        
        dispatcher_thread = threading.Thread(target=message_dispatcher, name="MessageDispatcher")
        dispatcher_thread.daemon = True
        
        private_thread = threading.Thread(target=private_message_processor, name="PrivateProcessor")
        private_thread.daemon = True
        
        group_thread = threading.Thread(target=group_message_processor, name="GroupProcessor")
        group_thread.daemon = True
        
        dispatcher_thread.start()
        private_thread.start()
        group_thread.start()
        
        print_status("并行消息处理系统已启动", "success", "CHECK")
        print_status("  ├─ 消息分发器线程", "info", "ANTENNA")
        print_status("  ├─ 私聊处理器线程", "info", "USER")
        print_status("  └─ 群聊处理器线程", "info", "USERS")

        print_status("初始化主动消息系统...", "info", "CLOCK")
        print_status("主动消息系统已启动", "success", "CHECK")

        print("-" * 50)
        print_status("系统初始化完成", "success", "STAR_2")
        print("=" * 50)

        while True:
            time.sleep(1)
            
            threads_status = [
                ("消息分发器", dispatcher_thread),
                ("私聊处理器", private_thread),
                ("群聊处理器", group_thread)
            ]
            
            dead_threads = []
            for thread_name, thread in threads_status:
                if not thread.is_alive():
                    dead_threads.append(thread_name)
            
            if dead_threads:
                print_status(f"检测到线程异常: {', '.join(dead_threads)}", "warning", "WARNING")
                time.sleep(5)

    except Exception as e:
        print_status(f"主程序异常: {str(e)}", "error", "ERROR")
        logger.error(f"主程序异常: {str(e)}", exc_info=True)
    finally:
        if 'auto_sender' in locals():
            auto_sender.stop()

        stop_event.set()

        try:
            private_message_queue.put(None)
            group_message_queue.put(None)
        except:
            pass

        threads_to_wait = [
            ("消息分发器", dispatcher_thread),
            ("私聊处理器", private_thread),
            ("群聊处理器", group_thread)
        ]
        
        for thread_name, thread in threads_to_wait:
            if thread and thread.is_alive():
                print_status(f"正在关闭{thread_name}线程...", "info", "SYNC")
                thread.join(timeout=3)
                if thread.is_alive():
                    print_status(f"{thread_name}线程未能正常关闭", "warning", "WARNING")
        
        try:
            from src.services.video_server import stop_video_server
            stop_video_server()
        except:
            pass
        
        print_status("正在关闭系统...", "warning", "STOP")
        print_status("系统已退出", "info", "BYE")
        print("\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        print_status("用户终止程序", "warning", "STOP")
        print_status("感谢使用，再见！", "info", "BYE")
        print("\n")
    except Exception as e:
        print_status(f"程序异常退出: {str(e)}", "error", "ERROR")