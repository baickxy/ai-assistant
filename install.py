"""
安装脚本
安装AI助手桌面应用所需的依赖
"""

import subprocess
import sys
import os
import platform
from pathlib import Path


def print_header(text):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_step(step, total, text):
    """打印步骤"""
    print(f"[{step}/{total}] {text}")


def run_command(command, description=""):
    """运行命令"""
    if description:
        print(f"  {description}...")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"  ✓ 成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ 失败: {e}")
        if e.stderr:
            print(f"  错误信息: {e.stderr}")
        return False


def check_python_version():
    """检查Python版本"""
    print_step(1, 6, "检查Python版本")

    version = sys.version_info
    print(f"  Python版本: {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("  ✗ 需要Python 3.10或更高版本")
        return False

    print("  ✓ Python版本符合要求")
    return True


def install_system_dependencies():
    """安装系统依赖"""
    print_step(2, 6, "安装系统依赖")

    system = platform.system()

    if system == "Windows":
        print("  Windows系统，跳过系统依赖安装")
        print("  注意: 某些功能可能需要Visual C++ Redistributable")
        return True

    elif system == "Darwin":  # macOS
        print("  macOS系统")

        # 检查Homebrew
        if run_command("which brew", "检查Homebrew"):
            # 安装PortAudio (PyAudio依赖)
            run_command("brew install portaudio", "安装PortAudio")
            return True
        else:
            print("  ✗ 未安装Homebrew，请先安装Homebrew")
            return False

    elif system == "Linux":
        print("  Linux系统")

        # 检测发行版
        if os.path.exists("/etc/debian_version"):
            # Debian/Ubuntu
            deps = [
                "python3-dev",
                "portaudio19-dev",
                "libasound2-dev",
                "libgl1-mesa-dev",
                "libglib2.0-0"
            ]

            cmd = f"sudo apt-get update && sudo apt-get install -y {' '.join(deps)}"
            return run_command(cmd, "安装系统依赖包")

        elif os.path.exists("/etc/redhat-release"):
            # RedHat/CentOS/Fedora
            deps = [
                "python3-devel",
                "portaudio-devel",
                "alsa-lib-devel",
                "mesa-libGL-devel"
            ]

            cmd = f"sudo yum install -y {' '.join(deps)}"
            return run_command(cmd, "安装系统依赖包")

        else:
            print("  ⚠ 未知的Linux发行版，请手动安装依赖")
            return True

    return True


def install_python_packages():
    """安装Python包"""
    print_step(3, 6, "安装Python包")

    # 升级pip
    run_command(f"{sys.executable} -m pip install --upgrade pip", "升级pip")

    # 安装requirements.txt中的包
    req_file = Path(__file__).parent / "requirements.txt"

    if req_file.exists():
        return run_command(
            f"{sys.executable} -m pip install -r {req_file}",
            "安装依赖包"
        )
    else:
        print("  ✗ 未找到requirements.txt文件")
        return False


def install_optional_packages():
    """安装可选包"""
    print_step(4, 6, "安装可选包")

    # Edge TTS (更好的语音合成)
    run_command(
        f"{sys.executable} -m pip install edge-tts",
        "安装Edge TTS (在线语音合成)"
    )

    # Vosk (离线语音识别)
    run_command(
        f"{sys.executable} -m pip install vosk",
        "安装Vosk (离线语音识别)"
    )

    return True


def create_directories():
    """创建必要的目录"""
    print_step(5, 6, "创建目录结构")

    base_dir = Path(__file__).parent

    directories = [
        "assets/models",
        "assets/voices",
        "assets/icons",
        "logs"
    ]

    for dir_path in directories:
        full_path = base_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✓ {dir_path}")

    return True


def check_ollama():
    """检查Ollama安装"""
    print_step(6, 6, "检查Ollama")

    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=3)

        if response.status_code == 200:
            print("  ✓ Ollama服务运行中")

            # 显示可用模型
            data = response.json()
            models = [m['name'] for m in data.get('models', [])]

            if models:
                print(f"  可用模型: {', '.join(models)}")
            else:
                print("  ⚠ 未找到任何模型，请运行: ollama pull llama3.2")

            return True

    except Exception:
        pass

    print("  ⚠ Ollama未运行或未安装")
    print("  请访问 https://ollama.com 下载并安装Ollama")
    print("  安装后运行: ollama pull llama3.2")

    return True  # 不阻止安装


def create_launcher():
    """创建启动器"""
    print_step(0, 6, "创建启动器")

    base_dir = Path(__file__).parent
    python_exe = sys.executable  # 补充定义python_exe变量，避免未定义错误

    system = platform.system()

    if system == "Windows":
        # 创建Windows批处理文件
        bat_content = f"""@echo off
cd /d "{base_dir}"
"{python_exe}" main.py
pause
"""
        bat_path = base_dir / "启动AI助手.bat"
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)
        print(f"  ✓ 创建启动器: {bat_path}")

        # 创建VBS脚本 (无控制台窗口)
        # 修复引号转义：Python中用单引号包裹VBS字符串，内部双引号直接写
        vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "{python_exe}" "{base_dir / 'main.py'}", 0, False
Set WshShell = Nothing
'''
        vbs_path = base_dir / "启动AI助手(后台).vbs"
        with open(vbs_path, 'w', encoding='utf-8') as f:
            f.write(vbs_content)
        print(f"  ✓ 创建后台启动器: {vbs_path}")

    elif system == "Darwin":  # macOS
        # 创建shell脚本
        sh_content = f"""#!/bin/bash
cd "{base_dir}"
python3 main.py
"""
        sh_path = base_dir / "start.sh"
        with open(sh_path, 'w', encoding='utf-8') as f:
            f.write(sh_content)
        os.chmod(sh_path, 0o755)
        print(f"  ✓ 创建启动器: {sh_path}")

    elif system == "Linux":
        # 创建shell脚本
        sh_content = f"""#!/bin/bash
cd "{base_dir}"
python3 main.py
"""
        sh_path = base_dir / "start.sh"
        with open(sh_path, 'w', encoding='utf-8') as f:
            f.write(sh_content)
        os.chmod(sh_path, 0o755)
        print(f"  ✓ 创建启动器: {sh_path}")

        # 创建.desktop文件
        desktop_content = f"""[Desktop Entry]
Name=AI助手
Comment=AI Assistant Desktop App
Exec=python3 {base_dir / 'main.py'}
Icon={base_dir / 'assets/icons/icon.png'}
Type=Application
Categories=Utility;
"""
        desktop_path = base_dir / "AI助手.desktop"
        with open(desktop_path, 'w', encoding='utf-8') as f:
            f.write(desktop_content)
        os.chmod(desktop_path, 0o755)
        print(f"  ✓ 创建桌面入口: {desktop_path}")


def main():
    print_header("AI助手桌面应用 - 安装程序")

    print("开始安装...\n")

    # 创建启动器
    create_launcher()

    # 执行安装步骤
    steps = [
        ("检查Python版本", check_python_version),
        ("安装系统依赖", install_system_dependencies),
        ("安装Python包", install_python_packages),
        ("安装可选包", install_optional_packages),
        ("创建目录结构", create_directories),
        ("检查Ollama", check_ollama),
    ]

    results = []
    for name, func in steps:
        try:
            result = func()
            results.append((name, result))
        except Exception as e:
            print(f"  ✗ 错误: {e}")
            results.append((name, False))
        print()

    # 打印总结
    print_header("安装总结")

    for name, result in results:
        status = "✓ 成功" if result else "✗ 失败"
        print(f"  {status} - {name}")

    print("\n" + "=" * 60)

    if all(r for _, r in results):
        print("  安装完成！")
        print("\n  启动方式:")
        print("  1. 双击启动脚本")
        print("  2. 或运行: python main.py")
    else:
        print("  安装过程中出现错误，请检查上面的输出信息")
        print("  某些功能可能无法正常使用")

    print("=" * 60 + "\n")

    input("按Enter键退出...")


if __name__ == "__main__":
    main()