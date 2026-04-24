#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

print("====================================")
print("         C H U J I A N")
print("====================================")
print()
print("==============================")
print("I       初见 - AI 助手        I")
print("==============================")
print()

print("[步骤] 正在检查 Python 环境...")
result = os.system("python --version >nul 2>&1")
if result != 0:
    print("[错误] 未找到 Python，请先安装 Python!")
    input("\n按任意键退出...")
    sys.exit(1)
print("[完成] Python 已就绪")

print("[步骤] 正在检查 pywechat...")
if not os.path.exists("pywechat-git"):
    print("[步骤] 正在克隆 pywechat...")
    result = os.system("git clone https://gh-proxy.org/https://github.com/Hello-Mr-Crab/pywechat.git pywechat-git")
    if result != 0:
        print("[错误] 克隆 pywechat 失败")
        input("\n按任意键退出...")
        sys.exit(1)
    print("[完成] pywechat 已克隆")
else:
    print("[完成] pywechat 已存在")

venv_dir = ".venv"
venv_pip = os.path.join(venv_dir, "Scripts", "pip.exe")
venv_python = os.path.join(venv_dir, "Scripts", "python.exe")

current_dir = os.getcwd()

if not os.path.exists(venv_dir):
    print("[步骤] 正在创建虚拟环境...")
    result = os.system(f'cd /d "{current_dir}" && python -m venv {venv_dir}')
    if result != 0:
        print("[错误] 创建虚拟环境失败")
        input("\n按任意键退出...")
        sys.exit(1)
    print("[完成] 虚拟环境已创建")
elif not os.path.exists(venv_pip):
    print("[警告] 虚拟环境损坏正在重建...")
    os.system(f'rmdir /s /q "{current_dir}\\{venv_dir}" >nul 2>&1')
    result = os.system(f'cd /d "{current_dir}" && python -m venv {venv_dir}')
    if result != 0:
        print("[错误] 创建虚拟环境失败")
        input("\n按任意键退出...")
        sys.exit(1)
    print("[完成] 虚拟环境已重建")

if not os.path.exists(venv_pip):
    print("[错误] 虚拟环境未正确创建")
    input("\n按任意键退出...")
    sys.exit(1)

print("[步骤] 正在安装 pywechat...")
result = os.system(f'cd /d "{current_dir}" && "{venv_pip}" install ./pywechat-git')
if result != 0:
    print("[错误] 安装 pywechat 失败")
    input("\n按任意键退出...")
    sys.exit(1)
print("[完成] pywechat 已安装")

print("[步骤] 正在安装依赖...")
mirrors = [
    ("阿里源", "https://mirrors.aliyun.com/pypi/simple/"),
    ("清华源", "https://pypi.tuna.tsinghua.edu.cn/simple"),
    ("腾讯源", "https://mirrors.cloud.tencent.com/pypi/simple"),
]
success = False
for name, url in mirrors:
    print(f"[步骤] 使用 {name} 安装依赖...")
    result = os.system(f'cd /d "{current_dir}" && "{venv_pip}" install -r requirements.txt -i {url}')
    if result == 0:
        print(f"[完成] {name} 安装成功!")
        success = True
        break
    else:
        print(f"[失败] {name} 安装失败，尝试下一个源...")

if not success:
    print("[错误] 所有源安装失败")
    input("\n按任意键退出...")
    sys.exit(1)

if not os.path.exists("run_config_web.py"):
    print("[错误] 入口文件 run_config_web.py 不存在")
    input("\n按任意键退出...")
    sys.exit(1)

print()
print("==============================")
print("请确保微信已登录")
print("并在前台运行!")
print("==============================")
print()

print("[步骤] 正在启动初见 AI...")
print()
print("========================================")
print("按 Ctrl+C 停止程序")
print("========================================")
os.system(f'cd /d "{current_dir}" && "{venv_python}" run_config_web.py')

print("[完成] 程序已退出")
input("\n按回车键退出...")