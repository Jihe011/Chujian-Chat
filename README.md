# 初见 (Chujian Chat)

> 每一次对话，都像初次见面。

基于 [KouriChat](https://github.com/KouriChat/KouriChat) 改写的微信对话机器人，保留核心功能并简化配置。

## 特性

### 🤖 AI 对话
- 基于 DeepSeek AI 大模型的智能对话
- 支持多模型切换
- 可配置的温度、token 数等参数

### 👤 个性化人设
- 可自定义 AI 角色设定（avatar）
- 支持多种人设切换
- 记忆功能，记住对话上下文

### 💬 微信集成
- 自动监听和回复微信消息
- 支持私聊和群聊
- 多用户同时对话

### 🎨 个性化设置
- 自定义图标头像
- 自定义背景图片
- 渐变 UI 界面

### 🌐 高级功能
- 网络搜索
- 图像识别
- 视频理解
- 语音合成（TTS）
- 定时任务
- 版本更新检测

### 📊 Web 管理界面
- 仪表盘实时显示状态
- 配置管理（Web界面）
- 人设管理
- 日志查看

## 环境要求

- Windows 10/11
- Python 3.10+
- 微信 PC 版（4.1.8）

## 快速开始

### 1. 解压与运行

```bash
# 解压压缩包
unzip Chujian-Chat-v1.0.0.zip

# 进入目录
cd Chujian-Chat

# 双击运行 run.bat
```

### 2. 手动启动

```bash
# 克隆 pywechat（如 run.bat 未自动完成）
git clone https://github.com/Hello-Mr-Crab/pywechat.git pywechat-git

# 复制配置模板
copy data\config\config.json.template data\config\config.json

# 编辑 config.json，填入你的 API Key

# 安装依赖
pip install -r requirements.txt

# 运行
python run_config_web.py
```

### 3. 访问

打开浏览器访问：http://localhost:8502

## 配置说明

### config.json

主要配置项：

```json
{
    "llm_settings": {
        "api_key": "your-api-key-here",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat"
    },
    "user_settings": {
        "listen_list": ["微信昵称1", "微信昵称2"]
    }
}
```

## 目录结构

```
Chujian-Chat/
├── run_config_web.py    # 主程序
├── run.bat              # 启动脚本
├── requirements.txt     # 依赖
├── data/
│   ├── config/
│   │   └── config.json.template  # 配置模板
│   └── avatars/
│       └── default/   # 人设目录
└── src/
    ├── main.py         # 核心逻辑
    ├── wechat/       # 微信适配器
    ├── handlers/     # 消息处理器
    ├── services/     # AI 服务
    └── webui/        # Web 界面
```

## 功能演示

### 启动界面

```
================================
        C H U J I A N
================================

[Step 1] Clone pywechat...
[OK] pywechat ready

[Step 2] Install dependencies...
[OK] Dependencies ready

[Starting] Launching Chujian...

==================================
  Local:   http://localhost:8502
  Network: http://192.168.1.x:8502
==================================
```

## 技术栈

### 后端
- Python 3.10+
- Flask - Web 框架
- DeepSeek AI - 大语言模型
- SQLAlchemy - 数据库

### 微信自动化
- pywechat - 微信 API 封装
- PyAutoGUI - UI 自动化

### 前端
- Bootstrap 5 - UI 框架
- JavaScript - 交互逻辑

## 常见问题

### 微信无响应？
- 确保微信已登录并在前台运行
- 检查是否有安全软件拦截

### API Key 错误？
- 确保在 config.json 中填入有效的 API Key
- 可从 DeepSeek 官网获取：https://platform.deepseek.com/

## 开源协议

Apache License 2.0

## 致谢

- [KouriChat](https://github.com/KouriChat/KouriChat) - 本项目基于此项目改写
- [DeepSeek](https://deepseek.com/) - AI 大模型
- [pywechat](https://github.com/Hello-Mr-Crab/pywechat) - 微信 API
- [Flask](https://flask.palletsprojects.com/) - Web 框架

---

*每一次对话，都像初次见面。*
