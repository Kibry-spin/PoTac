#!/usr/bin/env python3
"""
语音管理器测试脚本
模拟完整的录制流程，测试所有语音提示
"""

import sys
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from utils.voice_manager import VoiceManager


def test_voice_manager():
    """测试VoiceManager的所有功能"""

    print("="*70)
    print("语音管理器功能测试")
    print("="*70)
    print()

    # 初始化VoiceManager
    print("初始化 VoiceManager...")
    voice_manager = VoiceManager()

    if not voice_manager.enabled:
        print("❌ VoiceManager未启用（可能是语音文件缺失或playsound未安装）")
        sys.exit(1)

    print("✓ VoiceManager 初始化成功")
    print(f"  语音素材目录: {voice_manager.assets_dir}")
    print()

    # 模拟录制流程
    print("="*70)
    print("模拟完整录制流程")
    print("="*70)
    print()

    # 1. 等待距离靠近（IDLE -> ARMED）
    print("[1/4] 等待距离靠近...")
    print("      (模拟：距离从100mm -> 45mm)")
    time.sleep(1)

    # 2. 开始录制
    print("\n[2/4] 距离达到阈值，开始录制...")
    print("      播放: StartRecording.wav")
    voice_manager.start_recording(blocking=True)
    print("      ✓ 语音播放完成")
    print("      (模拟录制中...)")
    time.sleep(2)

    # 3. 停止录制
    print("\n[3/4] 距离超出阈值，停止录制...")
    print("      播放: StopRecording.wav")
    voice_manager.stop_recording(blocking=True)
    print("      ✓ 语音播放完成")
    print("      (模拟数据处理中...)")
    time.sleep(1)

    # 4. 保存数据
    print("\n[4/4] 正在保存和处理数据...")
    print("      播放: Saving and processing recorded data. Please wait..wav")
    voice_manager.saving_data(blocking=True)
    print("      ✓ 语音播放完成")
    print("      (模拟数据保存中...)")
    time.sleep(2)

    # 5. 保存成功
    print("\n[5/5] 数据保存成功...")
    print("      播放: Save success! Ready for next record..wav")
    voice_manager.save_success(blocking=True)
    print("      ✓ 语音播放完成")

    print()
    print("="*70)
    print("✓ 所有语音提示测试完成！")
    print("="*70)
    print()

    # 测试非阻塞模式
    print("测试非阻塞播放模式...")
    print("  启动非阻塞播放...")
    voice_manager.start_recording(blocking=False)
    print("  ✓ 播放已启动（后台运行）")
    print("  主线程可以继续执行其他任务...")
    time.sleep(0.5)
    print("  等待播放完成...")
    voice_manager.wait()
    print("  ✓ 播放完成")
    print()

    print("="*70)
    print("✓ 所有测试通过！")
    print("="*70)


def test_individual_prompts():
    """测试单个语音提示"""
    voice_manager = VoiceManager()

    if not voice_manager.enabled:
        print("VoiceManager未启用")
        return

    print("\n测试单个语音提示：\n")

    prompts = [
        ('start_recording', '开始录制'),
        ('stop_recording', '停止录制'),
        ('saving_data', '正在保存数据'),
        ('save_success', '保存成功'),
    ]

    for key, desc in prompts:
        print(f"播放: {desc} ({key})")
        voice_manager.play(key, blocking=True)
        print("  ✓ 完成\n")
        time.sleep(0.5)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='测试VoiceManager语音提示功能')
    parser.add_argument('--mode', choices=['full', 'individual'], default='full',
                      help='测试模式: full=完整流程, individual=单个提示')

    args = parser.parse_args()

    try:
        if args.mode == 'full':
            test_voice_manager()
        else:
            test_individual_prompts()

    except KeyboardInterrupt:
        print("\n\n测试被中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
