import logging
import time
import win32gui
import pygame
from pyweixin import WeChatAuto
from uiautomation import ControlFromHandle

logger = logging.getLogger('main')

CALL_WINDOW_CLASSNAME = 'AudioWnd'
CALL_WINDOW_NAME = '微信'
CALL_BUTTON_NAME = '语音聊天'
HANG_UP_BUTTON_NAME = '挂断'
HANG_UP_BUTTON_LABEL = '挂断'
REFUSE_MSG = '对方已拒绝'
CALL_TIME_OUT = 15


def CallforWho(wx, who: str):
    logger.info("尝试发起语音通话")
    try:
        if win32gui.FindWindow('ChatWnd', who):
            try:
                wx.Navigator.open_separate_dialog_window(friend=who)
                time.sleep(0.5)
                voice_call_button = wx.UiaAPI.ButtonControl(Name=CALL_BUTTON_NAME)
                if voice_call_button.Exists(1):
                    voice_call_button.Click()
                    logger.info("已发起通话")
                    time.sleep(0.5)
                    hWnd = win32gui.FindWindow(CALL_WINDOW_CLASSNAME, CALL_WINDOW_NAME)
                    return hWnd, True
                else:
                    logger.error("发起通话时发生错误：找不到通话按钮")
                    return None, False
            except Exception as e:
                logger.error(f"发起通话时发生错误: {e}")
                return None, False
        else:
            wx.Navigator.open_dialog_window(friend=who)
            time.sleep(0.5)
            chat_box = wx.ChatBox
            if not chat_box.Exists(1):
                logger.error("未找到聊天页面")
                return None, False
            voice_call_button = None
            voice_call_button = chat_box.ButtonControl(Name=CALL_BUTTON_NAME)
            if voice_call_button.Exists(1):
                voice_call_button.Click()
                logger.info("已发起通话")
                hWnd = win32gui.FindWindow(CALL_WINDOW_CLASSNAME, CALL_WINDOW_NAME)
                return hWnd, True
            else:
                logger.error("发起通话时发生错误：找不到通话按钮")
                return None, False
    except Exception as e:
        logger.error(f"发起通话时发生错误: {e}")
        return None, False


def CancelCall(hWnd: int) -> bool:
    logger.info("尝试挂断语音通话")
    if not hWnd:
        logger.error("找不到通话句柄")
        return False

    try:
        call_window = ControlFromHandle(hWnd)
    except Exception as e:
        logger.error(f"取得窗口控制时发生错误: {e}")
        return False

    if call_window is None:
        logger.error(f"无法获取通话窗口控制 (句柄: {hWnd})，可能窗口已关闭")
        return False

    try:
        hang_up_button = None
        hang_up_button = call_window.ButtonControl(Name=HANG_UP_BUTTON_NAME)
        if hang_up_button.Exists(1):
            win32gui.ShowWindow(hWnd, 1)
            win32gui.SetWindowPos(hWnd, -1, 0, 0, 0, 0, 3)
            win32gui.SetWindowPos(hWnd, -2, 0, 0, 0, 0, 3)
            call_window.SwitchToThisWindow()
            hang_up_button.Click()
            logger.info("语音通话已挂断")
            return True
        else:
            logger.error("挂断通话时发生错误：找不到挂断按钮")
            return False
    except Exception as e:
        logger.error(f"挂断通话时发生错误: {e}")
        return False


def PlayVoice(audio_file_path: str, device=None) -> bool:
    logger.info(f"尝试播放音频文件: '{audio_file_path}'")
    if device:
        logger.info(f"目标输出设备: '{device}'")
    else:
        logger.info("目标输出设备: 系统��认")

    try:
        pygame.mixer.quit()
        pygame.mixer.init(devicename=device)
        pygame.mixer.music.load(audio_file_path)
        time.sleep(2)
        pygame.mixer.music.play()
        logger.info("开始播放音频...")

        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

        logger.info("音频播放完毕。")
        return True
    except pygame.error as e:
        logger.error(f"Pygame 错误:{e}")
        return False
    except FileNotFoundError:
        logger.error(f"音频文件未找到:'{audio_file_path}'")
        return False
    except Exception as e:
        logger.error(f"发生未知错误:{e}")
        return False
    finally:
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.quit()


def Call(wx, who: str, audio_file_path: str) -> None:
    call_hwnd, success = CallforWho(wx, who)
    if not success:
        logger.error(f"发起通话失败")
        return
    logger.info(f"等待对方接听 (等待{CALL_TIME_OUT}秒)...")

    start_time = time.time()
    call_status = 0
    call_window = None

    try:
        call_window = ControlFromHandle(call_hwnd)
        if call_window is None:
            logger.error(f"无法获取通话窗口控制 (句柄: {call_hwnd})，可能窗口已关闭或句柄无效")
            CancelCall(call_hwnd)
            return

        while time.time() - start_time < CALL_TIME_OUT:
            if not call_window.Exists(0.2, 0.1):
                logger.warning(f"通话窗口 (句柄: {call_hwnd}) 在等待接听时关闭或不再有效 (可能对方已拒接或发生错误)。")
                call_status = 0
                break

            try:
                hang_up_text = call_window.TextControl(Name=HANG_UP_BUTTON_LABEL)
                refuse_msg = call_window.TextControl(Name=REFUSE_MSG)
                if hang_up_text.Exists(0.1, 0.1) and not refuse_msg.Exists(0.1, 0.1):
                    logger.info(f"通话已接通！")
                    call_status = 1
                    break
                elif hang_up_text.Exists(0.1, 0.1) and refuse_msg.Exists(0.1, 0.1):
                    logger.info(f"通话被拒接！")
                    call_status = 2
                    break
                else:
                    continue
            except Exception as e:
                logger.error(f"检查通话状态时发生错误: {e}")
                call_status = 0
                break

        if call_status == 1:
            PlayVoice(audio_file_path=audio_file_path)
            logger.info("语音播放完成，即将挂断...")
            CancelCall(call_hwnd)
        elif call_status == 2:
            pass
        else:
            logger.info(f"在超时时间内，对方未接听通话。")
            CancelCall(call_hwnd)
    except Exception as e:
        logger.error(f"处理通话时发生未知错误: {e}")
        if call_hwnd is not None:
            CancelCall(call_hwnd)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s: %(message)s',
        handlers=[logging.StreamHandler()]
    )
    logger.info("程序启动")
    wx = WeChatAuto()
    who = ""
    if wx and who:
        try:
            Call(wx, who, 'test.mp3')
        except Exception as main_e:
            logger.error(f"主程序执行过程中发生错误: {main_e}", exc_info=True)
    else:
        logger.error("未能初始化 WeChatAuto 对象或未指定通话对象。")
    logger.info("程序结束")