#!/usr/bin/env python3
"""
音频播放测试脚本
测试语音素材播放功能
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
assets_dir = project_root / "Assets" / "Potac-Voice"

def test_pygame():
    """使用pygame播放音频"""
    try:
        import pygame

        print("测试方法: pygame")
        pygame.mixer.init()

        # 列出所有音频文件
        audio_files = sorted(assets_dir.glob("*.wav"))

        print(f"\n找到 {len(audio_files)} 个音频文件:")
        for i, audio_file in enumerate(audio_files, 1):
            print(f"  {i}. {audio_file.name}")

        # 逐个播放
        print("\n开始播放测试...")
        for i, audio_file in enumerate(audio_files, 1):
            print(f"\n[{i}/{len(audio_files)}] 正在播放: {audio_file.name}")

            pygame.mixer.music.load(str(audio_file))
            pygame.mixer.music.play()

            # 等待播放完成
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)

            print("  ✓ 播放完成")

        pygame.mixer.quit()
        print("\n✓ 所有音频测试完成！")
        return True

    except ImportError:
        print("pygame未安装")
        return False
    except Exception as e:
        print(f"pygame播放失败: {e}")
        return False


def test_sounddevice():
    """使用sounddevice播放音频"""
    try:
        import sounddevice as sd
        import soundfile as sf

        print("测试方法: sounddevice")

        # 列出所有音频文件
        audio_files = sorted(assets_dir.glob("*.wav"))

        print(f"\n找到 {len(audio_files)} 个音频文件:")
        for i, audio_file in enumerate(audio_files, 1):
            print(f"  {i}. {audio_file.name}")

        # 逐个播放
        print("\n开始播放测试...")
        for i, audio_file in enumerate(audio_files, 1):
            print(f"\n[{i}/{len(audio_files)}] 正在播放: {audio_file.name}")

            # 读取音频文件
            data, samplerate = sf.read(str(audio_file))

            # 播放
            sd.play(data, samplerate)
            sd.wait()  # 等待播放完成

            print("  ✓ 播放完成")

        print("\n✓ 所有音频测试完成！")
        return True

    except ImportError:
        print("sounddevice或soundfile未安装")
        return False
    except Exception as e:
        print(f"sounddevice播放失败: {e}")
        return False


def test_playsound():
    """使用playsound播放音频（最简单）"""
    try:
        from playsound import playsound

        print("测试方法: playsound")

        # 列出所有音频文件
        audio_files = sorted(assets_dir.glob("*.wav"))

        print(f"\n找到 {len(audio_files)} 个音频文件:")
        for i, audio_file in enumerate(audio_files, 1):
            print(f"  {i}. {audio_file.name}")

        # 逐个播放
        print("\n开始播放测试...")
        for i, audio_file in enumerate(audio_files, 1):
            print(f"\n[{i}/{len(audio_files)}] 正在播放: {audio_file.name}")

            playsound(str(audio_file))

            print("  ✓ 播放完成")

        print("\n✓ 所有音频测试完成！")
        return True

    except ImportError:
        print("playsound未安装")
        return False
    except Exception as e:
        print(f"playsound播放失败: {e}")
        return False


def main():
    print("="*70)
    print("语音素材播放测试")
    print("="*70)
    print(f"\n音频目录: {assets_dir}")

    if not assets_dir.exists():
        print(f"错误: 音频目录不存在: {assets_dir}")
        sys.exit(1)

    print("\n尝试不同的音频播放方法...\n")

    # 按优先级尝试不同方法
    methods = [
        ("pygame", test_pygame),
        ("sounddevice", test_sounddevice),
        ("playsound", test_playsound),
    ]

    for method_name, test_func in methods:
        print(f"\n{'='*70}")
        try:
            if test_func():
                print(f"\n✓ {method_name} 测试成功！")
                print(f"\n推荐使用: {method_name}")
                break
        except Exception as e:
            print(f"✗ {method_name} 测试失败: {e}")
            continue
    else:
        print("\n所有方法都失败了。请安装以下任一库:")
        print("  pip install pygame")
        print("  pip install sounddevice soundfile")
        print("  pip install playsound")
        sys.exit(1)


if __name__ == "__main__":
    main()
