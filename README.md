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
# AI助手桌面应用

一个轻量化的本地桌面AI助手，支持语音交互、本地LLM以及可定制的视觉展示。

> 注意：最近的改动中我们已临时放弃复杂的 FBX 渲染管线，改为支持直接在窗口中渲染图片（更稳定、跨平台、易于调试）。项目仍保留3D渲染路径，可在后续恢复。

---

## 主要变化（重要）

- 将 `modules/renderer.py` 增加了图片渲染模式：通过 `renderer.load_image(Path)` 加载图片后，优先使用 `QPainter` 绘制图片到窗口，快速可见且无需 FBX 依赖。
- 修复并强化了窗口与 OpenGL 初始化（`modules/window.py`、`main.py` 中增加了对 primaryScreen() 返回 None 情形的兜底）。
- 保留并改进了 OpenGL 调试路径（着色器日志、固定管线回退、覆盖调试三角），便于调试显卡/驱动问题。

---

## 环境与依赖

- Python 3.10+
- 在虚拟环境中安装依赖（推荐）：

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

requirements.txt 中常见依赖（示例）：PyQt6、PyOpenGL、numpy、pillow（用于图片，QImage 也可用）等。

如果需要 FBX 功能，请额外安装 `pyassimp`（可选且在某些平台上难以编译）。

---

## 快速运行（Windows / PowerShell）

1. 从项目根目录启动（非常重要：在项目根目录运行 `python main.py`，确保模块路径和配置生效）：

```powershell
python main.py
```

2. 或者使用提供的启动脚本：双击 `start.bat` 或在 PowerShell 中运行：

```powershell
.\start.bat
```

注意：请始终从项目根目录运行脚本，避免直接对 `modules/*.py` 单独运行（会导致相对导入错误）。

---

## 图片渲染：如何快速验证（推荐）

这个改动的目标是让你能最快看到视觉输出而不依赖 FBX。方法：

1. 选择一张图片放到 `assets/icons/`，例如 `assets/icons/avatar.png`。
2. 在程序运行后，通过 Python 交互或在代码里调用：

```python
from pathlib import Path
# 假设 app 是 AIAssistantApp 实例并已初始化
app.main_window.renderer.load_image(Path('assets/icons/avatar.png'))
```

或者在应用中增加设置项由 UI 调用（我可以帮你把这个功能加入设置面板）。图片会按窗口大小拉伸显示，便于快速确认渲染管线工作正常。

---

## API 与开发者说明

- `modules/renderer.py`：主要类 `OpenGLRenderer`。
  - 新增方法：`load_image(self, image_path: Path) -> bool` —— 加载图片并切换到图片渲染模式。
  - 如果 `self.image` 不为 None，`paintGL` 将使用 `QPainter` 绘制图片并直接返回（优先级高于 3D 渲染）。

- `modules/window.py`：主窗口管理，已调整透明度与主屏幕获取的鲁棒性。

- `main.py`：应用启动入口；请从项目根目录运行，确保 `config` 正确加载。

---

## 调试与常见问题

- ImportError: attempted relative import with no known parent package
  - 原因：直接运行模块文件（如 `python modules/window.py`）会导致包上下文缺失，进而使相对导入失败。
  - 解决：请从项目根目录运行 `python main.py`，或使用 `python -m` 按包方式运行（若你把项目改为可安装包）。

- 窗口全透明或看不到内容
  - 检查 `config.window.opacity`（默认 0.95）。在高透明度情况下，某些平台窗口组合可能看起来“不可见”。`modules/window.py` 已做阈值处理，仅在 opacity < 0.5 时启用 `WA_TranslucentBackground`。

- OpenGL 相关问题
  - 程序会在日志中输出 GL Vendor/Renderer/Version/GLSL 信息（查看 `logs/ai-assistant.log`）。确保显卡驱动支持 OpenGL 3.3+
  - 如果着色器失败，会在日志中记录编译或链接错误，并回退到固定管线绘制（兼容模式）。

---

## 恢复 FBX / 3D 路径

如果你希望恢复 FBX 渲染流程（更完整的 3D avatar），后续工作包括：

1. 安装并确认 `pyassimp` 可用，或替换为更可靠的 FBX 解析器。
2. 校验模型的坐标系、缩放与相机设置（当前调试显示模型可能被相机裁剪或缩放过小）。
3. 将临时调试着色器恢复到正式光照/纹理着色器并移除覆盖红三角形。

我可以在你确认要继续 3D 路线时帮助完成这些步骤。

---

## 开发与贡献

欢迎 PR、Issue 和建议。常见工作流程：

```bash
git checkout -b feature/your-feature
# 修改代码
git commit -am "feat: ..."
git push origin feature/your-feature
```

---

如果你希望，我可以：

- 把图片加载入口加到设置面板（UI 上选择图片并保存到 config），
- 或把图片渲染改为保留纵横比并支持居中/裁剪/填充模式，
- 或继续调试 FBX 渲染管线。

请告诉我你接下来想优先做哪一项，我会继续实现并验证。

---

© 开发者团队
