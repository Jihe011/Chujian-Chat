"""
微信适配器 - 基于 pywechat/pyweixin
支持通过截图检测发送人
支持图片、视频、语音转文字
"""

import time
import logging
import os
import shutil
import re
import json
from typing import List, Optional, Dict, Any
from PIL import Image
import numpy as np
import psutil
from datetime import datetime

logger = logging.getLogger(__name__)


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


def detect_sender_by_color(img: Image.Image, rect_left: int, rect_top: int, rect_right: int, rect_bottom: int) -> str:
    """通过颜色检测发送人"""
    if rect_right <= rect_left or rect_bottom <= rect_top:
        return "?"
    
    msg_img = img.crop((rect_left, rect_top, rect_right, rect_bottom))
    arr = np.array(msg_img)
    
    h, w = arr.shape[:2]
    if h < 10 or w < 10:
        return "?"
    
    center = arr[h//4:3*h//4, w//4:3*w//4]
    avg = center.mean(axis=(0,1))
    r, g, b = avg[0], avg[1], avg[2]
    
    is_green = g > r + 5 and g > b + 5
    is_white = r > 244 and g > 244 and b > 244
    
    if is_green:
        return "self"
    elif is_white:
        return "friend"
    else:
        edge_top = arr[:5, :].mean(axis=(0,1))
        edge_bottom = arr[-5:, :].mean(axis=(0,1))
        edge_avg = (edge_top + edge_bottom) / 2
        er, eg, eb = edge_avg[0], edge_avg[1], edge_avg[2]
        
        if eg > er + 5 and eg > eb + 5:
            return "self"
        elif er > 244 and eg > 244 and eb > 244:
            return "friend"
    
    return "?"


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
        from pyweixin.WeChatTools import Navigator
        from pyweixin.WeChatAuto import Monitor, Messages, Files, Contacts
        from pyweixin.WeChatTools import Tools
        
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
        self._last_runtime_id = {}  # 记录每个聊天的最后 runtime_id
        
        self._runtime_ids_file = self._get_runtime_ids_file()
        self.load_runtime_ids()
        
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
        """从文件加载 runtime_ids"""
        filepath = self._runtime_ids_file
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    self._last_runtime_id = json.load(f)
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
        try:
            wxid = self.Tools.get_current_wxid()
            if wxid:
                return wxid
            return "初见"
        except Exception as e:
            logger.error(f"获取机器人名称失败: {e}")
            return "初见"
    
    def send_message(self, msg: str, who: str = None) -> bool:
        try:
            target = who or self._current_chat
            if not target:
                return False
            self.Messages.send_messages_to_friend(friend=target, messages=[msg], close_weixin=False)
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False
    
    def send_file(self, filepath: str, who: str = None) -> bool:
        try:
            target = who or self._current_chat
            if not target:
                return False
            self.Files.send_files_to_friend(friend=target, files=[filepath], close_weixin=False)
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
        try:
            self._ensure_main_window()
            self.Navigator.open_dialog_window(friend=name)
            self._current_chat = name
        except Exception as e:
            logger.error(f"打开聊天窗口失败: {e}")
    
    def chat_with(self, name: str) -> bool:
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
        try:
            self._ensure_main_window()
            return self.Messages.dump_sessions() or []
        except Exception as e:
            logger.error(f"获取会话列表失败: {e}")
            return []
    
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
    
    def get_new_messages(self, who: str = None, max_new_minutes: int = 60) -> list:
        """
        获取新消息（使用 runtime_id 检测）
        """
        target = who or self._current_chat
        if not target:
            return []
        
        all_messages = self.get_all_messages(target, update_runtime_id=False)
        
        if not all_messages:
            return []
        
        chat_key = target
        last_runtime_id = self._last_runtime_id.get(chat_key, '')
        
        if not last_runtime_id:
            self._last_runtime_id[chat_key] = all_messages[-1].get('runtime_id', '')
            logger.info(f"第一次获取消息，记录 runtime_id")
            return []
        
        new_messages = []
        current_time_msg = None
        
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        last_index = -1
        for i, msg in enumerate(all_messages):
            if msg.get('runtime_id') == last_runtime_id:
                last_index = i
                break
        
        if last_index == -1:
            # 没有找到匹配的消息，可能是新消息
            last_index = -1
        
        new_items = all_messages[last_index+1:]
        
        for msg in new_items:
            content = msg.get('content', '')
            msg_type = msg.get('type', 'text')
            
            if msg_type == 'time':
                current_time_msg = content
                continue
            
            is_new = True
            if current_time_msg:
                tm = re.match(r'^(\d{2}):(\d{2})$', current_time_msg)
                if tm:
                    h = int(tm.group(1))
                    mi = int(tm.group(2))
                    diff = (current_hour * 60 + current_minute) - (h * 60 + mi)
                    if diff > max_new_minutes:
                        is_new = False
            
            msg['time'] = current_time_msg
            
            if is_new:
                msg['is_new'] = True
                new_messages.append(msg)
        
        self._last_runtime_id[chat_key] = all_messages[-1].get('runtime_id', '')
        self.save_runtime_ids()
        
        return new_messages
    
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
            lists = Lists()
            windows = Windows()
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
            return None
        
        # 查找消息列表
        dlg = app.window(handle=wechat_hwnd)
        dlg.set_focus()
        time.sleep(0.5)
        
        all_desc = dlg.descendants()
        
        # 查找图片/视频消息项
        media_item = None
        for i, item in enumerate(all_desc):
            try:
                class_name = item.class_name()
                text = item.window_text()
                if 'ChatBubbleReferItemView' in class_name and text in ('图片', '视频'):
                    logger.info(f"save_media: 找到媒体消息: {text}")
                    media_item = item
                    break
            except:
                pass
        
        if not media_item:
            logger.warning("save_media: 未找到图片/视频消息项")
            return None
        
        # 双击打开预览
        logger.info("save_media: 双击打开预览...")
        media_item.double_click_input()
        time.sleep(2)
        
        # 用 win32gui 查找预览窗口（类名 Qt51514QWindowIcon，标题 "图片和视频"）
        preview_hwnd = None
        
        def find_preview(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                try:
                    title = win32gui.GetWindowText(hwnd)
                    cls = win32gui.GetClassName(hwnd)
                    logger.info(f"检查窗口: {hwnd} [{cls}] {title}")
                    if '图片' in title or '视频' in title:
                        preview_hwnd = hwnd
                        return False
                except:
                    pass
            return True
        
        win32gui.EnumWindows(find_preview, None)
        
        if not preview_hwnd:
            logger.warning("save_media: 未找到预览窗口")
            return None
        
        logger.info(f"save_media: 找到预览窗口: {preview_hwnd}")
        
        # 连接预览窗口
        preview_app = Application(backend='uia')
        try:
            preview_app.connect(handle=preview_hwnd)
        except Exception as e:
            logger.warning(f"连接预览窗口失败: {e}")
            return None
        
        preview = preview_app.window(handle=preview_hwnd)
        preview.set_focus()
        time.sleep(0.3)
        
        # 找保存按钮
        save_button = None
        for d in preview.descendants():
            try:
                text = d.window_text()
                if '保存' in text:
                    save_button = d
                    logger.info(f"save_media: 找到保存按钮: {text}")
                    break
            except:
                pass
        
        if not save_button:
            logger.warning("save_media: 未找到保存按钮")
            return None
        
        # 点击保存
        save_button.click_input()
        time.sleep(1)
        
        # 处理保存对话框
        hwnd = win32gui.GetForegroundWindow()
        cls = win32gui.GetClassName(hwnd)
        if cls == '#32770':
            win32gui.SendMessage(hwnd, win32con.WM_KEYDOWN, 0x0D, 0)
            time.sleep(1)
        
        # 复制文件
        pictures_dir = os.path.join(os.path.expanduser('~'), 'Pictures')
        if os.path.exists(pictures_dir):
            files = [f for f in os.listdir(pictures_dir) if f.startswith('微信图片_') and f.endswith('.jpg')]
            if files:
                files_with_time = [(f, os.path.getmtime(os.path.join(pictures_dir, f))) for f in files]
                files_with_time.sort(key=lambda x: x[1], reverse=True)
                
                if target_folder:
                    os.makedirs(target_folder, exist_ok=True)
                    latest = files_with_time[0][0]
                    src_path = os.path.join(pictures_dir, latest)
                    dest_path = os.path.join(target_folder, latest)
                    shutil.copy2(src_path, dest_path)
                    logger.info(f"图片已保存到: {dest_path}")
                    return dest_path
                else:
                    return os.path.join(pictures_dir, files_with_time[0][0])
        
        logger.warning("save_media: 未找到保存的文件")
        return None

    @property
    def A_MyIcon(self):
        return "default_icon"


def get_wechat_adapter() -> PyWeChatAdapter:
    """获取微信适配器实例"""
    return PyWeChatAdapter()