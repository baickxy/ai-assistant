# AI助手桌面应用

一个功能强大的离线AI助手桌面应用，支持3D模型显示、语音交互和本地LLM。

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ 功能特点

- 🎨 **3D模型显示** - 支持FBX格式模型，透明背景，可拖动
- 🎙️ **语音交互** - 语音唤醒、语音识别、语音合成
- 🤖 **本地LLM** - 集成Ollama，支持多种开源模型
- 🖥️ **桌面宠物模式** - 无边框窗口，始终置顶
- ⚙️ **高度可配置** - 模型、语音、AI参数均可自定义
- 🔧 **模块化设计** - 功能分离，易于扩展

## 📋 系统要求

- **操作系统**: Windows 10/11, macOS 10.15+, Linux
- **Python**: 3.10 或更高版本
- **内存**: 建议8GB以上
- **显卡**: 支持OpenGL 3.3+
- **麦克风**: 用于语音输入
- **扬声器**: 用于语音输出

## 🚀 快速开始

### 1. 安装Ollama

首先安装Ollama并下载模型：

```bash
# 访问 https://ollama.com 下载安装程序

# 安装完成后，下载模型
ollama pull llama3.2
```

### 2. 安装AI助手

```bash
# 克隆或下载本项目
cd ai-assistant

# 运行安装脚本
python install.py
```

### 3. 启动应用

**Windows:**
```bash
双击 start.bat
# 或
python main.py
```

**macOS/Linux:**
```bash
./start.sh
# 或
python3 main.py
```

## 📁 项目结构

```
ai-assistant/
├── main.py                 # 程序入口
├── config.py               # 配置管理
├── config.json             # 用户配置文件
├── requirements.txt        # Python依赖
├── install.py              # 安装脚本
├── start.bat               # Windows启动脚本
├── start.sh                # Linux/macOS启动脚本
├── design.md               # 设计文档
├── README.md               # 本文件
│
├── modules/                # 核心功能模块
│   ├── window.py           # 主窗口管理
│   ├── renderer.py         # OpenGL 3D渲染
│   ├── fbx_loader.py       # FBX模型加载
│   ├── animator.py         # 动画控制器
│   ├── voice_recognizer.py # 语音识别
│   ├── voice_synthesizer.py# 语音合成
│   ├── wake_word.py        # 唤醒词检测
│   ├── llm_client.py       # Ollama客户端
│   ├── chat_panel.py       # 对话面板
│   ├── settings_panel.py   # 设置面板
│   └── tray_icon.py        # 系统托盘
│
├── utils/                  # 工具模块
│   ├── thread_pool.py      # 线程池管理
│   └── helpers.py          # 辅助函数
│
├── assets/                 # 资源文件
│   ├── models/             # FBX模型文件
│   ├── voices/             # 语音样本
│   └── icons/              # 图标资源
│
└── logs/                   # 日志文件
```

## 🎮 使用指南

### 基本操作

| 操作 | 说明 |
|------|------|
| 双击3D模型 | 打开/关闭对话面板 |
| 拖动3D模型 | 移动窗口位置 |
| 右键3D模型 | 显示设置菜单 |
| 语音唤醒 | 说出唤醒词 (默认: "小助手") |

### 语音命令

- **"小助手"** - 唤醒AI助手
- **"打开设置"** - 打开设置面板
- **"清除历史"** - 清除对话历史
- **"退出"** - 关闭应用

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl + ,` | 打开设置 |
| `Ctrl + H` | 显示/隐藏窗口 |
| `Ctrl + Q` | 退出应用 |
| `Esc` | 关闭面板 |

## ⚙️ 配置说明

配置文件位于 `config.json`，可自定义以下选项：

### 窗口设置
```json
{
  "window": {
    "width": 400,
    "height": 600,
    "pos_x": 1400,
    "pos_y": 400,
    "opacity": 0.95,
    "always_on_top": true
  }
}
```

### 模型设置
```json
{
  "model": {
    "current": "default.fbx",
    "scale": 1.0,
    "animation_speed": 1.0
  }
}
```

### 语音设置
```json
{
  "voice": {
    "recognition_lang": "zh-CN",
    "synthesis_voice": "zh-CN-XiaoxiaoNeural",
    "synthesis_rate": 150,
    "synthesis_volume": 0.8
  }
}
```

### Ollama设置
```json
{
  "ollama": {
    "host": "http://localhost:11434",
    "model": "llama3.2",
    "temperature": 0.7,
    "max_tokens": 2048
  }
}
```

## 🎨 自定义3D模型

1. 准备FBX格式的3D模型文件
2. 将模型文件放入 `assets/models/` 目录
3. 在设置面板中选择该模型

### 模型要求

- 格式: FBX (Binary或ASCII)
- 大小: 建议不超过10MB
- 多边形数: 建议不超过10000面
- 动画: 支持骨骼动画

## 🎙️ 语音配置

### 语音识别

默认使用Google语音识别 (需要网络连接)。

如需离线识别，可安装Vosk：
```bash
pip install vosk
```

### 语音合成

支持多种语音引擎：

1. **pyttsx3** (离线，默认)
2. **Edge TTS** (在线，质量更好)

启用Edge TTS：
```bash
pip install edge-tts
```

然后在设置中选择Edge TTS语音。

## 🔧 故障排除

### 应用无法启动

1. 检查Python版本: `python --version`
2. 检查依赖安装: `pip list | grep PyQt6`
3. 查看日志文件: `logs/ai-assistant.log`

### Ollama连接失败

1. 检查Ollama是否运行: `ollama list`
2. 检查服务地址配置
3. 防火墙设置

### 语音识别不工作

1. 检查麦克风权限
2. 检查PyAudio安装
3. 校准麦克风 (在设置中)

### 3D模型不显示

1. 检查OpenGL支持
2. 更新显卡驱动
3. 尝试简化模型

## 📝 更新日志

### v1.0.0 (2024-01-01)

- ✨ 初始版本发布
- 🎨 3D模型显示支持
- 🎙️ 语音交互功能
- 🤖 Ollama LLM集成
- ⚙️ 完整的设置面板

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本项目
2. 创建功能分支: `git checkout -b feature/xxx`
3. 提交更改: `git commit -am 'Add xxx'`
4. 推送分支: `git push origin feature/xxx`
5. 创建Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI框架
- [Ollama](https://ollama.com) - 本地LLM运行环境
- [OpenGL](https://www.opengl.org/) - 3D图形渲染
- [Porcupine](https://picovoice.ai/platform/porcupine/) - 唤醒词检测

## 📧 联系方式

如有问题或建议，欢迎通过以下方式联系：

- 提交 [GitHub Issue](https://github.com/yourusername/ai-assistant/issues)
- 发送邮件至: your.email@example.com

---

**Made with ❤️ by AI Assistant**
