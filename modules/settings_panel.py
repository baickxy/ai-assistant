"""
设置面板模块
提供应用程序设置界面
"""

import logging
from typing import Optional, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QSlider, QCheckBox, QPushButton, QTabWidget, QSpinBox,
    QDoubleSpinBox, QLineEdit, QGroupBox, QMessageBox,
    QFileDialog, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from config import config
from utils.helpers import (
    get_available_voices, 
    get_available_ollama_models,
    check_ollama_running
)

logger = logging.getLogger(__name__)


class SettingsPanel(QWidget):
    """设置面板"""
    
    # 信号
    model_changed = pyqtSignal(str)  # 模型改变
    voice_changed = pyqtSignal(str)  # 语音改变
    settings_saved = pyqtSignal()    # 设置保存
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 初始化UI
        self._setup_ui()
        
        # 加载当前设置
        self._load_settings()
        
        logger.info("设置面板初始化完成")
        
    def _setup_ui(self):
        """设置UI界面"""
        # 窗口属性
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 主容器
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #1a1a2e;
                border: 1px solid #2d3561;
                border-radius: 16px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        container_layout.setSpacing(16)
        
        # 标题栏
        title_bar = QHBoxLayout()
        
        title_label = QLabel("⚙️ 设置")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 20px;
                font-weight: 600;
            }
        """)
        title_bar.addWidget(title_label)
        
        title_bar.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #b8b8d1;
                border: none;
                border-radius: 16px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #e94560;
                color: #ffffff;
            }
        """)
        close_btn.clicked.connect(self.hide)
        title_bar.addWidget(close_btn)
        
        container_layout.addLayout(title_bar)
        
        # 标签页
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2d3561;
                border-radius: 8px;
                background-color: #16213e;
            }
            QTabBar::tab {
                background-color: #252542;
                color: #b8b8d1;
                padding: 10px 20px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #0f3460;
                color: #ffffff;
            }
            QTabBar::tab:hover:!selected {
                background-color: #2d3561;
            }
        """)
        
        # 通用设置页
        self._create_general_tab()
        
        # 模型设置页
        self._create_model_tab()
        
        # 语音设置页
        self._create_voice_tab()
        
        # AI设置页
        self._create_ai_tab()
        
        container_layout.addWidget(self.tabs)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # 重置按钮
        reset_btn = QPushButton("重置")
        reset_btn.setFixedSize(80, 36)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #252542;
                color: #b8b8d1;
                border: 1px solid #2d3561;
                border-radius: 18px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2d3561;
                color: #ffffff;
            }
        """)
        reset_btn.clicked.connect(self._reset_settings)
        button_layout.addWidget(reset_btn)
        
        # 保存按钮
        save_btn = QPushButton("保存")
        save_btn.setFixedSize(80, 36)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0f3460;
                color: #ffffff;
                border: none;
                border-radius: 18px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e94560;
            }
        """)
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)
        
        container_layout.addLayout(button_layout)
        
        main_layout.addWidget(container)
        
    def _create_general_tab(self):
        """创建通用设置页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # 窗口设置组
        window_group = QGroupBox("窗口设置")
        window_group.setStyleSheet(self._group_box_style())
        window_layout = QVBoxLayout(window_group)
        
        # 置顶选项
        self.always_on_top = QCheckBox("窗口始终置顶")
        self.always_on_top.setStyleSheet(self._checkbox_style())
        window_layout.addWidget(self.always_on_top)
        
        # 透明度滑块
        opacity_layout = QHBoxLayout()
        opacity_label = QLabel("窗口透明度:")
        opacity_label.setStyleSheet(self._label_style())
        opacity_layout.addWidget(opacity_label)
        
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(50, 100)
        self.opacity_slider.setStyleSheet(self._slider_style())
        opacity_layout.addWidget(self.opacity_slider)
        
        self.opacity_value = QLabel("95%")
        self.opacity_value.setStyleSheet(self._label_style())
        self.opacity_value.setFixedWidth(40)
        opacity_layout.addWidget(self.opacity_value)
        
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_value.setText(f"{v}%")
        )
        window_layout.addLayout(opacity_layout)
        
        layout.addWidget(window_group)
        
        # 启动设置组
        startup_group = QGroupBox("启动设置")
        startup_group.setStyleSheet(self._group_box_style())
        startup_layout = QVBoxLayout(startup_group)
        
        self.auto_start = QCheckBox("开机自动启动")
        self.auto_start.setStyleSheet(self._checkbox_style())
        startup_layout.addWidget(self.auto_start)
        
        self.minimize_to_tray = QCheckBox("关闭时最小化到托盘")
        self.minimize_to_tray.setStyleSheet(self._checkbox_style())
        startup_layout.addWidget(self.minimize_to_tray)
        
        layout.addWidget(startup_group)
        
        # 反馈设置组
        feedback_group = QGroupBox("反馈设置")
        feedback_group.setStyleSheet(self._group_box_style())
        feedback_layout = QVBoxLayout(feedback_group)
        
        self.voice_feedback = QCheckBox("启用语音反馈")
        self.voice_feedback.setStyleSheet(self._checkbox_style())
        feedback_layout.addWidget(self.voice_feedback)
        
        layout.addWidget(feedback_group)
        
        layout.addStretch()
        
        self.tabs.addTab(tab, "通用")
        
    def _create_model_tab(self):
        """创建模型设置页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # 3D模型设置组
        model_group = QGroupBox("3D模型")
        model_group.setStyleSheet(self._group_box_style())
        model_layout = QVBoxLayout(model_group)
        
        # 模型选择
        model_select_layout = QHBoxLayout()
        model_label = QLabel("当前模型:")
        model_label.setStyleSheet(self._label_style())
        model_select_layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.setStyleSheet(self._combo_box_style())
        self.model_combo.addItems(config.get_available_models() or ["default.fbx"])
        model_select_layout.addWidget(self.model_combo)
        
        # 浏览按钮
        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet(self._button_style())
        browse_btn.clicked.connect(self._browse_model)
        model_select_layout.addWidget(browse_btn)
        
        model_layout.addLayout(model_select_layout)
        
        # 模型缩放
        scale_layout = QHBoxLayout()
        scale_label = QLabel("模型缩放:")
        scale_label.setStyleSheet(self._label_style())
        scale_layout.addWidget(scale_label)
        
        self.model_scale = QDoubleSpinBox()
        self.model_scale.setRange(0.1, 3.0)
        self.model_scale.setSingleStep(0.1)
        self.model_scale.setValue(1.0)
        self.model_scale.setStyleSheet(self._spin_box_style())
        scale_layout.addWidget(self.model_scale)
        scale_layout.addStretch()
        
        model_layout.addLayout(scale_layout)
        
        # 动画速度
        anim_layout = QHBoxLayout()
        anim_label = QLabel("动画速度:")
        anim_label.setStyleSheet(self._label_style())
        anim_layout.addWidget(anim_label)
        
        self.anim_speed = QDoubleSpinBox()
        self.anim_speed.setRange(0.1, 3.0)
        self.anim_speed.setSingleStep(0.1)
        self.anim_speed.setValue(1.0)
        self.anim_speed.setStyleSheet(self._spin_box_style())
        anim_layout.addWidget(self.anim_speed)
        anim_layout.addStretch()
        
        model_layout.addLayout(anim_layout)
        
        layout.addWidget(model_group)
        layout.addStretch()
        
        self.tabs.addTab(tab, "模型")
        
    def _create_voice_tab(self):
        """创建语音设置页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # 语音识别设置组
        recog_group = QGroupBox("语音识别")
        recog_group.setStyleSheet(self._group_box_style())
        recog_layout = QVBoxLayout(recog_group)
        
        # 识别语言
        lang_layout = QHBoxLayout()
        lang_label = QLabel("识别语言:")
        lang_label.setStyleSheet(self._label_style())
        lang_layout.addWidget(lang_label)
        
        self.recog_lang = QComboBox()
        self.recog_lang.setStyleSheet(self._combo_box_style())
        self.recog_lang.addItems([
            "zh-CN (简体中文)",
            "zh-TW (繁体中文)",
            "en-US (英语)",
            "ja-JP (日语)",
            "ko-KR (韩语)",
        ])
        lang_layout.addWidget(self.recog_lang)
        lang_layout.addStretch()
        
        recog_layout.addLayout(lang_layout)
        
        layout.addWidget(recog_group)
        
        # 语音合成设置组
        synth_group = QGroupBox("语音合成")
        synth_group.setStyleSheet(self._group_box_style())
        synth_layout = QVBoxLayout(synth_group)
        
        # 语音选择
        voice_layout = QHBoxLayout()
        voice_label = QLabel("语音:")
        voice_label.setStyleSheet(self._label_style())
        voice_layout.addWidget(voice_label)
        
        self.voice_combo = QComboBox()
        self.voice_combo.setStyleSheet(self._combo_box_style())
        
        # 添加可用语音
        voices = get_available_voices()
        for voice in voices:
            self.voice_combo.addItem(voice['name'], voice['id'])
            
        voice_layout.addWidget(self.voice_combo)
        voice_layout.addStretch()
        
        synth_layout.addLayout(voice_layout)
        
        # 语速
        rate_layout = QHBoxLayout()
        rate_label = QLabel("语速:")
        rate_label.setStyleSheet(self._label_style())
        rate_layout.addWidget(rate_label)
        
        self.speech_rate = QSpinBox()
        self.speech_rate.setRange(50, 300)
        self.speech_rate.setValue(150)
        self.speech_rate.setStyleSheet(self._spin_box_style())
        rate_layout.addWidget(self.speech_rate)
        rate_layout.addStretch()
        
        synth_layout.addLayout(rate_layout)
        
        # 音量
        vol_layout = QHBoxLayout()
        vol_label = QLabel("音量:")
        vol_label.setStyleSheet(self._label_style())
        vol_layout.addWidget(vol_label)
        
        self.speech_volume = QSlider(Qt.Orientation.Horizontal)
        self.speech_volume.setRange(0, 100)
        self.speech_volume.setValue(80)
        self.speech_volume.setStyleSheet(self._slider_style())
        vol_layout.addWidget(self.speech_volume)
        
        self.vol_value = QLabel("80%")
        self.vol_value.setStyleSheet(self._label_style())
        self.vol_value.setFixedWidth(40)
        vol_layout.addWidget(self.vol_value)
        
        self.speech_volume.valueChanged.connect(
            lambda v: self.vol_value.setText(f"{v}%")
        )
        
        synth_layout.addLayout(vol_layout)
        
        # 测试按钮
        test_btn = QPushButton("🎵 测试语音")
        test_btn.setStyleSheet(self._button_style())
        test_btn.clicked.connect(self._test_voice)
        synth_layout.addWidget(test_btn)
        
        layout.addWidget(synth_group)
        layout.addStretch()
        
        self.tabs.addTab(tab, "语音")
        
    def _create_ai_tab(self):
        """创建AI设置页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        
        # Ollama设置组
        ollama_group = QGroupBox("Ollama设置")
        ollama_group.setStyleSheet(self._group_box_style())
        ollama_layout = QVBoxLayout(ollama_group)
        
        # 服务地址
        host_layout = QHBoxLayout()
        host_label = QLabel("服务地址:")
        host_label.setStyleSheet(self._label_style())
        host_layout.addWidget(host_label)
        
        self.ollama_host = QLineEdit()
        self.ollama_host.setStyleSheet(self._line_edit_style())
        self.ollama_host.setPlaceholderText("http://localhost:11434")
        host_layout.addWidget(self.ollama_host)
        
        # 检查按钮
        check_btn = QPushButton("检查连接")
        check_btn.setStyleSheet(self._button_style())
        check_btn.clicked.connect(self._check_ollama)
        host_layout.addWidget(check_btn)
        
        ollama_layout.addLayout(host_layout)
        
        # 模型选择
        model_layout = QHBoxLayout()
        model_label = QLabel("AI模型:")
        model_label.setStyleSheet(self._label_style())
        model_layout.addWidget(model_label)
        
        self.ollama_model = QComboBox()
        self.ollama_model.setStyleSheet(self._combo_box_style())
        self.ollama_model.setEditable(True)
        
        # 添加可用模型
        models = get_available_ollama_models()
        self.ollama_model.addItems(models)
        
        model_layout.addWidget(self.ollama_model)
        model_layout.addStretch()
        
        ollama_layout.addLayout(model_layout)
        
        # 温度参数
        temp_layout = QHBoxLayout()
        temp_label = QLabel("温度 (创造性):")
        temp_label.setStyleSheet(self._label_style())
        temp_layout.addWidget(temp_label)
        
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(0.0, 2.0)
        self.temperature.setSingleStep(0.1)
        self.temperature.setValue(0.7)
        self.temperature.setStyleSheet(self._spin_box_style())
        temp_layout.addWidget(self.temperature)
        temp_layout.addStretch()
        
        ollama_layout.addLayout(temp_layout)
        
        # 最大token
        token_layout = QHBoxLayout()
        token_label = QLabel("最大响应长度:")
        token_label.setStyleSheet(self._label_style())
        token_layout.addWidget(token_label)
        
        self.max_tokens = QSpinBox()
        self.max_tokens.setRange(256, 8192)
        self.max_tokens.setSingleStep(256)
        self.max_tokens.setValue(2048)
        self.max_tokens.setStyleSheet(self._spin_box_style())
        token_layout.addWidget(self.max_tokens)
        token_layout.addStretch()
        
        ollama_layout.addLayout(token_layout)
        
        layout.addWidget(ollama_group)
        layout.addStretch()
        
        self.tabs.addTab(tab, "AI")
        
    # ==================== 样式方法 ====================
    
    def _group_box_style(self) -> str:
        """组框样式"""
        return """
            QGroupBox {
                color: #ffffff;
                font-size: 14px;
                font-weight: 600;
                border: 1px solid #2d3561;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """
        
    def _label_style(self) -> str:
        """标签样式"""
        return """
            QLabel {
                color: #b8b8d1;
                font-size: 13px;
            }
        """
        
    def _checkbox_style(self) -> str:
        """复选框样式"""
        return """
            QCheckBox {
                color: #ffffff;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #2d3561;
                background-color: #252542;
            }
            QCheckBox::indicator:checked {
                background-color: #0f3460;
                border-color: #0f3460;
            }
        """
        
    def _slider_style(self) -> str:
        """滑块样式"""
        return """
            QSlider::groove:horizontal {
                height: 6px;
                background: #252542;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                height: 16px;
                margin: -5px 0;
                background: #0f3460;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #e94560;
            }
            QSlider::sub-page:horizontal {
                background: #0f3460;
                border-radius: 3px;
            }
        """
        
    def _combo_box_style(self) -> str:
        """下拉框样式"""
        return """
            QComboBox {
                background-color: #252542;
                color: #ffffff;
                border: 1px solid #2d3561;
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 120px;
            }
            QComboBox:hover {
                border-color: #0f3460;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox QAbstractItemView {
                background-color: #252542;
                color: #ffffff;
                border: 1px solid #2d3561;
                selection-background-color: #0f3460;
            }
        """
        
    def _spin_box_style(self) -> str:
        """数字框样式"""
        return """
            QSpinBox, QDoubleSpinBox {
                background-color: #252542;
                color: #ffffff;
                border: 1px solid #2d3561;
                border-radius: 6px;
                padding: 6px;
                min-width: 60px;
            }
            QSpinBox:hover, QDoubleSpinBox:hover {
                border-color: #0f3460;
            }
        """
        
    def _line_edit_style(self) -> str:
        """输入框样式"""
        return """
            QLineEdit {
                background-color: #252542;
                color: #ffffff;
                border: 1px solid #2d3561;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QLineEdit:focus {
                border-color: #0f3460;
            }
        """
        
    def _button_style(self) -> str:
        """按钮样式"""
        return """
            QPushButton {
                background-color: #0f3460;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e94560;
            }
        """
        
    # ==================== 功能方法 ====================
    
    def _load_settings(self):
        """加载当前设置"""
        # 通用设置
        self.always_on_top.setChecked(config.window.always_on_top)
        self.opacity_slider.setValue(int(config.window.opacity * 100))
        self.auto_start.setChecked(config.general.auto_start)
        self.minimize_to_tray.setChecked(config.general.minimize_to_tray)
        self.voice_feedback.setChecked(config.general.voice_feedback)
        
        # 模型设置
        model_index = self.model_combo.findText(config.model.current)
        if model_index >= 0:
            self.model_combo.setCurrentIndex(model_index)
        self.model_scale.setValue(config.model.scale)
        self.anim_speed.setValue(config.model.animation_speed)
        
        # 语音设置
        lang_map = {
            'zh-CN': 0, 'zh-TW': 1, 'en-US': 2,
            'ja-JP': 3, 'ko-KR': 4
        }
        self.recog_lang.setCurrentIndex(lang_map.get(config.voice.recognition_lang, 0))
        
        voice_index = self.voice_combo.findData(config.voice.synthesis_voice)
        if voice_index >= 0:
            self.voice_combo.setCurrentIndex(voice_index)
        self.speech_rate.setValue(config.voice.synthesis_rate)
        self.speech_volume.setValue(int(config.voice.synthesis_volume * 100))
        
        # AI设置
        self.ollama_host.setText(config.ollama.host)
        model_index = self.ollama_model.findText(config.ollama.model)
        if model_index >= 0:
            self.ollama_model.setCurrentIndex(model_index)
        self.temperature.setValue(config.ollama.temperature)
        self.max_tokens.setValue(config.ollama.max_tokens)
        
    def _save_settings(self):
        """保存设置"""
        # 通用设置
        config.window.always_on_top = self.always_on_top.isChecked()
        config.window.opacity = self.opacity_slider.value() / 100
        config.general.auto_start = self.auto_start.isChecked()
        config.general.minimize_to_tray = self.minimize_to_tray.isChecked()
        config.general.voice_feedback = self.voice_feedback.isChecked()
        
        # 模型设置
        config.model.current = self.model_combo.currentText()
        config.model.scale = self.model_scale.value()
        config.model.animation_speed = self.anim_speed.value()
        
        # 语音设置
        lang_map = ['zh-CN', 'zh-TW', 'en-US', 'ja-JP', 'ko-KR']
        config.voice.recognition_lang = lang_map[self.recog_lang.currentIndex()]
        config.voice.synthesis_voice = self.voice_combo.currentData()
        config.voice.synthesis_rate = self.speech_rate.value()
        config.voice.synthesis_volume = self.speech_volume.value() / 100
        
        # AI设置
        config.ollama.host = self.ollama_host.text()
        config.ollama.model = self.ollama_model.currentText()
        config.ollama.temperature = self.temperature.value()
        config.ollama.max_tokens = self.max_tokens.value()
        
        # 保存到文件
        config.save()
        
        # 发送信号
        self.model_changed.emit(config.model.current)
        self.voice_changed.emit(config.voice.synthesis_voice)
        self.settings_saved.emit()
        
        # 关闭面板
        self.hide()
        
        QMessageBox.information(self, "保存成功", "设置已保存！")
        logger.info("设置已保存")
        
    def _reset_settings(self):
        """重置设置"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置所有设置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 删除配置文件
            config_file = Path(__file__).parent.parent / "config.json"
            if config_file.exists():
                config_file.unlink()
                
            QMessageBox.information(
                self,
                "重置成功",
                "设置已重置，请重启应用以应用更改。"
            )
            logger.info("设置已重置")
            
    def _browse_model(self):
        """浏览模型文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择FBX模型",
            "",
            "FBX文件 (*.fbx)"
        )
        
        if file_path:
            self.model_combo.addItem(Path(file_path).name)
            self.model_combo.setCurrentIndex(self.model_combo.count() - 1)
            
    def _test_voice(self):
        """测试语音"""
        from .voice_synthesizer import VoiceSynthesizer
        
        synthesizer = VoiceSynthesizer()
        synthesizer.set_voice(self.voice_combo.currentData())
        synthesizer.set_rate(self.speech_rate.value())
        synthesizer.set_volume(self.speech_volume.value() / 100)
        synthesizer.speak("你好，这是语音测试。")
        
    def _check_ollama(self):
        """检查Ollama连接"""
        host = self.ollama_host.text()
        
        if check_ollama_running(host):
            QMessageBox.information(self, "连接成功", "Ollama服务运行正常！")
        else:
            QMessageBox.warning(
                self,
                "连接失败",
                "无法连接到Ollama服务，请确保Ollama已启动。"
            )
