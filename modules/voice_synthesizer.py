"""
语音合成模块
支持多种语音引擎: pyttsx3 (离线), edge-tts (在线)
"""

import logging
import tempfile
import asyncio
import threading
import queue
from typing import Optional, Callable, List
from pathlib import Path
from dataclasses import dataclass

import pygame

# 尝试导入pyttsx3
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    logging.warning("pyttsx3未安装")

# 尝试导入edge-tts
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    logging.warning("edge-tts未安装")

from config import config
from utils.helpers import get_available_voices

logger = logging.getLogger(__name__)


@dataclass
class SpeechTask:
    """语音任务"""
    text: str
    voice: str
    rate: int
    volume: float
    on_complete: Optional[Callable] = None


class VoiceSynthesizer:
    """语音合成器"""
    
    def __init__(self):
        # pyttsx3引擎
        self.tts_engine = None
        
        # 播放队列
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        
        # 当前语音设置
        self.current_voice = config.voice.synthesis_voice
        self.current_rate = config.voice.synthesis_rate
        self.current_volume = config.voice.synthesis_volume
        
        # 使用Edge TTS
        self.use_edge_tts = config.voice.use_edge_tts
        self.edge_voice = config.voice.edge_tts_voice
        
        # 初始化pygame音频
        pygame.mixer.init(frequency=24000, channels=1)
        
        # 初始化TTS引擎
        self._initialize_tts()
        
        # 启动播放线程
        self.play_thread = threading.Thread(target=self._play_loop, daemon=True)
        self.play_thread.start()
        
        logger.info("语音合成器初始化完成")
        
    def _initialize_tts(self):
        """初始化TTS引擎"""
        if PYTTSX3_AVAILABLE:
            try:
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', self.current_rate)
                self.tts_engine.setProperty('volume', self.current_volume)
                
                # 设置语音
                voices = self.tts_engine.getProperty('voices')
                if voices:
                    # 尝试找到中文语音
                    for voice in voices:
                        if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                            self.tts_engine.setProperty('voice', voice.id)
                            break
                            
                logger.info("pyttsx3引擎初始化完成")
                
            except Exception as e:
                logger.error(f"pyttsx3初始化失败: {e}")
                self.tts_engine = None
        else:
            logger.warning("pyttsx3不可用")
            
    def _play_loop(self):
        """播放循环线程"""
        while True:
            try:
                task = self.speech_queue.get(timeout=0.1)
                self._speak_task(task)
                self.speech_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"播放循环错误: {e}")
                
    def _speak_task(self, task: SpeechTask):
        """
        执行语音任务
        
        Args:
            task: 语音任务
        """
        self.is_speaking = True
        
        try:
            if self.use_edge_tts and EDGE_TTS_AVAILABLE:
                self._speak_with_edge_tts(task)
            elif self.tts_engine:
                self._speak_with_pyttsx3(task)
            else:
                logger.warning("没有可用的TTS引擎")
                
        except Exception as e:
            logger.error(f"语音合成错误: {e}")
            
        finally:
            self.is_speaking = False
            if task.on_complete:
                task.on_complete()
                
    def _speak_with_pyttsx3(self, task: SpeechTask):
        """
        使用pyttsx3合成语音
        
        Args:
            task: 语音任务
        """
        if not self.tts_engine:
            return
            
        # 设置参数
        self.tts_engine.setProperty('rate', task.rate)
        self.tts_engine.setProperty('volume', task.volume)
        
        # 合成并播放
        self.tts_engine.say(task.text)
        self.tts_engine.runAndWait()
        
    def _speak_with_edge_tts(self, task: SpeechTask):
        """
        使用Edge TTS合成语音
        
        Args:
            task: 语音任务
        """
        if not EDGE_TTS_AVAILABLE:
            return
            
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                tmp_path = tmp_file.name
                
            # 运行异步TTS
            asyncio.run(self._edge_tts_synthesize(task.text, tmp_path))
            
            # 播放音频
            self._play_audio(tmp_path)
            
            # 删除临时文件
            Path(tmp_path).unlink(missing_ok=True)
            
        except Exception as e:
            logger.error(f"Edge TTS错误: {e}")
            # 回退到pyttsx3
            if self.tts_engine:
                self._speak_with_pyttsx3(task)
                
    async def _edge_tts_synthesize(self, text: str, output_path: str):
        """
        Edge TTS异步合成
        
        Args:
            text: 文本
            output_path: 输出路径
        """
        communicate = edge_tts.Communicate(text, self.edge_voice)
        await communicate.save(output_path)
        
    def _play_audio(self, audio_path: str):
        """
        播放音频文件
        
        Args:
            audio_path: 音频文件路径
        """
        try:
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
                
        except Exception as e:
            logger.error(f"播放音频错误: {e}")
            
    def speak(
        self, 
        text: str, 
        voice: Optional[str] = None,
        rate: Optional[int] = None,
        volume: Optional[float] = None,
        on_complete: Optional[Callable] = None
    ):
        """
        合成语音
        
        Args:
            text: 要合成的文本
            voice: 语音ID (可选)
            rate: 语速 (可选)
            volume: 音量 (可选)
            on_complete: 完成回调 (可选)
        """
        if not text:
            return
            
        task = SpeechTask(
            text=text,
            voice=voice or self.current_voice,
            rate=rate or self.current_rate,
            volume=volume or self.current_volume,
            on_complete=on_complete
        )
        
        self.speech_queue.put(task)
        logger.info(f"语音任务已添加: {text[:30]}...")
        
    def speak_immediately(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: Optional[int] = None,
        volume: Optional[float] = None
    ):
        """
        立即合成语音 (阻塞式)
        
        Args:
            text: 要合成的文本
            voice: 语音ID (可选)
            rate: 语速 (可选)
            volume: 音量 (可选)
        """
        task = SpeechTask(
            text=text,
            voice=voice or self.current_voice,
            rate=rate or self.current_rate,
            volume=volume or self.current_volume
        )
        
        self._speak_task(task)
        
    def stop(self):
        """停止播放"""
        # 清空队列
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except queue.Empty:
                break
                
        # 停止当前播放
        pygame.mixer.music.stop()
        
        if self.tts_engine:
            self.tts_engine.stop()
            
        self.is_speaking = False
        logger.info("语音播放已停止")
        
    def pause(self):
        """暂停播放"""
        pygame.mixer.music.pause()
        
    def resume(self):
        """恢复播放"""
        pygame.mixer.music.unpause()
        
    def is_busy(self) -> bool:
        """检查是否正在播放"""
        return self.is_speaking or not self.speech_queue.empty()
        
    def set_voice(self, voice_id: str):
        """
        设置语音
        
        Args:
            voice_id: 语音ID
        """
        self.current_voice = voice_id
        
        # 如果是Edge TTS语音
        if voice_id.startswith('zh-') or voice_id.startswith('en-'):
            self.use_edge_tts = True
            self.edge_voice = voice_id
            logger.info(f"切换到Edge TTS语音: {voice_id}")
        else:
            self.use_edge_tts = False
            
            # 设置pyttsx3语音
            if self.tts_engine:
                voices = self.tts_engine.getProperty('voices')
                for voice in voices:
                    if voice_id in voice.id or voice_id in voice.name:
                        self.tts_engine.setProperty('voice', voice.id)
                        logger.info(f"设置语音: {voice.name}")
                        break
                        
    def set_rate(self, rate: int):
        """
        设置语速
        
        Args:
            rate: 语速 (默认150)
        """
        self.current_rate = rate
        if self.tts_engine:
            self.tts_engine.setProperty('rate', rate)
        logger.info(f"语速设置为: {rate}")
        
    def set_volume(self, volume: float):
        """
        设置音量
        
        Args:
            volume: 音量 (0.0 - 1.0)
        """
        self.current_volume = max(0.0, min(1.0, volume))
        if self.tts_engine:
            self.tts_engine.setProperty('volume', self.current_volume)
        logger.info(f"音量设置为: {self.current_volume}")
        
    def get_available_voices(self) -> List[dict]:
        """获取可用语音列表"""
        return get_available_voices()
        
    def save_to_file(self, text: str, output_path: str, voice: Optional[str] = None):
        """
        保存语音到文件
        
        Args:
            text: 文本
            output_path: 输出文件路径
            voice: 语音ID (可选)
        """
        if not self.tts_engine:
            logger.error("TTS引擎未初始化")
            return
            
        try:
            self.tts_engine.save_to_file(text, output_path)
            self.tts_engine.runAndWait()
            logger.info(f"语音已保存到: {output_path}")
        except Exception as e:
            logger.error(f"保存语音失败: {e}")
