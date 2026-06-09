"""
视频理解服务模块
在主程序启动时自动运行
"""

import threading
import requests
import time

VIDEO_SERVER_PORT = 8848
_server_thread = None
_server_process = None


def start_video_server():
    """启动视频静态文件服务器（后台线程）"""
    global _server_thread, _server_process
    
    # 检查服务器是否已运行
    try:
        response = requests.get(f"http://localhost:{VIDEO_SERVER_PORT}/health", timeout=2)
        if response.status_code == 200:
            print(f"视频服务器已在运行: http://localhost:{VIDEO_SERVER_PORT}")
            return None
    except:
        pass
    
    # 启动服务器（使用子进程）
    import subprocess
    import os
    
    server_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "video_server.py")
    server_path = os.path.normpath(server_path)
    
    try:
        _server_process = subprocess.Popen(
            ["python", server_path, str(VIDEO_SERVER_PORT)],
            creationflags=subprocess.CREATE_NEW_CONSOLE if subprocess.os.name == 'nt' else 0
        )
        print(f"视频静态文件服务已启动: http://localhost:{VIDEO_SERVER_PORT}")
        print(f"公网地址: https://video.geiniyigmmp.dpdns.org/")
        
        # 等待服务器启动
        for i in range(10):
            try:
                response = requests.get(f"http://localhost:{VIDEO_SERVER_PORT}/health", timeout=1)
                if response.status_code == 200:
                    print(f"视频服务器就绪")
                    return _server_process
            except:
                time.sleep(0.5)
        
        print(f"视频服务器启动超时")
        return _server_process
        
    except Exception as e:
        print(f"启动视频服务器失败: {e}")
        return None


def stop_video_server():
    """停止视频静态文件服务器"""
    global _server_process
    
    if _server_process:
        try:
            _server_process.terminate()
            print("视频服务器已停止")
        except:
            pass


def get_video_server_url():
    """获取视频服务器URL"""
    return f"http://localhost:{VIDEO_SERVER_PORT}"


def get_public_url(filename: str) -> str:
    """获取视频的公网URL"""
    return f"https://video.geiniyigmmp.dpdns.org/videos/{filename}"