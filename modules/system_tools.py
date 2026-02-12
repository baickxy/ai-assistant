"""
系统工具模块
提供获取系统信息的功能，如时间、位置等
"""

import logging
import platform
import datetime
import socket
import subprocess
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class SystemTools:
    """系统工具类"""

    @staticmethod
    def get_current_time(format: str = "%Y-%m-%d %H:%M:%S") -> Dict[str, Any]:
        """
        获取当前时间

        Args:
            format: 时间格式字符串，默认为 "%Y-%m-%d %H:%M:%S"

        Returns:
            包含时间信息的字典
        """
        try:
            # 获取本地当前时间（使用datetime.now()不带参数，确保使用系统本地时间）
            now = datetime.datetime.now()
            formatted_time = now.strftime(format)

            # 获取当前时间的UTC偏移
            import time as time_module
            utc_now = datetime.datetime.utcnow()
            # 计算本地时间与UTC的差值（小时）
            offset_seconds = (now - utc_now).total_seconds()
            offset_hours = offset_seconds / 3600

            return {
                "success": True,
                "time": formatted_time,
                "timestamp": now.timestamp(),
                "timezone": f"UTC{'+' if offset_hours >= 0 else ''}{offset_hours:.0f}"
            }
        except Exception as e:
            logger.error(f"获取时间失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_date() -> Dict[str, Any]:
        """
        获取当前日期

        Returns:
            包含日期信息的字典
        """
        try:
            now = datetime.datetime.now()
            return {
                "success": True,
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "weekday": now.weekday(),  # 0=Monday, 6=Sunday
                "weekday_name": now.strftime("%A"),
                "date_str": now.strftime("%Y年%m月%d日")
            }
        except Exception as e:
            logger.error(f"获取日期失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """
        获取系统信息

        Returns:
            包含系统信息的字典
        """
        try:
            return {
                "success": True,
                "system": platform.system(),
                "node": platform.node(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version()
            }
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_network_info() -> Dict[str, Any]:
        """
        获取网络信息

        Returns:
            包含网络信息的字典
        """
        try:
            hostname = socket.gethostname()
            ip_address = socket.gethostbyname(hostname)

            return {
                "success": True,
                "hostname": hostname,
                "ip_address": ip_address
            }
        except Exception as e:
            logger.error(f"获取网络信息失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_location() -> Dict[str, Any]:
        """
        获取位置信息（基于IP）

        Returns:
            包含位置信息的字典
        """
        try:
            # 使用公开的IP定位API
            import requests
            response = requests.get('http://ip-api.com/json/', timeout=5)
            data = response.json()

            if data.get('status') == 'success':
                return {
                    "success": True,
                    "country": data.get('country'),
                    "country_code": data.get('countryCode'),
                    "region": data.get('regionName'),
                    "city": data.get('city'),
                    "latitude": data.get('lat'),
                    "longitude": data.get('lon'),
                    "timezone": data.get('timezone'),
                    "isp": data.get('isp')
                }
            else:
                return {
                    "success": False,
                    "error": "无法获取位置信息"
                }
        except Exception as e:
            logger.error(f"获取位置信息失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_weather(location: Optional[str] = None) -> Dict[str, Any]:
        """
        获取天气信息

        Args:
            location: 位置，如"北京"或"Beijing"。如果为None，则使用IP定位

        Returns:
            包含天气信息的字典
        """
        try:
            import requests

            # 如果没有指定位置，先获取位置
            if not location:
                loc_result = SystemTools.get_location()
                if loc_result.get('success'):
                    location = f"{loc_result.get('city')},{loc_result.get('country')}"
                else:
                    return {
                        "success": False,
                        "error": "无法确定位置"
                    }

            # 使用免费的天气API
            url = f"http://api.openweathermap.org/data/2.5/weather"
            params = {
                'q': location,
                'appid': 'demo',  # 使用demo密钥，实际使用时需要替换
                'units': 'metric',
                'lang': 'zh_cn'
            }

            response = requests.get(url, params=params, timeout=5)
            data = response.json()

            if response.status_code == 200:
                return {
                    "success": True,
                    "location": location,
                    "temperature": data.get('main', {}).get('temp'),
                    "description": data.get('weather', [{}])[0].get('description'),
                    "humidity": data.get('main', {}).get('humidity'),
                    "wind_speed": data.get('wind', {}).get('speed')
                }
            else:
                return {
                    "success": False,
                    "error": data.get('message', '获取天气信息失败')
                }
        except Exception as e:
            logger.error(f"获取天气信息失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def execute_command(command: str, timeout: int = 10) -> Dict[str, Any]:
        """
        执行系统命令（谨慎使用）

        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）

        Returns:
            包含执行结果的字典
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                "success": True,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            logger.error(f"命令执行超时: {command}")
            return {
                "success": False,
                "error": "命令执行超时"
            }
        except Exception as e:
            logger.error(f"执行命令失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def read_file(file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """
        读取文件内容

        Args:
            file_path: 文件路径
            encoding: 文件编码，默认为utf-8

        Returns:
            包含文件内容的字典
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"文件不存在: {file_path}"
                }

            # 检查是否为文件
            if not os.path.isfile(file_path):
                return {
                    "success": False,
                    "error": f"路径不是文件: {file_path}"
                }

            # 读取文件内容
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()

            return {
                "success": True,
                "file_path": file_path,
                "content": content,
                "size": os.path.getsize(file_path)
            }
        except Exception as e:
            logger.error(f"读取文件失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def write_file(file_path: str, content: str, encoding: str = 'utf-8', mode: str = 'w') -> Dict[str, Any]:
        """
        写入文件内容

        Args:
            file_path: 文件路径
            content: 要写入的内容
            encoding: 文件编码，默认为utf-8
            mode: 写入模式，'w'为覆盖，'a'为追加

        Returns:
            包含操作结果的字典
        """
        try:
            # 检查是否是C盘路径
            if file_path.upper().startswith('C:\\'):
                return {
                    "success": False,
                    "error": f"需要用户确认: 正在尝试写入C盘文件: {file_path}",
                    "requires_confirmation": True,
                    "file_path": file_path,
                    "content": content
                }

            # 获取目录路径和文件名
            dir_path = os.path.dirname(file_path)
            file_name = os.path.basename(file_path)

            # 如果没有提供扩展名，自动添加.txt
            if not os.path.splitext(file_name)[1]:
                file_path = file_path + '.txt'

            # 创建目录（如果不存在）
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

            # 写入文件
            with open(file_path, mode, encoding=encoding) as f:
                f.write(content)

            return {
                "success": True,
                "file_path": file_path,
                "size": os.path.getsize(file_path)
            }
        except Exception as e:
            logger.error(f"写入文件失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def delete_file(file_path: str) -> Dict[str, Any]:
        """
        删除文件

        Args:
            file_path: 文件路径

        Returns:
            包含操作结果的字典
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"文件不存在: {file_path}"
                }

            # 检查是否是C盘路径
            if file_path.upper().startswith('C:\\'):
                return {
                    "success": False,
                    "error": f"需要用户确认: 正在尝试删除C盘文件: {file_path}",
                    "requires_confirmation": True,
                    "file_path": file_path
                }

            # 删除文件
            os.remove(file_path)

            return {
                "success": True,
                "file_path": file_path
            }
        except Exception as e:
            logger.error(f"删除文件失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def list_directory(dir_path: str, show_hidden: bool = False) -> Dict[str, Any]:
        """
        列出目录内容

        Args:
            dir_path: 目录路径
            show_hidden: 是否显示隐藏文件

        Returns:
            包含目录内容的字典
        """
        try:
            # 检查目录是否存在
            if not os.path.exists(dir_path):
                return {
                    "success": False,
                    "error": f"目录不存在: {dir_path}"
                }

            # 检查是否是目录
            if not os.path.isdir(dir_path):
                return {
                    "success": False,
                    "error": f"路径不是目录: {dir_path}"
                }

            # 获取目录内容
            items = []
            for item in os.listdir(dir_path):
                # 跳过隐藏文件（如果show_hidden为False）
                if not show_hidden and item.startswith('.'):
                    continue

                item_path = os.path.join(dir_path, item)
                item_info = {
                    "name": item,
                    "path": item_path,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "size": os.path.getsize(item_path) if os.path.isfile(item_path) else 0
                }
                items.append(item_info)

            return {
                "success": True,
                "dir_path": dir_path,
                "items": items,
                "count": len(items)
            }
        except Exception as e:
            logger.error(f"列出目录内容失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# 工具函数映射
TOOL_FUNCTIONS = {
    "get_time": SystemTools.get_current_time,
    "get_date": SystemTools.get_date,
    "get_system_info": SystemTools.get_system_info,
    "get_network_info": SystemTools.get_network_info,
    "get_location": SystemTools.get_location,
    "get_weather": SystemTools.get_weather,
    "execute_command": SystemTools.execute_command,
    "read_file": SystemTools.read_file,
    "write_file": SystemTools.write_file,
    "delete_file": SystemTools.delete_file,
    "list_directory": SystemTools.list_directory
}
