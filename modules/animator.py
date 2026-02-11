"""
动画控制器模块
管理3D模型的动画播放和混合
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AnimationState(Enum):
    """动画状态"""
    STOPPED = 0
    PLAYING = 1
    PAUSED = 2
    BLENDING = 3


@dataclass
class AnimationClip:
    """动画片段"""
    name: str
    duration: float
    channels: List[Any]
    loop: bool = True
    speed: float = 1.0


class Animator:
    """动画控制器"""
    
    def __init__(self):
        self.animations: Dict[str, AnimationClip] = {}
        self.current_animation: Optional[str] = None
        self.next_animation: Optional[str] = None
        
        # 播放状态
        self.state = AnimationState.STOPPED
        self.current_time = 0.0
        self.blend_time = 0.0
        self.blend_duration = 0.3  # 混合动画持续时间
        
        # 骨骼变换
        self.bone_matrices: Dict[str, np.ndarray] = {}
        
        # 表情/口型同步
        self.mouth_openness = 0.0
        self.target_mouth_openness = 0.0
        
        # 空闲动画参数
        self.idle_time = 0.0
        self.breathe_scale = 1.0
        
        logger.info("动画控制器初始化完成")
        
    def load_animations(self, animations: List[Any]):
        """
        加载动画
        
        Args:
            animations: 动画数据列表
        """
        for anim_data in animations:
            clip = AnimationClip(
                name=anim_data.name,
                duration=anim_data.duration,
                channels=anim_data.channels,
                loop=True,
                speed=1.0
            )
            self.animations[anim_data.name] = clip
            logger.info(f"加载动画: {anim_data.name}, 时长: {anim_data.duration:.2f}s")
            
    def play(self, animation_name: str, fade_in: float = 0.3):
        """
        播放动画
        
        Args:
            animation_name: 动画名称
            fade_in: 淡入时间
        """
        if animation_name not in self.animations:
            logger.warning(f"动画不存在: {animation_name}")
            return
            
        if self.current_animation and self.state == AnimationState.PLAYING:
            # 混合到新动画
            self.next_animation = animation_name
            self.blend_duration = fade_in
            self.blend_time = 0.0
            self.state = AnimationState.BLENDING
            logger.info(f"混合动画: {self.current_animation} -> {animation_name}")
        else:
            # 直接播放
            self.current_animation = animation_name
            self.current_time = 0.0
            self.state = AnimationState.PLAYING
            logger.info(f"播放动画: {animation_name}")
            
    def stop(self):
        """停止动画"""
        self.state = AnimationState.STOPPED
        self.current_animation = None
        self.next_animation = None
        logger.info("动画停止")
        
    def pause(self):
        """暂停动画"""
        if self.state == AnimationState.PLAYING:
            self.state = AnimationState.PAUSED
            logger.info("动画暂停")
            
    def resume(self):
        """恢复动画"""
        if self.state == AnimationState.PAUSED:
            self.state = AnimationState.PLAYING
            logger.info("动画恢复")
            
    def update(self, delta_time: float):
        """
        更新动画
        
        Args:
            delta_time: 时间增量 (秒)
        """
        # 更新空闲动画
        self._update_idle(delta_time)
        
        # 更新口型同步
        self._update_lip_sync(delta_time)
        
        # 更新当前动画
        if self.state == AnimationState.PLAYING and self.current_animation:
            anim = self.animations[self.current_animation]
            
            # 更新时间
            self.current_time += delta_time * anim.speed
            
            # 循环处理
            if self.current_time > anim.duration:
                if anim.loop:
                    self.current_time = self.current_time % anim.duration
                else:
                    self.current_time = anim.duration
                    self.state = AnimationState.STOPPED
                    
        # 更新混合
        elif self.state == AnimationState.BLENDING:
            self.blend_time += delta_time
            
            if self.blend_time >= self.blend_duration:
                # 混合完成
                self.current_animation = self.next_animation
                self.next_animation = None
                self.current_time = 0.0
                self.state = AnimationState.PLAYING
                logger.info(f"混合完成，当前动画: {self.current_animation}")
                
    def _update_idle(self, delta_time: float):
        """更新空闲动画 (呼吸效果)"""
        self.idle_time += delta_time
        
        # 呼吸效果: 正弦波缩放
        breathe = 1.0 + np.sin(self.idle_time * 2.0) * 0.02
        self.breathe_scale = breathe
        
    def _update_lip_sync(self, delta_time: float):
        """更新口型同步"""
        # 平滑过渡到目标开合度
        diff = self.target_mouth_openness - self.mouth_openness
        self.mouth_openness += diff * 10.0 * delta_time
        
    def set_mouth_openness(self, openness: float):
        """
        设置嘴巴开合度 (用于语音同步)
        
        Args:
            openness: 开合度 (0.0 - 1.0)
        """
        self.target_mouth_openness = np.clip(openness, 0.0, 1.0)
        
    def get_bone_transform(self, bone_name: str) -> Optional[np.ndarray]:
        """
        获取骨骼变换矩阵
        
        Args:
            bone_name: 骨骼名称
            
        Returns:
            4x4变换矩阵
        """
        # 简化的实现，返回单位矩阵
        return np.eye(4, dtype=np.float32)
        
    def get_current_pose(self) -> Dict[str, np.ndarray]:
        """
        获取当前姿态
        
        Returns:
            骨骼名称到变换矩阵的映射
        """
        return self.bone_matrices.copy()
        
    def get_blend_factor(self) -> float:
        """
        获取混合因子
        
        Returns:
            混合因子 (0.0 - 1.0)
        """
        if self.state == AnimationState.BLENDING:
            return self.blend_time / self.blend_duration
        return 0.0
        
    def is_playing(self) -> bool:
        """检查是否正在播放"""
        return self.state == AnimationState.PLAYING
        
    def get_animation_names(self) -> List[str]:
        """获取所有动画名称"""
        return list(self.animations.keys())
        
    def set_animation_speed(self, animation_name: str, speed: float):
        """
        设置动画播放速度
        
        Args:
            animation_name: 动画名称
            speed: 速度倍数
        """
        if animation_name in self.animations:
            self.animations[animation_name].speed = speed
            
    def set_animation_loop(self, animation_name: str, loop: bool):
        """
        设置动画是否循环
        
        Args:
            animation_name: 动画名称
            loop: 是否循环
        """
        if animation_name in self.animations:
            self.animations[animation_name].loop = loop
