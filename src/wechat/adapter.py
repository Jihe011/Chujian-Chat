"""
微信适配器 - 基于 pywechat-main (pywechat127)
使用 pywechat-main 多选方案精确区分发送人
支持图片、视频、语音转文字
"""

import time
import logging
import os
import shutil
import re
import json
import threading
from collections import deque
from typing import List, Optional, Dict, Any
from PIL import Image
import numpy as np
import psutil
from datetime import datetime
from data.config import config

logger = logging.getLogger(__name__)

SIGNATURE_DEPTH = 5       # 签名使用的消息条数
SYNC_INTERVAL = 300       # dump_chat_history 同步间隔（秒）
_shared_ui_lock = threading.Lock()  # 所有 PyWeChatAdapter 实例共用，防止跨线程 UI 操作冲突


def capture_window(hwnd):
    """截取窗口图像"""
    import win32gui
    import win32ui
    import win32con
    
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top
    
    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
    saveDC.SelectObject(saveBitMap)
    saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
    
    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)
    
    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)
    
    return img



def detect_sender_by_chatitem(item) -> str:
    """
    通过 ChatTextItemView 控件截图检测发送人
    绿色 = 自己消息
    否则 = 对方消息
    """
    try:
        msg_img = item.capture_as_image()
        if not msg_img:
            return "friend"
        
        arr = np.array(msg_img)
        h, w = arr.shape[:2]
        
        if h < 10 or w < 10:
            return "friend"
        
        # 分析中心区域颜色
        center = arr[5:h-5, 5:w-5]
        center_avg = center.mean(axis=(0,1))
        cr, cg, cb = center_avg[0], center_avg[1], center_avg[2]
        
        # 判断: g - r > 5 表示自己消息（绿色气泡）
        is_green = cg - cr > 5
        
        return "self" if is_green else "friend"
        
    except Exception as e:
        logger.debug(f"detect_sender_by_chatitem 失败: {e}")
        return "friend"


class WeChatAdapter:
    """微信适配器基类"""
    
    def get_robot_name(self) -> str:
        raise NotImplementedError
    
    def send_message(self, msg: str, who: str = None) -> bool:
        raise NotImplementedError
    
    def send_file(self, filepath: str, who: str = None) -> bool:
        raise NotImplementedError
     
    def send_files(self, filepath: str, who: str = None) -> bool:
        raise NotImplementedError
    
    def open_chat(self, name: str):
        raise NotImplementedError
    
    def chat_with(self, name: str) -> bool:
        raise NotImplementedError
    
    def get_current_chat(self) -> Optional[str]:
        raise NotImplementedError
    
    def get_session_list(self) -> List:
        raise NotImplementedError


class PyWeChatAdapter(WeChatAdapter):
    """基于 pywechat/pyweixin 的微信适配器"""
    
    def __init__(self):
        from pyweixin.WeChatTools import Navigator, Tools
        from pyweixin.WeChatAuto import Monitor, Messages, Files, Contacts
        from pyweixin.WeChatAuto import Lists
        
        self.Navigator = Navigator
        self.Monitor = Monitor
        self.Messages = Messages
        self.Files = Files
        self.Tools = Tools
        self.Contacts = Contacts
        
        self._main_window = None
        self._current_chat = None
        self._dialog_windows = {}
        self._listen_status = {}
        self._last_runtime_id = {}  # 记录每个聊天的签名（JSON字符串）
        self._last_sync_time = {}   # {chat_key: 上次dump_chat_history时间戳}
        self._timestamp_map = {}    # {chat_key: {content_truncated: time_string}}
        self._ui_lock = _shared_ui_lock  # 串行化所有UI操作（模块级，跨实例共享）
        self._recently_sent = deque(maxlen=20)  # 最近发送的消息内容，用于区分自发言
        self._msg_seq = 0  # 全局单调递增消息序列号
        self._chat_list_cache = {}  # {friend: (chat_list, last_use_time)} 缓存已打开的聊天列表
        
        self._runtime_ids_file = self._get_runtime_ids_file()
        self.load_runtime_ids()
        
        self._robot_name = None  # 延迟初始化
        
        logger.info("PyWeChat 适配器初始化成功")
    
    def _get_runtime_ids_file(self) -> str:
        """获取 runtime_ids 文件路径"""
        import sys
        # 使用项目根目录
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        data_dir = os.path.join(root_dir, 'data')
        if not os.path.exists(data_dir):
            try:
                os.makedirs(data_dir, exist_ok=True)
            except:
                pass
        return os.path.join(data_dir, 'runtime_ids.json')
    
    def load_runtime_ids(self):
        """从文件加载 runtime_ids（兼容旧格式 → 自动升级）"""
        filepath = self._runtime_ids_file
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    raw = json.load(f)
                # 检测旧格式（纯字符串，非JSON列表），自动重置
                migrated = False
                for k, v in raw.items():
                    if isinstance(v, str) and not v.startswith('['):
                        migrated = True
                        break
                if migrated:
                    logger.info("检测到旧版 runtime_ids 格式，已重置")
                    self._last_runtime_id = {}
                else:
                    self._last_runtime_id = raw
                logger.info(f"已加载 runtime_ids: {len(self._last_runtime_id)} 条")
            except Exception as e:
                logger.warning(f"加载 runtime_ids 失败: {e}")
                self._last_runtime_id = {}
    
    def save_runtime_ids(self):
        """保存 runtime_ids 到文件"""
        filepath = self._runtime_ids_file
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self._last_runtime_id, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存 runtime_ids 失败: {e}")
    
    def _make_signature(self, messages: list, n: int = None) -> list:
        """生成 (sender + content[:50]) 签名列表"""
        n = n or SIGNATURE_DEPTH
        return [f"{m['sender']}:{m['content'][:50]}" for m in messages[:n]]

    def _sync_timestamps(self, target: str):
        """用 _pull_messages 同步内容→时间映射"""
        try:
            raw = self._pull_messages(friend=target, number=30)
            if raw:
                ts_map = {}
                for m in raw:
                    content = m.get('消息内容', '')[:50]
                    if content:
                        ts_map[content] = ''
                self._timestamp_map[target] = ts_map
                self._last_sync_time[target] = time.time()
                logger.debug(f"时间同步完成: {target}, {len(ts_map)} 条")
        except Exception as e:
            logger.debug(f"时间同步失败: {e}")

    def _ensure_main_window(self):
        if self._main_window is None:
            logger.info("正在打开微信...")
            self._main_window = self.Navigator.open_weixin()
            time.sleep(2)
        
        if self._main_window:
            try:
                self._main_window.set_focus()
                time.sleep(0.5)
            except:
                pass
    
    def get_robot_name(self) -> str:
        if self._robot_name:
            return self._robot_name
        try:
            from pyweixin.WeChatTools import Navigator, Tools
            from pyweixin import Uielements
            from pywinauto import Desktop, mouse
            windows = Uielements.Windows
            import time
            moments_window = Navigator.open_moments(is_maximize=False, close_weixin=False)
            time.sleep(1)
            moments_list = moments_window.child_window(control_type='List', auto_id="sns_list")
            rec = moments_list.children()[0].rectangle()
            click_coords = (rec.right - 60, rec.bottom - 35)
            mouse.click(coords=click_coords)
            time.sleep(0.5)
            desktop = Desktop(backend='uia')
            profile_pane = desktop.window(**windows.PopUpProfileWindow)
            group = profile_pane.child_window(control_type='Group', found_index=3).children()[1]
            texts = group.descendants(control_type='Text')
            texts = [item.window_text() for item in texts]
            self._robot_name = texts[0]
            profile_pane.close()
            moments_window.close()
            return self._robot_name
        except Exception as e:
            logger.error(f"获取机器人名称失败: {e}")
            return "初见"
    
    def send_message(self, msg: str, who: str = None) -> bool:
        with self._ui_lock:
            try:
                target = who or self._current_chat
                if not target:
                    return False
                self.Messages.send_messages_to_friend(friend=target, messages=[msg], close_weixin=False)
                self._recently_sent.append(msg)
                return True
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                return False
    
    def send_file(self, filepath: str, who: str = None) -> bool:
        with self._ui_lock:
            try:
                target = who or self._current_chat
                if not target:
                    return False
                self.Files.send_files_to_friend(friend=target, files=[filepath], close_weixin=False)
                self._recently_sent.append(os.path.basename(filepath))
                return True
            except Exception as e:
                logger.error(f"发送文件失败: {e}")
                return False
    
    def send_files(self, filepath: str, who: str = None) -> bool:
        return self.send_file(filepath, who)
    
    def SendMsg(self, msg: str, who: str = None) -> bool:
        """发送消息（兼容旧接口）"""
        return self.send_message(msg, who)
    
    def SendFiles(self, filepath: str, who: str = None) -> bool:
        """发送文件（兼容旧接口）"""
        return self.send_file(filepath, who)
    
    def open_chat(self, name: str):
        with self._ui_lock:
            try:
                self._ensure_main_window()
                self.Navigator.open_dialog_window(friend=name)
                self._current_chat = name
            except Exception as e:
                logger.error(f"打开聊天窗口失败: {e}")
    
    def chat_with(self, name: str) -> bool:
        with self._ui_lock:
            try:
                self._ensure_main_window()
                result = self.Navigator.open_dialog_window(friend=name, is_maximize=True)
                if result:
                    self._current_chat = name
                    return True
                return False
            except Exception as e:
                logger.error(f"打开聊天窗口失败: {e}")
                return False
    
    def get_current_chat(self) -> Optional[str]:
        return self._current_chat
    
    def get_session_list(self) -> List:
        with self._ui_lock:
            try:
                self._ensure_main_window()
                return self.Messages.dump_sessions() or []
            except Exception as e:
                logger.error(f"获取会话列表失败: {e}")
                return []
    
    def get_all_messages_v2(self, who: str = None, max_messages: int = 50) -> list:
        """使用官方 dump_chat_history 方法获取消息（带时间戳和类型）"""
        target = who or self._current_chat
        if not target:
            return []
        if not self._ui_lock.acquire(blocking=False):
            logger.debug("另一UI操作进行中，跳过 get_all_messages_v2")
            return []
        try:
            from pyweixin.WeChatAuto import Messages
            
            self._ensure_main_window()
            
            raw_messages = Messages.dump_chat_history(
                friend=target,
                number=max_messages,
                close_weixin=False,
                is_maximize=False
            )
            
            type_map = {
                '文本': 'text',
                '图片': 'image',
                '视频': 'video',
            }
            
            messages = []
            for raw_msg in raw_messages:
                content = raw_msg.get('消息内容', '')
                sender_raw = raw_msg.get('消息发送人', '')
                msg_time = raw_msg.get('消息发送时间', '')
                msg_type = raw_msg.get('消息类型', '')
                
                if sender_raw in config.user.listen_list:
                    sender = 'friend'
                else:
                    sender = 'self'
                
                messages.append({
                    'content': content,
                    'sender': sender,
                    'type': type_map.get(msg_type, 'text'),
                    'time': msg_time,
                })
            
            logger.debug(f"get_all_messages_v2: 获取 {len(messages)} 条消息")
            return messages
            
        except Exception as e:
            logger.error(f"get_all_messages_v2 失败: {e}")
            return []
        finally:
            self._ui_lock.release()
    
    def get_all_messages(self, who: str = None, update_runtime_id: bool = True) -> list:
        """获取当前聊天窗口的所有消息"""
        from pywinauto import Application
        
        target = who or self._current_chat
        if not target:
            return []
        
        self._ensure_main_window()
        
        try:
            self.Navigator.open_dialog_window(friend=target)
            time.sleep(0.5)
        except:
            pass
        
        try:
            app = Application(backend='uia')
            wechat = None
            
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info['name'].lower()
                    if 'wechat' in name or 'weixin' in name:
                        pid = proc.info['pid']
                        wechat = app.connect(process=pid, timeout=1)
                        time.sleep(0.5)
                        windows = wechat.windows()
                        if windows:
                            break
                except:
                    continue
            
            if not wechat or not windows:
                return []
            
            main = windows[0]
            main.set_focus()
            time.sleep(0.3)
            
            # 截取窗口
            img = capture_window(main.handle)
            rect = main.rectangle()
            
            # 找消息列表
            msg_list = None
            for d in main.descendants():
                try:
                    if d._control_types and d._control_types[0] == 'DataGrid' and '消息' in d.window_text():
                        msg_list = d
                        break
                except:
                    pass
            
            if not msg_list:
                return []
            
            items = msg_list.children()
            messages = []
            current_time_msg = None
            
            for idx, item in enumerate(items):
                try:
                    item_rect = item.rectangle()
                    left = item_rect.left - rect.left + 10
                    top = item_rect.top - rect.top + 10
                    right = item_rect.right - rect.left - 10
                    bottom = item_rect.bottom - rect.top - 10
                    
                    text = item.window_text()
                    class_name = item.class_name()
                    
                    # 检查时间消息
                    if re.match(r'^\d{2}:\d{2}$', text):
                        current_time_msg = text
                        continue
                    
                    if '撤回' in text:
                        continue
                    
                    if class_name == 'mmui::ChatTextItemView':
                        sender = detect_sender_by_chatitem(item)
                    else:
                        sender = "friend"
                    
                    msg_type = 'text'
                    if 'ChatBubbleReferItemView' in class_name:
                        if text == '图片':
                            msg_type = 'image'
                        elif '视频' in text:
                            msg_type = 'video'
                    elif 'ChatVoiceItemView' in class_name:
                        msg_type = 'voice'
                    
                    # 获取 runtime_id
                    runtime_id = ''
                    try:
                        if hasattr(item, 'element_info') and item.element_info:
                            runtime_id = item.element_info.runtime_id
                    except:
                        pass
                    
                    messages.append({
                        'content': text,
                        'sender': sender,
                        'type': msg_type,
                        'time': current_time_msg,
                        'index': idx,
                        'runtime_id': runtime_id
                    })
                    
                except Exception as e:
                    logger.debug(f"处理消息项 {idx} 失败: {e}")
            
            # 只在 get_new_messages 时更新 runtime_id
            if update_runtime_id:
                self._last_runtime_id[target] = messages[-1].get('runtime_id', '') if messages else ''
            
            return messages
            
        except Exception as e:
            logger.error(f"获取消息失败: {e}")
            return []
    
    def _do_pull_messages(self, friend: str, number: int = 20) -> list[dict]:
        """拉消息（无锁，供 _pull_messages 和 _sync_timestamps 复用）
        使用 pywechat-main 多选方案：traverse_message + parse_messages 精确区分发送人"""
        from pyweixin.utils import traverse_message, parse_messages, parse_group_messages
        from pyweixin.WeChatAuto import Navigator, Tools, Lists
        # 使用缓存的 main_window
        cached = self._chat_list_cache.get(friend)
        if cached:
            _, main_window, _ = cached
            try:
                _ = main_window.child_window(**Lists.FriendChatList).children()
            except Exception:
                cached = None
        if not cached:
            self._ensure_main_window()
            self.get_robot_name()
            main_window = Navigator.open_dialog_window(friend=friend, is_maximize=False, search_pages=0)
            self._chat_list_cache[friend] = (None, main_window, time.time())
        else:
            _, main_window, _ = cached
        chat_list = main_window.child_window(**Lists.FriendChatList)
        if not chat_list.exists(timeout=0.1):
            logger.debug(f"[{friend}] 非正常好友或群聊")
            return []
        if not chat_list.children(control_type='ListItem'):
            return []
        is_group = Tools.is_group_chat(main_window)
        try:
            details_with_name = traverse_message(main_window, select=True, number=number)
        except (ValueError, Exception) as e:
            logger.debug(f"[{friend}] traverse_message(select=True) 失败: {e}")
            return []
        if is_group:
            details_without_name = traverse_message(main_window, select=False, number=number)
            contents, senders, mtypes = parse_group_messages(details_with_name, details_without_name)
        else:
            contents, senders, mtypes = parse_messages(friend, self._robot_name or '初见', details_with_name)
        results = []
        for sender, content, mtype in zip(senders, contents, mtypes):
            results.append({'消息发送人': sender, '消息内容': content, '消息类型': mtype})
        return results

    def _pull_messages(self, friend: str, number: int = 20) -> list[dict]:
        """封装 _do_pull_messages，加锁防冲突"""
        if not self._ui_lock.acquire(blocking=False):
            logger.debug(f"[{friend}] 另一UI操作进行中，跳过本轮")
            return []
        try:
            return self._do_pull_messages(friend=friend, number=number)
        except Exception as e:
            logger.error(f"_pull_messages({friend}) 失败: {e}")
            return []
        finally:
            self._ui_lock.release()

    def get_new_messages(self, who: str = None, max_new_minutes: int = 60) -> list:
        """
        获取新消息
        主轮询用 pull_messages（快），多消息签名去重
        定期用 dump_chat_history 同步时间戳
        """
        target = who or self._current_chat
        if not target:
            return []
        
        self._ensure_main_window()
        
        try:
            # 1. 快速拉取（使用本地版本，避免打开朋友圈）
            raw_messages = self._pull_messages(friend=target, number=20)
            logger.info(f"[{target}] _pull_messages 返回 {len(raw_messages)} 条")
            
            if not raw_messages:
                return []
            
            # 2. 处理消息
            messages = []
            type_map = {'文本': 'text', '图片': 'image', '视频': 'video', '文件': 'file', '动画表情': 'emoji'}
            for i, raw_msg in enumerate(raw_messages):
                content = raw_msg.get('消息内容', '')
                sender_raw = raw_msg.get('消息发送人', '')
                
                if sender_raw in config.user.listen_list:
                    sender = 'friend'
                else:
                    sender = 'self'
                
                raw_type = raw_msg.get('消息类型', '文本')
                mtype = type_map.get(raw_type, 'text')
                
                if i == 0:
                    logger.info(f"[{target}] 首条: sender_raw={sender_raw}, sender={sender}, content={content[:40]}, type={raw_type}")
                
                messages.append({
                    'content': content,
                    'sender': sender,
                    'type': mtype,
                    'time': None,
                    'index': self._msg_seq,
                })
                self._msg_seq += 1
            
            if not messages:
                return []
            
            chat_key = target
            
            # 3. 生成当前签名
            current_sig = self._make_signature(messages)
            
            # 4. 加载上次签名
            last_sig_raw = self._last_runtime_id.get(chat_key, '')
            last_sig = json.loads(last_sig_raw) if last_sig_raw else []
            
            # 5. 首次运行 → 存签名 + 同步时间戳
            if not last_sig:
                self._last_runtime_id[chat_key] = json.dumps(current_sig)
                self.save_runtime_ids()
                logger.info(f"[{target}] 首次运行，记录签名: {current_sig[:3]}...")
                self._sync_timestamps(target)
                return []
            
            # 5b. 签名 debug
            logger.info(f"[{target}] last_sig={last_sig[:3]}, current_sig={current_sig[:3]}, 相同={current_sig == last_sig}")
            
            # 6. 签名相同 → 无新消息
            if current_sig == last_sig:
                now = time.time()
                if now - self._last_sync_time.get(chat_key, 0) > SYNC_INTERVAL:
                    self._sync_timestamps(target)
                return []
            
            # 7. 扫描新消息（基于位置偏移匹配，解决相同内容被漏检的问题）
            # 思路：新消息插在开头 → 后面的消息整体下移 → 找第一个与 last_sig 对齐的位置
            new_messages = []
            for start in range(min(len(messages), len(last_sig) + 1)):
                match = True
                for j in range(min(len(messages) - start, len(last_sig))):
                    key = f"{messages[start + j]['sender']}:{messages[start + j]['content'][:50]}"
                    if key != last_sig[j]:
                        match = False
                        break
                if match:
                    new_messages = messages[:start]
                    break
            
            logger.info(f"[{target}] 签名不同，新消息: {len(new_messages)} 条")
            
            # 8. 尝试补时间戳
            ts_map = self._timestamp_map.get(chat_key, {})
            for msg in new_messages:
                t = ts_map.get(msg['content'][:50])
                if t:
                    msg['time'] = t
            
            # 9. 更新签名 + 定期同步
            self._last_runtime_id[chat_key] = json.dumps(current_sig)
            self.save_runtime_ids()
            
            now = time.time()
            if now - self._last_sync_time.get(chat_key, 0) > SYNC_INTERVAL:
                self._sync_timestamps(target)
            
            return new_messages
            
        except Exception as e:
            logger.error(f"get_new_messages 失败: {e}")
            return []
    
    def add_listen_chat(self, who: str, savepic: bool = True, savevoice: bool = True, savefile: bool = True):
        """添加聊天监听"""
        try:
            self._ensure_main_window()
            self.Navigator.open_dialog_window(friend=who, is_maximize=True)
            self._current_chat = who
            self._listen_status[who] = True
            logger.info(f"已添加监听: {who}")
        except Exception as e:
            logger.error(f"添加监听失败 {who}: {e}")

    def save_media(self, who: str = None, target_folder: str = None) -> Optional[str]:
        """保存图片或视频 - 使用 pyweixin 作者的方法"""
        with self._ui_lock:
            import win32gui
            from pywinauto import Desktop
            from pyweixin.Uielements import Lists, Windows
            import shutil
            import os
            
            target = who or self._current_chat
            if not target:
                logger.warning("save_media: 未指定目标聊天")
                return None
            
            try:
                # 打开聊天窗口
                self._ensure_main_window()
                logger.info(f"save_media: 打开聊天窗口: {target}")
                self.Navigator.open_dialog_window(friend=target)
                time.sleep(2)  # 增加等待时间确保 UI 加载完成
                
                # 验证窗口是否打开
                wechat_hwnd = win32gui.FindWindow(None, "微信")
                logger.info(f"save_media: 微信窗口句柄: {wechat_hwnd}")
            except Exception as e:
                logger.warning(f"打开聊天窗口失败: {e}")
                return None
            
            try:
                lists = Lists
                windows = Windows
                desktop = Desktop(backend='uia')
                
                # 获取聊天列表
                dialog_window = None
                try:
                    from pyweixin.WeChatTools import Navigator
                    logger.info(f"save_media: 重新获取聊天窗口: {target}")
                    dialog_window = Navigator.open_dialog_window(friend=target)
                    logger.info(f"save_media: dialog_window: {dialog_window}")
                except Exception as e:
                    logger.warning(f"获取 dialog_window 失败: {e}")
                
                if not dialog_window:
                    logger.warning("save_media: 无法获取聊天窗口")
                    return None
                
                chat_list = dialog_window.child_window(**lists.FriendChatList)
                
                # 找到图片项和视频项
                photo_items = chat_list.children(class_name='mmui::ChatBubbleReferItemView', title='图片')
                video_items = chat_list.children(class_name='mmui::ChatBubbleReferItemView', title='视频')
                
                # 如果没找到视频，尝试通过 text 包含"视频"来查找
                if not video_items:
                    for child in chat_list.children():
                        try:
                            text = child.window_text()
                            if '视频' in text and 'ChatBubbleReferItemView' in child.class_name():
                                video_items.append(child)
                        except:
                            pass
                
                media_items = photo_items + video_items
                
                if not media_items:
                    logger.warning("save_media: 未找到图片或视频项")
                    return None
                
                # 显示所有媒体项
                logger.info(f"save_media: 找到 {len(media_items)} 个媒体项(图片:{len(photo_items)}, 视频:{len(video_items)})")
                for i, item in enumerate(media_items):
                    logger.info(f"  媒体 {i}: {item.rectangle()}")
                
                # 点击最后一个媒体项（最新）- 双击打开预览窗口
                logger.info("save_media: 点击媒体项...")
                item = media_items[-1]
                rect = item.rectangle()
                # 双击位置：对方发送的图片在左侧，使用相对偏移
                # X = 控件.left + 88（图片内容实际位置）
                # Y = 控件.top + 10
                click_x = rect.left + 88
                click_y = rect.top + 10
                logger.info(f"save_media: 双击位置: ({click_x}, {click_y})")
                
                from pywinauto.mouse import double_click
                double_click(coords=(click_x, click_y))
                time.sleep(3)  # 等待更长时间让预览窗口打开
                
                # 列出所有顶级窗口
                logger.info("save_media: 列出所有顶级窗口...")
                top_windows = desktop.windows()
                for w in top_windows:
                    try:
                        cls = w.class_name()
                        title = w.window_text()
                        if title:
                            logger.info(f"  窗口: class={cls}, title={title[:50]}")
                    except:
                        pass
                
                # 查找预览窗口
                logger.info("save_media: 查找预览窗口...")
                image_preview = desktop.window(**windows.ImagePreviewWindow)
                
                logger.info(f"save_media: 预览窗口 exists={image_preview.exists()}")
                
                if not image_preview.exists():
                    # 如果是视频，尝试重新点击并等待
                    is_video = video_items and item == video_items[-1] if video_items else False
                    if is_video:
                        logger.info("save_media: 视频未打开预览窗口，尝试重新点击...")
                        double_click(coords=(click_x, click_y))
                        time.sleep(3)
                        # 重新查找预览窗口
                        image_preview = desktop.window(**windows.ImagePreviewWindow)
                        if not image_preview.exists():
                            for w in top_windows:
                                try:
                                    cls = w.class_name()
                                    title = w.window_text()
                                    if 'Preview' in cls or '预览' in title:
                                        logger.info(f"  可能预览窗口: class={cls}, title={title}")
                                except:
                                    pass
                            logger.warning("save_media: 视频预览窗口未找到")
                            return None
                    else:
                        # 尝试其他方式查找
                        logger.info("save_media: 尝试其他方式查找预览窗口...")
                        for w in top_windows:
                            try:
                                cls = w.class_name()
                                title = w.window_text()
                                if 'Preview' in cls or '预览' in title:
                                    logger.info(f"  可能预览窗口: class={cls}, title={title}")
                            except:
                                pass
                        logger.warning("save_media: 未找到预览窗口")
                        return None
                
                logger.info("save_media: 找到预览窗口")
                image_preview.restore()
                time.sleep(0.5)
                
                # 查找保存按钮 - 尝试多种方式
                save_button = None
                
                # 方法1: 通过文本查找
                for d in image_preview.descendants():
                    try:
                        text = d.window_text()
                        ctrl_type = d._control_types[0] if d._control_types else ""
                        if '保存' in text:
                            save_button = d
                            logger.info(f"save_media: 找到保存按钮(文本): {text}, ctrl_type={ctrl_type}")
                            break
                    except:
                        pass
                
                # 方法2: 如果没找到，尝试查找所有按钮
                if not save_button:
                    logger.warning("save_media: 未找到保存按钮，列出所有按钮...")
                    for d in image_preview.descendants():
                        try:
                            ctrl_type = d._control_types[0] if d._control_types else ""
                            text = d.window_text()
                            if ctrl_type == 'Button' and text:
                                logger.info(f"  按钮: {text}")
                        except:
                            pass
                
                if not save_button:
                    logger.warning("save_media: 未找到保存按钮")
                    return None
                
                # 点击保存按钮
                logger.info("save_media: 点击保存按钮...")
                save_button.click_input()
                time.sleep(1.5)
                
                # 等待保存对话框出现
                logger.info("save_media: 等待保存对话框...")
                time.sleep(1)
                
                # 处理保存对话框 - 需要输入路径后按两次回车
                import win32gui
                import win32con
                
                # 查找保存对话框
                save_dialog = None
                for _ in range(10):
                    hwnd = win32gui.GetForegroundWindow()
                    cls = win32gui.GetClassName(hwnd)
                    title = win32gui.GetWindowText(hwnd)
                    logger.info(f"save_media: 当前窗口: {hwnd}, class={cls}, title={title}")
                    
                    # 标准的保存对话框 或 Qt 的保存对话框
                    if cls == '#32770' or 'Q' in cls:
                        logger.info(f"save_media: 找到保存对话框: {title}")
                        save_dialog = hwnd
                        break
                    
                    time.sleep(0.5)
                
                if save_dialog and target_folder:
                    # 获取保存对话框中的文件名
                    logger.info("save_media: 获取原始文件名...")
                    
                    from pywinauto import Application
                    from pywinauto.keyboard import send_keys
                    import win32gui
                    import win32con
                    import win32clipboard
                    
                    save_app = Application(backend='uia')
                    save_app.connect(handle=save_dialog)
                    save_dialog_app = save_app.window(handle=save_dialog)
                    
                    # 方法1: 尝试通过 ComboBox 0 获取
                    combo_boxes = save_dialog_app.descendants(control_type='ComboBox')
                    logger.info(f"save_media: 找到 {len(combo_boxes)} 个 ComboBox")
                    
                    original_filename = ""
                    
                    if len(combo_boxes) >= 1:
                        cb = combo_boxes[0]
                        logger.info(f"save_media: ComboBox 0: {cb.window_text()}")
                        
                        # 点击 ComboBox 获取焦点
                        cb.click_input()
                        time.sleep(0.3)
                        
                        # 用 Ctrl+A 全选，然后 Ctrl+X 剪切
                        send_keys('^a')
                        time.sleep(0.2)
                        send_keys('^x')
                        time.sleep(0.3)
                        
                        # 获取剪贴板内容（被剪切的原始文件名）
                        win32clipboard.OpenClipboard()
                        clipboard_text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                        win32clipboard.CloseClipboard()
                        logger.info(f"save_media: 剪贴板内容: {clipboard_text}")
                        
                        if clipboard_text and ('微信图片' in clipboard_text or '微信视频' in clipboard_text):
                            original_filename = clipboard_text
                    
                    logger.info(f"save_media: 原始文件名: {original_filename}")
                    
                    if not original_filename:
                        logger.warning("save_media: 无法获取文件名")
                        return None
                    
                    # 构建完整路径
                    full_path = target_folder.replace('/', '\\')
                    if not full_path.endswith('\\'):
                        full_path += '\\'
                    full_path += original_filename
                    
                    logger.info(f"save_media: 完整路径: {full_path}")
                    
                    # 使用剪贴板粘贴完整路径
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardText(full_path)
                    win32clipboard.CloseClipboard()
                    
                    send_keys('^v')
                    time.sleep(1)
                    
                    logger.info("save_media: 按回车保存...")
                    send_keys('{ENTER}')
                    time.sleep(2)
                    
                    # 直接返回保存的完整路径
                    if os.path.exists(full_path):
                        logger.info(f"媒体已保存到: {full_path}")
                        # 关闭预览窗口
                        try:
                            image_preview.close()
                            logger.info("save_media: 已关闭预览窗口")
                        except:
                            pass
                        return full_path
                
                # 检查目标文件夹中是否有刚保存的文件（按文件名匹配）
                if target_folder and os.path.exists(target_folder) and original_filename:
                    expected_file = os.path.join(target_folder, original_filename)
                    if os.path.exists(expected_file):
                        logger.info(f"媒体已保存到: {expected_file}")
                        # 关闭预览窗口
                        try:
                            image_preview.close()
                            logger.info("save_media: 已关闭预览窗口")
                        except:
                            pass
                        return expected_file
                
                # 如果上面没找到，回退到查找最新文件
                if target_folder and os.path.exists(target_folder):
                    files_in_target = os.listdir(target_folder)
                    if files_in_target:
                        files_with_time = [(f, os.path.getmtime(os.path.join(target_folder, f))) for f in files_in_target 
                                           if (f.startswith('微信图片_') and f.endswith(('.jpg', '.png', '.jpeg'))) 
                                           or (f.startswith('微信视频') and f.endswith('.mp4'))]
                        if files_with_time:
                            files_with_time.sort(key=lambda x: x[1], reverse=True)
                            latest = files_with_time[0][0]
                            dest_path = os.path.join(target_folder, latest)
                            logger.info(f"媒体已保存到: {dest_path}")
                            # 关闭预览窗口
                            try:
                                image_preview.close()
                                logger.info("save_media: 已关闭预览窗口")
                            except:
                                pass
                            return dest_path
                
                # 如果目标文件夹没有新文件，尝试从图片目录查找
                pictures_dir = os.path.join(os.path.expanduser('~'), 'Pictures')
                if os.path.exists(pictures_dir):
                    files = [f for f in os.listdir(pictures_dir) 
                             if (f.startswith('微信图片_') and f.endswith(('.jpg', '.png', '.jpeg'))) 
                             or (f.startswith('微信视频') and f.endswith('.mp4'))]
                    if files:
                        files_with_time = [(f, os.path.getmtime(os.path.join(pictures_dir, f))) for f in files]
                        files_with_time.sort(key=lambda x: x[1], reverse=True)
                        
                        logger.info(f"save_media: 找到 {len(files)} 个媒体文件，最新: {files_with_time[0][0]}")
                        
                        if target_folder:
                            os.makedirs(target_folder, exist_ok=True)
                            latest = files_with_time[0][0]
                            src_path = os.path.join(pictures_dir, latest)
                            dest_path = os.path.join(target_folder, latest)
                            shutil.copy2(src_path, dest_path)
                            logger.info(f"媒体已保存到: {dest_path}")
                            # 关闭预览窗口
                            try:
                                image_preview.close()
                                logger.info("save_media: 已关闭预览窗口")
                            except:
                                pass
                            return dest_path
                        else:
                            result_path = os.path.join(pictures_dir, files_with_time[0][0])
                            # 关闭预览窗口
                            try:
                                image_preview.close()
                                logger.info("save_media: 已关闭预览窗口")
                            except:
                                pass
                            return result_path
                
                logger.warning("save_media: 未找到保存的文件")
                return None
                
            except Exception as e:
                logger.error(f"save_media 失败: {e}")
                return None

    @property
    def A_MyIcon(self):
        return "default_icon"


def get_wechat_adapter() -> PyWeChatAdapter:
    """获取微信适配器实例"""
    return PyWeChatAdapter()