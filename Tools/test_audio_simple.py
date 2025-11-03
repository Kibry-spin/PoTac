#!/usr/bin/env python3
"""
音频播放测试脚本（使用系统工具）
无需安装额外Python库
"""

import subprocess
import sys
from pathlib import Path

# 音频目录
project_root = Path(__file__).parent.parent
assets_dir = project_root / "Assets" / "Potac-Voice"


def play_audio_aplay(audio_file):
    """使用aplay播放音频（ALSA）"""
    try:
        result = subprocess.run(
            ['aplay', '-q', str(audio_file)],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"  播放失败: {e.stderr}")
        return False
    except FileNotFoundError:
        return False


def play_audio_paplay(audio_file):
    """使用paplay播放音频（PulseAudio）"""
    try:
        result = subprocess.run(
            ['paplay', str(audio_file)],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"  播放失败: {e.stderr}")
        return False
    except FileNotFoundError:
        return False


def play_audio_ffplay(audio_file):
    """使用ffplay播放音频（FFmpeg）"""
    try:
        result = subprocess.run(
            ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', str(audio_file)],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"  播放失败: {e.stderr}")
        return False
    except FileNotFoundError:
        return False


def main():
    print("="*70)
    print("语音素材播放测试（使用系统工具）")
    print("="*70)
    print(f"\n音频目录: {assets_dir}")

    if not assets_dir.exists():
        print(f"错误: 音频目录不存在: {assets_dir}")
        sys.exit(1)

    # 获取所有音频文件
    audio_files = sorted(assets_dir.glob("*.wav"))

    if not audio_files:
        print("错误: 未找到音频文件")
        sys.exit(1)

    print(f"\n找到 {len(audio_files)} 个音频文件:")
    for i, audio_file in enumerate(audio_files, 1):
        print(f"  {i}. {audio_file.name}")

    # 确定使用哪个播放器
    print("\n检测可用的音频播放工具...")

    test_file = audio_files[0]
    play_func = None

    # 测试aplay
    print("  测试 aplay... ", end='', flush=True)
    if play_audio_aplay(test_file):
        print("✓ 可用")
        play_func = play_audio_aplay
    else:
        print("✗ 不可用")

    # 如果aplay不可用，测试paplay
    if not play_func:
        print("  测试 paplay... ", end='', flush=True)
        if play_audio_paplay(test_file):
            print("✓ 可用")
            play_func = play_audio_paplay
        else:
            print("✗ 不可用")

    # 如果前两个都不可用，测试ffplay
    if not play_func:
        print("  测试 ffplay... ", end='', flush=True)
        if play_audio_ffplay(test_file):
            print("✓ 可用")
            play_func = play_audio_ffplay
        else:
            print("✗ 不可用")

    if not play_func:
        print("\n错误: 没有可用的音频播放工具")
        sys.exit(1)

    # 播放所有音频文件
    print("\n" + "="*70)
    print("开始播放测试...")
    print("="*70)

    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n[{i}/{len(audio_files)}] 正在播放: {audio_file.name}")

        if play_func(audio_file):
            print("  ✓ 播放完成")
        else:
            print("  ✗ 播放失败")

    print("\n" + "="*70)
    print("✓ 所有音频测试完成！")
    print("="*70)


if __name__ == "__main__":
    main()
