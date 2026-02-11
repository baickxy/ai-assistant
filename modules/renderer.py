"""
OpenGL渲染器模块
使用PyOpenGL渲染3D模型
"""

import logging
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict

from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QMouseEvent

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GL.shaders import compileProgram, compileShader

from config import config
from .fbx_loader import FBXLoader
from .animator import Animator

logger = logging.getLogger(__name__)


# 顶点着色器
VERTEX_SHADER = """
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aNormal;
layout (location = 2) in vec2 aTexCoord;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform float time;

out vec3 FragPos;
out vec3 Normal;
out vec2 TexCoord;

void main()
{
    vec3 pos = aPos;
    
    // 呼吸动画效果
    float breathe = 1.0 + sin(time * 2.0) * 0.02;
    pos *= breathe;
    
    FragPos = vec3(model * vec4(pos, 1.0));
    Normal = mat3(transpose(inverse(model))) * aNormal;
    TexCoord = aTexCoord;
    
    gl_Position = projection * view * vec4(FragPos, 1.0);
}
"""

# 片段着色器
FRAGMENT_SHADER = """
#version 330 core
in vec3 FragPos;
in vec3 Normal;
in vec2 TexCoord;

uniform vec3 lightPos;
uniform vec3 viewPos;
uniform vec3 lightColor;
uniform vec3 objectColor;
uniform float opacity;

out vec4 FragColor;

void main()
{
    // 环境光
    float ambientStrength = 0.3;
    vec3 ambient = ambientStrength * lightColor;
    
    // 漫反射
    vec3 norm = normalize(Normal);
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;
    
    // 镜面反射
    float specularStrength = 0.5;
    vec3 viewDir = normalize(viewPos - FragPos);
    vec3 reflectDir = reflect(-lightDir, norm);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32);
    vec3 specular = specularStrength * spec * lightColor;
    
    vec3 result = (ambient + diffuse + specular) * objectColor;
    FragColor = vec4(result, opacity);
}
"""


class OpenGLRenderer(QOpenGLWidget):
    """OpenGL渲染器"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 模型数据
        self.model_data = None
        self.fbx_loader = FBXLoader()
        self.animator = Animator()
        
        # OpenGL对象
        self.shader_program = None
        self.vao = None
        self.vbo = None
        self.ebo = None
        
        # 变换矩阵
        self.model_matrix = np.eye(4, dtype=np.float32)
        self.view_matrix = np.eye(4, dtype=np.float32)
        self.projection_matrix = np.eye(4, dtype=np.float32)
        
        # 相机参数
        self.camera_pos = np.array([0.0, 0.0, 5.0], dtype=np.float32)
        self.camera_target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.camera_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        
        # 旋转控制
        self.rotation_x = 0.0
        self.rotation_y = 0.0
        self.last_mouse_pos = None
        
        # 时间
        self.time = 0.0
        
        # 动画定时器
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(16)  # ~60fps
        
        # 设置背景透明
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        logger.info("OpenGL渲染器初始化完成")
        
    def initializeGL(self):
        """初始化OpenGL"""
        try:
            # 设置清除颜色 (透明)
            glClearColor(0.0, 0.0, 0.0, 0.0)
            
            # 启用深度测试
            glEnable(GL_DEPTH_TEST)
            
            # 启用混合 (透明度)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            # 创建着色器程序
            self._create_shaders()
            
            # 初始化视图矩阵
            self._update_view_matrix()
            
            # 加载默认模型
            self._load_default_model()
            
            logger.info("OpenGL初始化完成")
            
        except Exception as e:
            logger.error(f"OpenGL初始化失败: {e}", exc_info=True)
            
    def _create_shaders(self):
        """创建着色器程序"""
        try:
            vertex_shader = compileShader(VERTEX_SHADER, GL_VERTEX_SHADER)
            fragment_shader = compileShader(FRAGMENT_SHADER, GL_FRAGMENT_SHADER)
            self.shader_program = compileProgram(vertex_shader, fragment_shader)
            
            logger.info("着色器程序创建成功")
            
        except Exception as e:
            logger.error(f"着色器编译失败: {e}")
            # 使用固定管线作为后备
            self.shader_program = None
            
    def _load_default_model(self):
        """加载默认模型"""
        # 创建一个简单的立方体作为默认模型
        vertices = np.array([
            # 前面
            -0.5, -0.5,  0.5,  0.0,  0.0,  1.0,  0.0, 0.0,
             0.5, -0.5,  0.5,  0.0,  0.0,  1.0,  1.0, 0.0,
             0.5,  0.5,  0.5,  0.0,  0.0,  1.0,  1.0, 1.0,
            -0.5,  0.5,  0.5,  0.0,  0.0,  1.0,  0.0, 1.0,
            # 后面
            -0.5, -0.5, -0.5,  0.0,  0.0, -1.0,  0.0, 0.0,
             0.5, -0.5, -0.5,  0.0,  0.0, -1.0,  1.0, 0.0,
             0.5,  0.5, -0.5,  0.0,  0.0, -1.0,  1.0, 1.0,
            -0.5,  0.5, -0.5,  0.0,  0.0, -1.0,  0.0, 1.0,
        ], dtype=np.float32)
        
        indices = np.array([
            0, 1, 2, 2, 3, 0,  # 前面
            4, 5, 6, 6, 7, 4,  # 后面
            0, 1, 5, 5, 4, 0,  # 底面
            2, 3, 7, 7, 6, 2,  # 顶面
            0, 3, 7, 7, 4, 0,  # 左面
            1, 2, 6, 6, 5, 1,  # 右面
        ], dtype=np.uint32)
        
        self._create_buffers(vertices, indices)
        self.model_data = {
            'vertices': vertices,
            'indices': indices,
            'index_count': len(indices)
        }
        
    def _create_buffers(self, vertices: np.ndarray, indices: np.ndarray):
        """创建VBO和EBO"""
        if self.shader_program:
            # VAO
            self.vao = glGenVertexArrays(1)
            glBindVertexArray(self.vao)
            
            # VBO
            self.vbo = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
            glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)
            
            # EBO
            self.ebo = glGenBuffers(1)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self.ebo)
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)
            
            # 设置顶点属性
            # 位置 (location = 0)
            glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 8 * 4, ctypes.c_void_p(0))
            glEnableVertexAttribArray(0)
            
            # 法线 (location = 1)
            glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 8 * 4, ctypes.c_void_p(3 * 4))
            glEnableVertexAttribArray(1)
            
            # 纹理坐标 (location = 2)
            glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 8 * 4, ctypes.c_void_p(6 * 4))
            glEnableVertexAttribArray(2)
            
            glBindVertexArray(0)
            
    def _update_view_matrix(self):
        """更新视图矩阵"""
        # 简化的lookAt实现
        forward = self.camera_target - self.camera_pos
        forward = forward / np.linalg.norm(forward)
        
        right = np.cross(forward, self.camera_up)
        right = right / np.linalg.norm(right)
        
        up = np.cross(right, forward)
        
        self.view_matrix = np.array([
            [right[0], right[1], right[2], -np.dot(right, self.camera_pos)],
            [up[0], up[1], up[2], -np.dot(up, self.camera_pos)],
            [-forward[0], -forward[1], -forward[2], np.dot(forward, self.camera_pos)],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        
    def _update_projection_matrix(self):
        """更新投影矩阵"""
        aspect = self.width() / max(self.height(), 1)
        fov = 45.0
        near = 0.1
        far = 100.0
        
        f = 1.0 / np.tan(np.radians(fov) / 2)
        
        self.projection_matrix = np.array([
            [f / aspect, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, (far + near) / (near - far), (2 * far * near) / (near - far)],
            [0, 0, -1, 0]
        ], dtype=np.float32)
        
    def resizeGL(self, w: int, h: int):
        """调整窗口大小"""
        glViewport(0, 0, w, h)
        self._update_projection_matrix()
        
    def paintGL(self):
        """渲染场景"""
        # 清除缓冲区
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        if not self.model_data:
            return
            
        if self.shader_program:
            glUseProgram(self.shader_program)
            
            # 设置uniform变量
            self._set_uniforms()
            
            # 绑定VAO并绘制
            glBindVertexArray(self.vao)
            glDrawElements(GL_TRIANGLES, self.model_data['index_count'], GL_UNSIGNED_INT, None)
            glBindVertexArray(0)
            
            glUseProgram(0)
        else:
            # 使用固定管线绘制
            self._draw_fixed_pipeline()
            
    def _set_uniforms(self):
        """设置着色器uniform变量"""
        # 模型矩阵 (包含旋转)
        model = self.model_matrix.copy()
        
        # 应用旋转
        rx = np.radians(self.rotation_x)
        ry = np.radians(self.rotation_y)
        
        rot_x = np.array([
            [1, 0, 0, 0],
            [0, np.cos(rx), -np.sin(rx), 0],
            [0, np.sin(rx), np.cos(rx), 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        
        rot_y = np.array([
            [np.cos(ry), 0, np.sin(ry), 0],
            [0, 1, 0, 0],
            [-np.sin(ry), 0, np.cos(ry), 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        
        model = model @ rot_x @ rot_y
        
        # 设置矩阵uniform
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_program, "model"),
            1, GL_FALSE, model
        )
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_program, "view"),
            1, GL_FALSE, self.view_matrix
        )
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_program, "projection"),
            1, GL_FALSE, self.projection_matrix
        )
        
        # 设置时间uniform (用于呼吸动画)
        glUniform1f(glGetUniformLocation(self.shader_program, "time"), self.time)
        
        # 设置光照uniform
        glUniform3f(glGetUniformLocation(self.shader_program, "lightPos"), 5.0, 5.0, 5.0)
        glUniform3f(glGetUniformLocation(self.shader_program, "viewPos"), *self.camera_pos)
        glUniform3f(glGetUniformLocation(self.shader_program, "lightColor"), 1.0, 1.0, 1.0)
        glUniform3f(glGetUniformLocation(self.shader_program, "objectColor"), 0.9, 0.9, 1.0)
        glUniform1f(glGetUniformLocation(self.shader_program, "opacity"), 0.95)
        
    def _draw_fixed_pipeline(self):
        """使用固定管线绘制 (后备方案)"""
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, self.width() / max(self.height(), 1), 0.1, 100)
        
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(*self.camera_pos, *self.camera_target, *self.camera_up)
        
        # 应用旋转
        glRotatef(self.rotation_x, 1, 0, 0)
        glRotatef(self.rotation_y, 0, 1, 0)
        
        # 绘制立方体
        glColor4f(0.9, 0.9, 1.0, 0.95)
        glutSolidCube(1.0)
        
    def _update_animation(self):
        """更新动画"""
        self.time += 0.016  # ~60fps
        self.update()  # 触发重绘
        
    # ==================== 公共方法 ====================
    
    def load_model(self, model_path: Path):
        """
        加载FBX模型
        
        Args:
            model_path: 模型文件路径
        """
        try:
            logger.info(f"加载模型: {model_path}")
            
            # 使用FBX加载器加载模型
            model_data = self.fbx_loader.load(model_path)
            
            if model_data:
                self.model_data = model_data
                self._create_buffers(
                    model_data['vertices'],
                    model_data['indices']
                )
                
                # 加载动画
                if 'animations' in model_data:
                    self.animator.load_animations(model_data['animations'])
                    
                logger.info("模型加载成功")
            else:
                logger.warning("模型加载失败，使用默认模型")
                
        except Exception as e:
            logger.error(f"加载模型错误: {e}", exc_info=True)
            
    def play_animation(self, animation_name: str):
        """
        播放动画
        
        Args:
            animation_name: 动画名称
        """
        self.animator.play(animation_name)
        
    def set_rotation(self, x: float, y: float):
        """
        设置旋转角度
        
        Args:
            x: X轴旋转角度
            y: Y轴旋转角度
        """
        self.rotation_x = x
        self.rotation_y = y
        
    def cleanup(self):
        """清理资源"""
        logger.info("清理OpenGL资源...")
        
        self.animation_timer.stop()
        
        # 删除OpenGL对象
        if self.vao:
            glDeleteVertexArrays(1, [self.vao])
        if self.vbo:
            glDeleteBuffers(1, [self.vbo])
        if self.ebo:
            glDeleteBuffers(1, [self.ebo])
        if self.shader_program:
            glDeleteProgram(self.shader_program)
            
    # ==================== 鼠标事件 ====================
    
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.last_mouse_pos = event.pos()
            
    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动"""
        if self.last_mouse_pos:
            dx = event.pos().x() - self.last_mouse_pos.x()
            dy = event.pos().y() - self.last_mouse_pos.y()
            
            self.rotation_y += dx * 0.5
            self.rotation_x += dy * 0.5
            
            self.last_mouse_pos = event.pos()
            self.update()
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放"""
        self.last_mouse_pos = None
