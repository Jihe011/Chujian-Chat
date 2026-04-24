"""
Simple WeChat Adapter - uses open_dialog_window as fallback
"""

import time
import logging
import sys

logger = logging.getLogger(__name__)


class SimpleError(Exception):
    pass


class SimpleWeChatAdapter:
    def __init__(self):
        print("Initializing simple adapter...")
        
        # Import from WeChatTools
        from pyweixin.WeChatTools import Navigator
        from pyweixin.WeChatAuto import Monitor, Messages, Files
        from pyweixin.WeChatTools import Tools
        
        self.Navigator = Navigator
        self.Monitor = Monitor
        self.Messages = Messages
        self.Files = Files
        self.Tools = Tools
        
        self._main_window = None
        self._current_chat = None
        self._dialog_windows = {}
        self._listen_status = {}
        
        # Check which method is available
        self._use_separate = hasattr(Navigator, 'open_separate_dialog_window')
        print(f"Has open_separate_dialog_window: {self._use_separate}")
        
        # List available methods
        methods = [m for m in dir(Navigator) if not m.startswith('_') and 'window' in m.lower()]
        print(f"Window methods: {methods}")
        
        print("Simple adapter initialized")
    
    def _ensure_main_window(self):
        if self._main_window is None:
            print("Opening WeChat...")
            self._main_window = self.Navigator.open_weixin()
            time.sleep(1)
    
    def get_robot_name(self) -> str:
        try:
            wxid = self.Tools.get_current_wxid()
            return wxid if wxid else "初见"
        except Exception as e:
            print(f"Get name error: {e}")
            return "初见"
    
    def add_listen_chat(self, who: str, savepic: bool = True, savevoice: bool = True, savefile: bool = True):
        """Add listener for chat"""
        try:
            self._ensure_main_window()
            
            user = who
            print(f"Opening dialog window for {user}...")
            
            # Try open_separate_dialog_window first
            if self._use_separate:
                try:
                    dialog = self.Navigator.open_separate_dialog_window(
                        friend=user,
                        window_minimize=True,
                        close_weixin=False
                    )
                except AttributeError:
                    # Fall back
                    print("open_separate failed, trying open_dialog_window...")
                    dialog = self.Navigator.open_dialog_window(
                        friend=user,
                        is_maximize=True
                    )
            else:
                # Use regular dialog window
                dialog = self.Navigator.open_dialog_window(
                    friend=user,
                    is_maximize=True
                )
            
            self._dialog_windows[who] = {
                'window': dialog,
                'savepic': savepic,
                'savefile': savefile
            }
            self._listen_status[who] = 0
            
            print(f"Listener added for: {who}")
            self._current_chat = who
            
        except Exception as e:
            print(f"Add listener error: {e}")
            logger.error(f"添加监听失败: {e}")
    
    def get_listen_message(self, timeout: int = 60) -> dict:
        """Get messages from listeners"""
        results = {}
        
        for who, config in self._dialog_windows.items():
            dialog_window = config.get('window')
            if not dialog_window:
                continue
            
            try:
                print(f"Listening on {who} for 30s...")
                
                result = self.Monitor.listen_on_chat(
                    dialog_window=dialog_window,
                    duration='30s',
                    save_file=config.get('savepic', False),
                    save_photo=config.get('savepic', False),
                    close_dialog_window=False
                )
                
                text_count = result.get('文本数量', 0)
                print(f"Got {text_count} messages from {who}")
                
                if text_count > 0:
                    all_texts = result.get('文本内容', [])
                    if all_texts:
                        results[who] = all_texts
                        print(f"Messages: {all_texts}")
                        
            except Exception as e:
                print(f"Listen error for {who}: {e}")
                logger.debug(f"监听 {who} 消息: {e}")
        
        return results
    
    def send_message(self, msg: str, who: str = None) -> bool:
        try:
            target = who or self._current_chat
            if not target:
                return False
            
            self.Messages.send_messages_to_friend(friend=target, messages=[msg])
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False
    
    def get_session_list(self) -> list:
        try:
            self._ensure_main_window()
            return self.Messages.dump_sessions() or []
        except Exception as e:
            print(f"Session list error: {e}")
            return []


def get_wechat_adapter() -> SimpleWeChatAdapter:
    return SimpleWeChatAdapter()