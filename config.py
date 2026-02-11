"""
配置管理模块
负责加载、保存和管理应用程序配置
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional
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
    """3D模型配置"""
    current: str = "default.fbx"
    scale: float = 1.0
    animation_speed: float = 1.0


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
        """获取当前模型路径"""
        return self.base_dir / "assets" / "models" / self.model.current
    
    def get_available_models(self) -> list:
        """获取可用的模型列表"""
        models_dir = self.base_dir / "assets" / "models"
        if not models_dir.exists():
            return []
        return [f.name for f in models_dir.iterdir() if f.suffix.lower() == '.fbx']
    
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
