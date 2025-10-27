#!/usr/bin/env python3
"""
视触觉传感器多设备诊断工具
测试多个相机同时连接时的状态
"""

import cv2
import sys
import time
import numpy as np
from threading import Thread, Lock


class SensorDiagnostics:
    """传感器诊断工具"""

    def __init__(self):
        self.results = {}
        self.lock = Lock()

    def test_single_device(self, device_id, duration=3):
        """
        测试单个设备

        Args:
            device_id: 设备ID
            duration: 测试时长（秒）
        """
        print(f"\n{'='*60}")
        print(f"测试设备 {device_id}")
        print(f"{'='*60}")

        result = {
            'device_id': device_id,
            'can_open': False,
            'backend': None,
            'resolution': None,
            'fps_requested': None,
            'fps_actual': None,
            'frames_captured': 0,
            'frame_failures': 0,
            'avg_frame_time': 0,
            'buffer_size': None
        }

        cap = None
        try:
            # 尝试不同的后端
            backends_to_try = [
                ('AUTO', cv2.CAP_ANY),
                ('V4L2', cv2.CAP_V4L2),
            ]

            for backend_name, backend in backends_to_try:
                print(f"\n尝试后端: {backend_name}")
                cap = cv2.VideoCapture(device_id, backend)

                if cap.isOpened():
                    print(f"  ✓ 使用 {backend_name} 后端成功打开")
                    result['backend'] = backend_name
                    result['can_open'] = True
                    break
                else:
                    print(f"  ✗ {backend_name} 后端打开失败")
                    if cap:
                        cap.release()

            if not result['can_open']:
                print(f"\n✗ 无法打开设备 {device_id}")
                return result

            # 获取设备信息
            backend_name = cap.getBackendName()
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(cap.get(cv2.CAP_PROP_FPS))

            result['backend'] = backend_name
            result['resolution'] = (width, height)
            result['fps_requested'] = fps

            print(f"\n设备信息:")
            print(f"  后端: {backend_name}")
            print(f"  分辨率: {width}x{height}")
            print(f"  FPS (请求): {fps}")

            # 尝试设置缓冲区大小
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                buffer_size = int(cap.get(cv2.CAP_PROP_BUFFERSIZE))
                result['buffer_size'] = buffer_size
                print(f"  缓冲区大小: {buffer_size}")
            except:
                print(f"  缓冲区大小: 不支持")

            # 测试帧捕获
            print(f"\n测试帧捕获 ({duration}秒)...")
            start_time = time.time()
            frame_times = []
            frames_captured = 0
            frame_failures = 0

            while time.time() - start_time < duration:
                frame_start = time.time()
                ret, frame = cap.read()
                frame_end = time.time()

                if ret and frame is not None:
                    frames_captured += 1
                    frame_times.append(frame_end - frame_start)
                else:
                    frame_failures += 1

            elapsed = time.time() - start_time
            actual_fps = frames_captured / elapsed if elapsed > 0 else 0
            avg_frame_time = np.mean(frame_times) if frame_times else 0

            result['frames_captured'] = frames_captured
            result['frame_failures'] = frame_failures
            result['fps_actual'] = actual_fps
            result['avg_frame_time'] = avg_frame_time

            print(f"\n捕获统计:")
            print(f"  成功帧数: {frames_captured}")
            print(f"  失败帧数: {frame_failures}")
            print(f"  实际FPS: {actual_fps:.2f}")
            print(f"  平均帧时间: {avg_frame_time*1000:.2f}ms")

            # 健康评估
            if frame_failures == 0 and actual_fps > fps * 0.8:
                print(f"\n✓ 设备状态: 健康")
            elif frame_failures > frames_captured * 0.1:
                print(f"\n⚠ 设备状态: 不稳定 (失败率 {frame_failures/(frames_captured+frame_failures)*100:.1f}%)")
            else:
                print(f"\n⚠ 设备状态: 一般 (FPS偏低)")

        except Exception as e:
            print(f"\n✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()

        finally:
            if cap:
                cap.release()

        return result

    def test_concurrent_devices(self, device_ids, duration=5):
        """
        测试多个设备并发访问

        Args:
            device_ids: 设备ID列表
            duration: 测试时长（秒）
        """
        print(f"\n{'='*60}")
        print(f"并发测试 {len(device_ids)} 个设备")
        print(f"设备列表: {device_ids}")
        print(f"{'='*60}")

        caps = []
        threads = []
        stats = {did: {'frames': 0, 'failures': 0} for did in device_ids}

        # 打开所有设备
        print(f"\n打开设备...")
        for device_id in device_ids:
            try:
                cap = cv2.VideoCapture(device_id, cv2.CAP_V4L2)
                if cap.isOpened():
                    # 设置小缓冲区
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    caps.append((device_id, cap))
                    print(f"  ✓ 设备 {device_id} 打开成功")
                else:
                    print(f"  ✗ 设备 {device_id} 打开失败")
            except Exception as e:
                print(f"  ✗ 设备 {device_id} 异常: {e}")

        if len(caps) != len(device_ids):
            print(f"\n⚠ 只有 {len(caps)}/{len(device_ids)} 个设备成功打开")

        # 并发读取线程
        def read_loop(device_id, cap, duration):
            start_time = time.time()
            while time.time() - start_time < duration:
                ret, frame = cap.read()
                with self.lock:
                    if ret and frame is not None:
                        stats[device_id]['frames'] += 1
                    else:
                        stats[device_id]['failures'] += 1
                time.sleep(0.001)  # 小延迟

        # 启动线程
        print(f"\n开始并发读取 ({duration}秒)...")
        start_time = time.time()

        for device_id, cap in caps:
            thread = Thread(target=read_loop, args=(device_id, cap, duration), daemon=True)
            thread.start()
            threads.append(thread)

        # 实时显示进度
        while any(t.is_alive() for t in threads):
            elapsed = time.time() - start_time
            print(f"\r进度: {elapsed:.1f}/{duration}s", end='', flush=True)
            time.sleep(0.5)

        print(f"\n\n等待线程结束...")
        for thread in threads:
            thread.join(timeout=2)

        # 显示结果
        print(f"\n{'='*60}")
        print(f"并发测试结果")
        print(f"{'='*60}")

        for device_id, cap in caps:
            frames = stats[device_id]['frames']
            failures = stats[device_id]['failures']
            total = frames + failures
            fps = frames / duration if duration > 0 else 0
            success_rate = frames / total * 100 if total > 0 else 0

            print(f"\n设备 {device_id}:")
            print(f"  成功帧数: {frames}")
            print(f"  失败帧数: {failures}")
            print(f"  成功率: {success_rate:.1f}%")
            print(f"  实际FPS: {fps:.2f}")

            if success_rate < 90:
                print(f"  ⚠ 状态: 异常 (成功率低)")
            elif fps < 20:
                print(f"  ⚠ 状态: 不稳定 (FPS低)")
            else:
                print(f"  ✓ 状态: 正常")

        # 清理
        for device_id, cap in caps:
            cap.release()

        print(f"\n{'='*60}")

        # 冲突分析
        poor_performers = [did for did, s in stats.items() if s['failures'] > s['frames'] * 0.1]
        if poor_performers:
            print(f"\n⚠ 可能存在资源冲突的设备: {poor_performers}")
        else:
            print(f"\n✓ 所有设备运行正常")


def main():
    print("视触觉传感器多设备诊断工具")
    print("="*60)

    diagnostics = SensorDiagnostics()

    # 检测可用设备
    print("\n第一步: 检测可用设备...")
    available_devices = []
    for i in range(10):
        try:
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available_devices.append(i)
                    print(f"  ✓ 发现设备: {i}")
            cap.release()
        except:
            pass

    if not available_devices:
        print("\n✗ 未发现可用设备")
        return

    print(f"\n总共发现 {len(available_devices)} 个设备: {available_devices}")

    # 单独测试每个设备
    print(f"\n第二步: 单独测试每个设备...")
    single_results = {}
    for device_id in available_devices:
        result = diagnostics.test_single_device(device_id, duration=3)
        single_results[device_id] = result
        time.sleep(0.5)  # 设备释放延迟

    # 如果有多个设备，测试并发
    if len(available_devices) >= 2:
        print(f"\n第三步: 测试并发访问...")
        # 让用户选择要测试的设备
        print(f"\n可用设备: {available_devices}")
        print(f"默认测试所有设备，或输入设备ID（用逗号分隔）：")
        user_input = input().strip()

        if user_input:
            test_devices = [int(x.strip()) for x in user_input.split(',')]
        else:
            test_devices = available_devices[:2]  # 默认测试前两个

        diagnostics.test_concurrent_devices(test_devices, duration=5)
    else:
        print(f"\n第三步: 跳过并发测试（只有一个设备）")

    # 生成诊断报告
    print(f"\n{'='*60}")
    print(f"诊断报告")
    print(f"{'='*60}")

    for device_id, result in single_results.items():
        print(f"\n设备 {device_id}:")
        if result['can_open']:
            print(f"  后端: {result['backend']}")
            print(f"  分辨率: {result['resolution']}")
            print(f"  FPS: {result['fps_actual']:.2f} (请求: {result['fps_requested']})")
            print(f"  缓冲区: {result.get('buffer_size', 'N/A')}")
        else:
            print(f"  ✗ 无法打开")


if __name__ == "__main__":
    main()
