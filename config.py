"""
配置管理模块
负责加载、保存和管理应用程序配置
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class WindowConfig:
    """窗口配置"""
    width: int = 400
    height: int = 600
    pos_x: int = 1400
    pos_y: int = 400
    opacity: float = 0.95
    always_on_top: bool = True


@dataclass
class ModelConfig:
    """图片显示配置 (原3D模型配置已改用2D图片)"""
    current: str = "20240908154446102206.png"  # 当前显示的图片文件名（使用icons目录下实际存在的图片）
    scale_mode: str = "fit"  # 缩放模式: "fit" (保持宽高比) 或 "stretch" (拉伸填充)
    scale: float = 1.0  # 预留，未来可能用于缩放


@dataclass
class VoiceConfig:
    """语音配置"""
    recognition_lang: str = "zh-CN"
    synthesis_voice: str = "default"
    synthesis_rate: int = 150
    synthesis_volume: float = 0.8
    use_edge_tts: bool = True
    edge_tts_voice: str = "zh-CN-XiaoxiaoNeural"


@dataclass
class WakeWordConfig:
    """唤醒词配置"""
    enabled: bool = True
    keyword: str = "小助手"
    sensitivity: float = 0.7
    access_key: str = ""  # Picovoice访问密钥


@dataclass
class OllamaConfig:
    """Ollama配置"""
    host: str = "http://localhost:11434"
    model: str = "llama3.2"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30
    # 是否允许模型在推理时访问外部网络（由服务端实现支持时生效）
    allow_network: bool = True
    # 是否允许模型调用系统工具（如时间、位置等）
    allow_system_tools: bool = True
    # 系统工具调用的最大迭代次数
    max_tool_iterations: int = 3


@dataclass
class GeneralConfig:
    """通用配置"""
    auto_start: bool = False
    minimize_to_tray: bool = True
    voice_feedback: bool = True
    log_level: str = "INFO"


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.config_file = self.base_dir / "config.json"
        
        # 初始化配置对象
        self.window = WindowConfig()
        self.model = ModelConfig()
        self.voice = VoiceConfig()
        self.wake_word = WakeWordConfig()
        self.ollama = OllamaConfig()
        self.general = GeneralConfig()
        
        # 加载配置
        self.load()
    
    def load(self) -> None:
        """从文件加载配置"""
        if not self.config_file.exists():
            self.save()  # 创建默认配置
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 加载各模块配置
            if 'window' in data:
                self.window = WindowConfig(**data['window'])
            if 'model' in data:
                self.model = ModelConfig(**data['model'])
            if 'voice' in data:
                self.voice = VoiceConfig(**data['voice'])
            if 'wake_word' in data:
                self.wake_word = WakeWordConfig(**data['wake_word'])
            if 'ollama' in data:
                self.ollama = OllamaConfig(**data['ollama'])
            if 'general' in data:
                self.general = GeneralConfig(**data['general'])
                
        except Exception as e:
            print(f"加载配置失败: {e}，使用默认配置")
            self.save()
    
    def save(self) -> None:
        """保存配置到文件"""
        data = {
            'window': asdict(self.window),
            'model': asdict(self.model),
            'voice': asdict(self.voice),
            'wake_word': asdict(self.wake_word),
            'ollama': asdict(self.ollama),
            'general': asdict(self.general)
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def get_model_path(self) -> Path:
        """获取当前图片路径 (原模型路径)"""
        # 先尝试从images目录加载，如果不存在则从icons目录加载
        images_dir = self.base_dir / "assets" / "images"
        icons_dir = self.base_dir / "assets" / "icons"

        # 尝试从images目录加载
        image_path = images_dir / self.model.current
        if image_path.exists():
            return image_path

        # 如果images目录不存在或文件不存在，尝试从icons目录加载
        if icons_dir.exists():
            icon_path = icons_dir / self.model.current
            if icon_path.exists():
                return icon_path

            # 如果指定的文件不存在，返回icons目录下的第一个png文件
            for img_file in icons_dir.glob("*.png"):
                return img_file

        # 如果都找不到，返回默认路径
        return icons_dir / self.model.current

    def get_available_models(self) -> list:
        """获取可用的图片列表 (原模型列表)"""
        # 从icons和images两个目录查找图片
        images_dirs = [
            self.base_dir / "assets" / "icons",
            self.base_dir / "assets" / "images"
        ]

        models = []
        for images_dir in images_dirs:
            if images_dir.exists():
                for f in images_dir.iterdir():
                    if f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.bmp']:
                        models.append(f.name)

        return models
    
    def update_window_position(self, x: int, y: int) -> None:
        """更新窗口位置"""
        self.window.pos_x = x
        self.window.pos_y = y
        self.save()
    
    def update_model(self, model_name: str) -> None:
        """更新当前模型"""
        self.model.current = model_name
        self.save()
    
    def update_voice(self, voice_name: str) -> None:
        """更新语音"""
        self.voice.synthesis_voice = voice_name
        self.save()
    
    def update_ollama_model(self, model_name: str) -> None:
        """更新Ollama模型"""
        self.ollama.model = model_name
        self.save()


# 全局配置实例
config = ConfigManager()
