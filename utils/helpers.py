"""
辅助工具函数
"""

import os
import re
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def get_file_hash(filepath: str) -> str:
    """
    计算文件MD5哈希
    
    Args:
        filepath: 文件路径
        
    Returns:
        MD5哈希值
    """
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    # 移除非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # 移除控制字符
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    # 限制长度
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
    return filename.strip()


def ensure_dir(path: Path) -> Path:
    """
    确保目录存在
    
    Args:
        path: 目录路径
        
    Returns:
        目录路径
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_duration(seconds: float) -> str:
    """
    格式化时长
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化后的字符串 (如: 1:23)
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 后缀
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-len(suffix)] + suffix


def safe_get(dictionary: Dict, key: str, default: Any = None) -> Any:
    """
    安全获取字典值
    
    Args:
        dictionary: 字典
        key: 键
        default: 默认值
        
    Returns:
        值或默认值
    """
    try:
        return dictionary.get(key, default)
    except (AttributeError, TypeError):
        return default


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """
    将列表分块
    
    Args:
        lst: 列表
        chunk_size: 块大小
        
    Returns:
        分块后的列表
    """
    return [lst[i:i+chunk_size] for i in range(0, len(lst), chunk_size)]


def find_files(
    directory: Path, 
    pattern: str = "*", 
    recursive: bool = True
) -> List[Path]:
    """
    查找文件
    
    Args:
        directory: 目录
        pattern: 匹配模式
        recursive: 是否递归
        
    Returns:
        文件路径列表
    """
    if recursive:
        return list(directory.rglob(pattern))
    else:
        return list(directory.glob(pattern))


def get_available_voices() -> List[Dict[str, str]]:
    """
    获取可用的语音列表
    
    Returns:
        语音列表，每项包含id和name
    """
    # 系统默认语音
    voices = [
        {"id": "default", "name": "系统默认"},
        {"id": "chinese", "name": "中文"},
        {"id": "english", "name": "英文"},
    ]
    
    # Edge TTS 语音 (需要网络)
    edge_voices = [
        {"id": "zh-CN-XiaoxiaoNeural", "name": "晓晓 (女声)"},
        {"id": "zh-CN-XiaoyiNeural", "name": "晓伊 (女声)"},
        {"id": "zh-CN-YunjianNeural", "name": "云健 (男声)"},
        {"id": "zh-CN-YunxiNeural", "name": "云希 (男声)"},
        {"id": "zh-CN-YunxiaNeural", "name": "云夏 (男声)"},
        {"id": "zh-CN-YunyangNeural", "name": "云扬 (男声)"},
        {"id": "zh-CN-liaoning-XiaobeiNeural", "name": "晓北 (东北话女声)"},
        {"id": "zh-CN-shaanxi-XiaoniNeural", "name": "晓妮 (陕西话女声)"},
        {"id": "zh-HK-HiuMaanNeural", "name": "晓曼 (粤语女声)"},
        {"id": "zh-TW-HsiaoChenNeural", "name": "晓晨 (台湾话女声)"},
    ]
    
    return voices + edge_voices


def get_available_ollama_models() -> List[str]:
    """
    获取可用的Ollama模型列表
    
    Returns:
        模型名称列表
    """
    try:
        import requests
        from config import config
        
        response = requests.get(
            f"{config.ollama.host}/api/tags",
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            models = [model['name'] for model in data.get('models', [])]
            return models if models else ["llama3.2"]
            
    except Exception as e:
        logger.warning(f"获取Ollama模型列表失败: {e}")
        
    # 默认模型
    return ["llama3.2", "llama3.1", "qwen2.5", "phi4", "mistral"]


def check_ollama_running(host: str = "http://localhost:11434") -> bool:
    """
    检查Ollama是否运行
    
    Args:
        host: Ollama服务地址
        
    Returns:
        是否运行
    """
    try:
        import requests
        response = requests.get(f"{host}/api/tags", timeout=3)
        return response.status_code == 200
    except Exception:
        return False


def create_default_fbx_model(output_path: Path):
    """
    创建默认的FBX模型文件 (简单的立方体)
    
    注意: 这是一个占位函数，实际应该提供预制的FBX文件
    """
    logger.warning("默认FBX模型需要手动提供")
    logger.info(f"请将FBX模型文件放置在: {output_path}")
