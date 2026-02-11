"""
FBX模型加载模块
支持加载FBX格式的3D模型和动画
"""

import logging
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Mesh:
    """网格数据"""
    vertices: np.ndarray  # 顶点位置 (N, 3)
    normals: np.ndarray   # 顶点法线 (N, 3)
    uvs: np.ndarray       # 纹理坐标 (N, 2)
    indices: np.ndarray   # 索引 (M, 3)
    

@dataclass
class Bone:
    """骨骼数据"""
    name: str
    parent_index: int
    local_matrix: np.ndarray  # 4x4矩阵
    inverse_bind_matrix: np.ndarray  # 4x4矩阵
    

@dataclass
class AnimationCurve:
    """动画曲线"""
    times: np.ndarray
    values: np.ndarray
    

@dataclass
class AnimationChannel:
    """动画通道"""
    bone_name: str
    position_curves: Dict[str, AnimationCurve]  # x, y, z
    rotation_curves: Dict[str, AnimationCurve]  # x, y, z, w (四元数)
    scale_curves: Dict[str, AnimationCurve]     # x, y, z
    

@dataclass
class Animation:
    """动画数据"""
    name: str
    duration: float
    channels: List[AnimationChannel]
    

class FBXLoader:
    """FBX模型加载器"""
    
    def __init__(self):
        self.meshes: List[Mesh] = []
        self.bones: List[Bone] = []
        self.animations: List[Animation] = []
        
        # 尝试导入pyassimp
        self.assimp_available = False
        try:
            import pyassimp
            self.assimp_available = True
            logger.info("pyassimp加载成功")
        except ImportError:
            logger.warning("pyassimp未安装，使用简化模型加载")
            
    def load(self, filepath: Path) -> Optional[Dict[str, Any]]:
        """
        加载FBX文件
        
        Args:
            filepath: FBX文件路径
            
        Returns:
            模型数据字典，包含vertices, indices, animations等
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            logger.error(f"模型文件不存在: {filepath}")
            return None
            
        try:
            if self.assimp_available:
                return self._load_with_assimp(filepath)
            else:
                return self._load_simple_model()
                
        except Exception as e:
            logger.error(f"加载FBX文件失败: {e}", exc_info=True)
            return self._load_simple_model()
            
    def _load_with_assimp(self, filepath: Path) -> Dict[str, Any]:
        """使用pyassimp加载FBX"""
        import pyassimp
        
        logger.info(f"使用pyassimp加载: {filepath}")
        
        with pyassimp.load(str(filepath)) as scene:
            # 提取网格数据
            all_vertices = []
            all_normals = []
            all_uvs = []
            all_indices = []
            index_offset = 0
            
            for mesh in scene.meshes:
                # 顶点
                vertices = np.array(mesh.vertices, dtype=np.float32)
                all_vertices.append(vertices)
                
                # 法线
                if mesh.normals:
                    normals = np.array(mesh.normals, dtype=np.float32)
                else:
                    normals = np.zeros_like(vertices)
                all_normals.append(normals)
                
                # 纹理坐标
                if mesh.texturecoords:
                    uvs = np.array(mesh.texturecoords[0][:, :2], dtype=np.float32)
                else:
                    uvs = np.zeros((len(vertices), 2), dtype=np.float32)
                all_uvs.append(uvs)
                
                # 索引
                indices = np.array(mesh.faces, dtype=np.uint32) + index_offset
                all_indices.append(indices)
                
                index_offset += len(vertices)
                
            # 合并数据
            vertices = np.concatenate(all_vertices)
            normals = np.concatenate(all_normals)
            uvs = np.concatenate(all_uvs)
            indices = np.concatenate(all_indices)
            
            # 展平索引
            indices = indices.flatten()
            
            # 构建顶点数据 (位置 + 法线 + UV)
            vertex_data = np.concatenate([
                vertices,
                normals,
                uvs
            ], axis=1).flatten()
            
            # 提取骨骼数据
            bones = self._extract_bones(scene)
            
            # 提取动画数据
            animations = self._extract_animations(scene)
            
            logger.info(f"加载完成: {len(vertices)}顶点, {len(indices)//3}面, {len(bones)}骨骼, {len(animations)}动画")
            
            return {
                'vertices': vertex_data,
                'indices': indices,
                'index_count': len(indices),
                'bones': bones,
                'animations': animations
            }
            
    def _extract_bones(self, scene) -> List[Bone]:
        """提取骨骼数据"""
        bones = []
        
        # 从网格中提取骨骼
        bone_dict = {}
        for mesh in scene.meshes:
            for bone in mesh.bones:
                if bone.name not in bone_dict:
                    bone_dict[bone.name] = {
                        'offset_matrix': np.array(bone.offsetmatrix, dtype=np.float32).reshape(4, 4),
                        'weights': [(v.id, v.weight) for v in bone.weights]
                    }
                    
        # 从场景层级构建骨骼层级
        def process_node(node, parent_index=-1):
            if node.name in bone_dict:
                bone_data = bone_dict[node.name]
                
                # 获取本地变换矩阵
                transform = np.array(node.transformation, dtype=np.float32).reshape(4, 4)
                
                bone = Bone(
                    name=node.name,
                    parent_index=parent_index,
                    local_matrix=transform,
                    inverse_bind_matrix=bone_data['offset_matrix']
                )
                bones.append(bone)
                current_index = len(bones) - 1
                
                # 处理子节点
                for child in node.children:
                    process_node(child, current_index)
                    
        # 从根节点开始处理
        if scene.rootnode:
            process_node(scene.rootnode)
            
        return bones
        
    def _extract_animations(self, scene) -> List[Animation]:
        """提取动画数据"""
        animations = []
        
        if not scene.animations:
            return animations
            
        for anim in scene.animations:
            channels = []
            
            for channel in anim.channels:
                # 位置曲线
                pos_curves = {}
                if hasattr(channel, 'positionkeys') and channel.positionkeys:
                    times = np.array([k[0] for k in channel.positionkeys])
                    values = np.array([k[1] for k in channel.positionkeys])
                    for i, axis in enumerate(['x', 'y', 'z']):
                        pos_curves[axis] = AnimationCurve(
                            times=times,
                            values=values[:, i]
                        )
                        
                # 旋转曲线
                rot_curves = {}
                if hasattr(channel, 'rotationkeys') and channel.rotationkeys:
                    times = np.array([k[0] for k in channel.rotationkeys])
                    values = np.array([k[1] for k in channel.rotationkeys])
                    for i, axis in enumerate(['x', 'y', 'z', 'w']):
                        rot_curves[axis] = AnimationCurve(
                            times=times,
                            values=values[:, i]
                        )
                        
                # 缩放曲线
                scale_curves = {}
                if hasattr(channel, 'scalingkeys') and channel.scalingkeys:
                    times = np.array([k[0] for k in channel.scalingkeys])
                    values = np.array([k[1] for k in channel.scalingkeys])
                    for i, axis in enumerate(['x', 'y', 'z']):
                        scale_curves[axis] = AnimationCurve(
                            times=times,
                            values=values[:, i]
                        )
                        
                anim_channel = AnimationChannel(
                    bone_name=channel.name,
                    position_curves=pos_curves,
                    rotation_curves=rot_curves,
                    scale_curves=scale_curves
                )
                channels.append(anim_channel)
                
            animation = Animation(
                name=anim.name if hasattr(anim, 'name') else 'default',
                duration=anim.duration if hasattr(anim, 'duration') else 1.0,
                channels=channels
            )
            animations.append(animation)
            
        return animations
        
    def _load_simple_model(self) -> Dict[str, Any]:
        """加载简化模型 (当FBX加载失败时使用)"""
        logger.info("使用简化模型")
        
        # 创建一个彩色的立方体
        vertices = np.array([
            # 前面 (红色)
            -0.5, -0.5,  0.5,  0.0,  0.0,  1.0,  0.0, 0.0,
             0.5, -0.5,  0.5,  0.0,  0.0,  1.0,  1.0, 0.0,
             0.5,  0.5,  0.5,  0.0,  0.0,  1.0,  1.0, 1.0,
            -0.5,  0.5,  0.5,  0.0,  0.0,  1.0,  0.0, 1.0,
            # 后面 (绿色)
            -0.5, -0.5, -0.5,  0.0,  0.0, -1.0,  0.0, 0.0,
             0.5, -0.5, -0.5,  0.0,  0.0, -1.0,  1.0, 0.0,
             0.5,  0.5, -0.5,  0.0,  0.0, -1.0,  1.0, 1.0,
            -0.5,  0.5, -0.5,  0.0,  0.0, -1.0,  0.0, 1.0,
            # 右面 (蓝色)
             0.5, -0.5,  0.5,  1.0,  0.0,  0.0,  0.0, 0.0,
             0.5, -0.5, -0.5,  1.0,  0.0,  0.0,  1.0, 0.0,
             0.5,  0.5, -0.5,  1.0,  0.0,  0.0,  1.0, 1.0,
             0.5,  0.5,  0.5,  1.0,  0.0,  0.0,  0.0, 1.0,
            # 左面 (黄色)
            -0.5, -0.5, -0.5, -1.0,  0.0,  0.0,  0.0, 0.0,
            -0.5, -0.5,  0.5, -1.0,  0.0,  0.0,  1.0, 0.0,
            -0.5,  0.5,  0.5, -1.0,  0.0,  0.0,  1.0, 1.0,
            -0.5,  0.5, -0.5, -1.0,  0.0,  0.0,  0.0, 1.0,
            # 顶面 (紫色)
            -0.5,  0.5,  0.5,  0.0,  1.0,  0.0,  0.0, 0.0,
             0.5,  0.5,  0.5,  0.0,  1.0,  0.0,  1.0, 0.0,
             0.5,  0.5, -0.5,  0.0,  1.0,  0.0,  1.0, 1.0,
            -0.5,  0.5, -0.5,  0.0,  1.0,  0.0,  0.0, 1.0,
            # 底面 (青色)
            -0.5, -0.5, -0.5,  0.0, -1.0,  0.0,  0.0, 0.0,
             0.5, -0.5, -0.5,  0.0, -1.0,  0.0,  1.0, 0.0,
             0.5, -0.5,  0.5,  0.0, -1.0,  0.0,  1.0, 1.0,
            -0.5, -0.5,  0.5,  0.0, -1.0,  0.0,  0.0, 1.0,
        ], dtype=np.float32)
        
        indices = np.array([
            # 前面
            0, 1, 2, 2, 3, 0,
            # 后面
            4, 5, 6, 6, 7, 4,
            # 右面
            8, 9, 10, 10, 11, 8,
            # 左面
            12, 13, 14, 14, 15, 12,
            # 顶面
            16, 17, 18, 18, 19, 16,
            # 底面
            20, 21, 22, 22, 23, 20,
        ], dtype=np.uint32)
        
        return {
            'vertices': vertices,
            'indices': indices,
            'index_count': len(indices),
            'bones': [],
            'animations': []
        }
        
    def get_mesh_count(self) -> int:
        """获取网格数量"""
        return len(self.meshes)
        
    def get_bone_count(self) -> int:
        """获取骨骼数量"""
        return len(self.bones)
        
    def get_animation_count(self) -> int:
        """获取动画数量"""
        return len(self.animations)
