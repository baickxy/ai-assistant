# AI助手桌面应用设计文档

## Part 1: 视觉设计系统

### 色彩系统

**主色调**
- 主背景色: `#1a1a2e` (深邃蓝黑)
- 次背景色: `#16213e` (深蓝)
- 强调色: `#0f3460` (海蓝)
- 高亮色: `#e94560` (珊瑚红)

**文字颜色**
- 主要文字: `#ffffff` (白色)
- 次要文字: `#b8b8d1` (浅灰蓝)
- 禁用文字: `#6b6b8a` (深灰)

**UI元素颜色**
- 边框颜色: `#2d3561` (深蓝灰)
- 悬停背景: `#252542` (浅蓝黑)
- 成功色: `#4caf50` (绿色)
- 警告色: `#ff9800` (橙色)

### 字体系统

**字体家族**
- 主字体: `Segoe UI`, `PingFang SC`, `Microsoft YaHei`, sans-serif
- 等宽字体: `Consolas`, `Monaco`, `Courier New`, monospace

**字体大小**
- 标题: 18px, font-weight: 600
- 正文: 14px, font-weight: 400
- 小字: 12px, font-weight: 400
- 按钮文字: 14px, font-weight: 500

### 间距系统

**组件间距**
- 小间距: 8px
- 中间距: 16px
- 大间距: 24px
- 超大间距: 32px

**圆角**
- 小圆角: 4px (按钮、输入框)
- 中圆角: 8px (卡片、面板)
- 大圆角: 16px (窗口、对话框)

---

## Part 2: 全局动画与交互

### 窗口动画

**启动动画**
- 窗口从屏幕底部滑入
- 持续时间: 800ms
- 缓动函数: cubic-bezier(0.34, 1.56, 0.64, 1) (弹性效果)
- 透明度从0到1

**拖动交互**
- 鼠标按下时窗口轻微缩放 (0.98)
- 拖动时窗口透明度变为0.9
- 释放时弹性回弹
- 持续时间: 200ms

**关闭动画**
- 窗口缩小并淡出
- 持续时间: 300ms
- 缓动函数: ease-out

### 3D模型动画 (已改用2D渲染)

**渲染方式变更说明**
- 原始设计: 使用 QOpenGLWidget 进行 OpenGL 3.3 渲染
- 实际问题: QOpenGLWidget 在 PyQt6 + Intel Iris Xe Graphics 上存在严重渲染 bug，所有内容不可见
- 最终方案: 改用 QWidget + QPainter 进行 2D 图片渲染
- 影响: 不再支持 3D 模型和动画，改用静态图片显示

**当前支持的渲染特性**
- 图片加载: PNG, JPG, JPEG, BMP 格式
- 缩放模式:
  - "fit": 保持宽高比，完整显示图片
  - "stretch": 拉伸填充整个窗口
- 背景显示: 无图片时显示渐变蓝色背景
- 鼠标交互: 支持基本的鼠标事件记录

**已禁用的功能**
- FBX 3D 模型加载和显示
- 3D 模型动画（呼吸、说话、响应等）
- OpenGL 着色器渲染
- 3D 变换和交互

### 语音波形动画

**录音状态**
- 波形条高度随音量变化
- 颜色从绿色渐变到红色
- 动画流畅，60fps

**播放状态**
- 波形从中心向外扩散
- 颜色: 高亮色 #e94560
- 持续时间: 与语音长度同步

---

## Part 3: 功能模块设计

### 3.1 主窗口 (无边框、透明背景)

**布局**
- 窗口大小: 400x600px (可调整)
- 位置: 屏幕右下角，距边缘20px
- 无边框、无标题栏
- 背景透明 (仅显示3D模型)

**3D模型显示区域**
- 占据窗口大部分空间
- 支持鼠标拖动移动窗口
- 右键菜单显示功能选项

**交互区域**
- 双击模型: 打开/关闭对话面板
- 拖拽模型: 移动窗口位置
- 右键: 显示设置菜单

### 3.2 对话面板

**触发方式**
- 双击3D模型
- 语音唤醒词
- 系统托盘图标点击

**面板设计**
- 从模型右侧滑出
- 宽度: 350px
- 高度: 500px
- 圆角: 16px
- 背景: 毛玻璃效果 (backdrop-blur: 20px)
- 边框: 1px solid #2d3561

**内容区域**
- 顶部: 标题栏 (助手名称 + 关闭按钮)
- 中部: 对话历史 (滚动区域)
- 底部: 输入框 + 发送按钮

**消息气泡**
- 用户消息: 右对齐，背景 #0f3460
- AI消息: 左对齐，背景 #252542
- 圆角: 12px
- 最大宽度: 80%
- 内边距: 12px

### 3.3 设置面板

**触发方式**
- 右键3D模型
- 系统托盘菜单
- 快捷键 Ctrl+,

**面板内容**
- 模型选择 (FBX文件列表)
- 语音选择 (声音列表)
- 唤醒词设置
- Ollama模型选择
- 透明度调节
- 开机自启选项

### 3.4 系统托盘

**图标**
- 应用图标显示在系统托盘
- 右键菜单:
  - 显示/隐藏助手
  - 打开设置
  - 退出应用

---

## Part 4: 技术架构

### 模块划分

```
ai-assistant/
├── main.py                 # 程序入口
├── config.py               # 配置管理
├── requirements.txt        # Python依赖
│
├── modules/
│   ├── __init__.py
│   ├── window.py           # 主窗口管理 (PyQt6)
│   ├── renderer.py         # 3D渲染 (OpenGL)
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
├── assets/
│   ├── models/             # FBX模型文件
│   ├── voices/             # 语音样本
│   └── icons/              # 图标资源
│
└── utils/
    ├── __init__.py
    ├── thread_pool.py      # 线程池管理
    └── helpers.py          # 工具函数
```

### 多线程架构

**主线程**
- PyQt6 GUI事件循环
- 3D渲染更新 (60fps)

**语音线程**
- 持续监听麦克风
- 唤醒词检测
- 语音识别处理

**LLM线程**
- 与Ollama通信
- 流式响应处理

**动画线程**
- 3D模型动画更新
- 口型同步计算

### 技术栈

**核心框架**
- Python 3.10+
- PyQt6 6.6+ (GUI框架)
- PyOpenGL 3.1+ (3D渲染)
- Assimp/pyassimp (FBX加载)

**语音处理**
- SpeechRecognition (语音识别)
- pyttsx3 (语音合成)
- pvporcupine (唤醒词检测)
- PyAudio (音频输入)

**LLM集成**
- ollama-python (Ollama客户端)
- requests (HTTP通信)

**其他**
- numpy (数学计算)
- Pillow (图像处理)
- pystray (系统托盘)

---

## Part 5: 交互流程

### 启动流程
1. 加载配置文件
2. 初始化日志系统
3. 启动系统托盘
4. 加载3D模型
5. 初始化语音模块
6. 连接Ollama
7. 显示主窗口

### 语音交互流程
1. 持续监听麦克风 (唤醒词线程)
2. 检测到唤醒词 → 播放提示音
3. 开始录音 (5秒超时)
4. 语音识别 → 文本
5. 发送给LLM
6. 接收流式响应
7. 语音合成播放
8. 3D模型口型同步

### 文本交互流程
1. 用户输入文本
2. 显示在用户消息气泡
3. 发送给LLM
4. 接收流式响应
5. 实时更新AI消息气泡
6. 可选: 语音朗读

---

## Part 6: 配置说明

### 配置文件 (config.json)

```json
{
  "window": {
    "width": 400,
    "height": 600,
    "pos_x": 1400,
    "pos_y": 400,
    "opacity": 0.95,
    "always_on_top": true
  },
  "model": {
    "current": "default.png",
    "scale_mode": "fit",
    "scale": 1.0
  },
  "voice": {
    "recognition_lang": "zh-CN",
    "synthesis_voice": "default",
    "synthesis_rate": 150,
    "synthesis_volume": 0.8
  },
  "wake_word": {
    "enabled": true,
    "keyword": "小助手",
    "sensitivity": 0.7
  },
  "ollama": {
    "host": "http://localhost:11434",
    "model": "llama3.2",
    "temperature": 0.7,
    "max_tokens": 2048
  },
  "general": {
    "auto_start": false,
    "minimize_to_tray": true,
    "voice_feedback": true
  }
}
```

---

## Part 7: 性能优化

### 3D渲染优化
- 使用VBO/VAO减少CPU-GPU数据传输
- 帧率限制在60fps
- 模型LOD (细节层次)

### 内存优化
- 模型懒加载
- 语音缓存
- 对话历史限制 (最多100条)

### CPU优化
- 语音检测使用轻量级模型
- LLM请求异步处理
- 动画插值优化

---

## Part 8: 错误处理

### 常见错误
- Ollama未启动 → 显示提示，提供手动连接
- 麦克风权限 → 引导用户开启权限
- 模型加载失败 → 使用默认模型
- 网络错误 → 离线模式提示

### 日志系统
- 日志级别: INFO, WARNING, ERROR
- 日志文件: logs/ai-assistant.log
- 控制台输出: 开发模式开启
