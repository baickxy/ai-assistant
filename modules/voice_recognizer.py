"""
语音识别模块
使用SpeechRecognition库进行语音识别
"""

import logging
import queue
import threading
import time
from typing import Optional, Callable, List
from pathlib import Path

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    logging.warning("speech_recognition未安装")

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logging.warning("pyaudio未安装")

from config import config
from utils.thread_pool import WorkerThread

logger = logging.getLogger(__name__)


class VoiceRecognizer(WorkerThread):
    """语音识别器"""
    
    def __init__(self):
        super().__init__(name="VoiceRecognizer")
        
        self.recognizer = None
        self.microphone = None
        self.is_listening = False
        
        # 识别结果回调
        self.on_result: Optional[Callable[[str], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
        # 识别队列
        self.audio_queue = queue.Queue()
        
        # 识别语言
        self.language = config.voice.recognition_lang
        
        # 初始化
        self._initialize()
        
    def _initialize(self):
        """初始化语音识别器"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            logger.error("speech_recognition库未安装")
            return
            
        if not PYAUDIO_AVAILABLE:
            logger.error("pyaudio库未安装")
            return
            
        try:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold = 300
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.pause_threshold = 0.8
            
            # 获取麦克风
            self.microphone = sr.Microphone()
            
            # 校准环境噪音
            with self.microphone as source:
                logger.info("正在校准麦克风...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                logger.info(f"能量阈值: {self.recognizer.energy_threshold}")
                
            logger.info("语音识别器初始化完成")
            
        except Exception as e:
            logger.error(f"语音识别器初始化失败: {e}", exc_info=True)
            
    def run(self):
        """线程主循环"""
        if not self.recognizer or not self.microphone:
            logger.error("语音识别器未初始化，线程退出")
            return
            
        logger.info("语音识别线程启动")
        
        while self.running:
            self.wait_if_paused()
            
            if not self.is_listening:
                time.sleep(0.1)
                continue
                
            try:
                # 监听音频
                with self.microphone as source:
                    logger.debug("正在监听...")
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    
                # 放入队列进行识别
                self.audio_queue.put(audio)
                
                # 处理队列中的音频
                while not self.audio_queue.empty():
                    audio_data = self.audio_queue.get()
                    self._recognize_audio(audio_data)
                    self.audio_queue.task_done()
                    
            except sr.WaitTimeoutError:
                logger.debug("监听超时")
            except Exception as e:
                logger.error(f"监听错误: {e}")
                if self.on_error:
                    self.on_error(e)
                    
    def _recognize_audio(self, audio):
        """
        识别音频
        
        Args:
            audio: 音频数据
        """
        if not self.recognizer:
            return
            
        try:
            # 使用Google语音识别 (在线)
            logger.debug("正在识别...")
            text = self.recognizer.recognize_google(
                audio, 
                language=self.language
            )
            
            if text:
                logger.info(f"识别结果: {text}")
                if self.on_result:
                    self.on_result(text)
                    
        except sr.UnknownValueError:
            logger.debug("无法识别音频")
        except sr.RequestError as e:
            logger.error(f"识别服务错误: {e}")
            # 尝试使用离线识别
            self._recognize_offline(audio)
        except Exception as e:
            logger.error(f"识别错误: {e}")
            if self.on_error:
                self.on_error(e)
                
    def _recognize_offline(self, audio):
        """
        离线识别 (使用Vosk或其他离线引擎)
        
        Args:
            audio: 音频数据
        """
        # 简化的离线识别实现
        # 实际项目中可以使用Vosk、Whisper等离线引擎
        logger.debug("离线识别未实现")
        
    def start_listening(self):
        """开始监听"""
        if not self.recognizer:
            logger.error("语音识别器未初始化")
            return False
            
        self.is_listening = True
        logger.info("开始监听")
        return True
        
    def stop_listening(self):
        """停止监听"""
        self.is_listening = False
        logger.info("停止监听")
        
    def listen_once(self, timeout: int = 5) -> Optional[str]:
        """
        单次监听
        
        Args:
            timeout: 超时时间 (秒)
            
        Returns:
            识别到的文本，失败返回None
        """
        if not self.recognizer or not self.microphone:
            logger.error("语音识别器未初始化")
            return None
            
        try:
            with self.microphone as source:
                logger.info("请说话...")
                audio = self.recognizer.listen(source, timeout=timeout)
                
            text = self.recognizer.recognize_google(
                audio,
                language=self.language
            )
            
            logger.info(f"识别结果: {text}")
            return text
            
        except sr.UnknownValueError:
            logger.warning("无法识别")
            return None
        except sr.RequestError as e:
            logger.error(f"识别服务错误: {e}")
            return None
        except Exception as e:
            logger.error(f"识别错误: {e}")
            return None
            
    def set_language(self, language: str):
        """
        设置识别语言
        
        Args:
            language: 语言代码 (如 'zh-CN', 'en-US')
        """
        self.language = language
        logger.info(f"识别语言设置为: {language}")
        
    def set_energy_threshold(self, threshold: int):
        """
        设置能量阈值
        
        Args:
            threshold: 阈值 (默认300)
        """
        if self.recognizer:
            self.recognizer.energy_threshold = threshold
            logger.info(f"能量阈值设置为: {threshold}")
            
    def calibrate(self, duration: int = 1):
        """
        校准麦克风
        
        Args:
            duration: 校准时长 (秒)
        """
        if not self.recognizer or not self.microphone:
            logger.error("语音识别器未初始化")
            return
            
        try:
            with self.microphone as source:
                logger.info(f"正在校准麦克风 ({duration}秒)...")
                self.recognizer.adjust_for_ambient_noise(source, duration=duration)
                logger.info(f"校准完成，能量阈值: {self.recognizer.energy_threshold}")
        except Exception as e:
            logger.error(f"校准失败: {e}")
            
    def is_available(self) -> bool:
        """检查语音识别是否可用"""
        return SPEECH_RECOGNITION_AVAILABLE and PYAUDIO_AVAILABLE and self.recognizer is not None
        
    def get_microphones(self) -> List[str]:
        """获取可用麦克风列表"""
        if not PYAUDIO_AVAILABLE:
            return []
            
        try:
            p = pyaudio.PyAudio()
            devices = []
            
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    devices.append(f"{info['name']}")
                    
            p.terminate()
            return devices
            
        except Exception as e:
            logger.error(f"获取麦克风列表失败: {e}")
            return []
