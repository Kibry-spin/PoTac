#!/usr/bin/env python3
"""
简化版Rerun可视化 - 仅显示相机和触觉传感器图像
按时间戳对齐显示，不包含ArUco距离
"""

import rerun as rr
import rerun.blueprint as rrb
import cv2
import numpy as np
import pickle
import json
from pathlib import Path
import argparse
import sys


class SimpleSessionVisualizer:
    """简化的Session可视化器 - 仅显示图像"""

    def __init__(self, session_dir):
        self.session_dir = Path(session_dir)
        if not self.session_dir.exists():
            raise ValueError(f"Session目录不存在: {self.session_dir}")

        print(f"加载Session: {self.session_dir.name}")

        # 加载PKL数据
        pkl_path = self.session_dir / "aligned_data.pkl"
        if not pkl_path.exists():
            raise ValueError(f"PKL文件不存在: {pkl_path}")

        with open(pkl_path, 'rb') as f:
            data = pickle.load(f)

        self.metadata = data.get('metadata', {})
        self.aligned_data = data.get('data', {})
        self.timestamps = self.aligned_data.get('timestamps', [])

        # 获取起始时间戳（用于时间对齐）
        start_time = self.metadata.get('start_time', 0.0)
        if hasattr(start_time, 'timestamp'):
            self.start_timestamp = start_time.timestamp()
        else:
            self.start_timestamp = float(start_time) if start_time else 0.0

        # 传感器信息
        self.sensors = self.metadata.get('sensors', {})

        # 加载每个传感器的metadata
        self.sensor_metadata = {}
        for sensor_id, sensor_info in self.sensors.items():
            frames_dir = sensor_info.get('frames_dir', sensor_id)
            metadata_file = self.session_dir / frames_dir / 'frames_metadata.json'

            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    self.sensor_metadata[sensor_id] = json.load(f)
                    frame_count = len(self.sensor_metadata[sensor_id].get('frames', []))
                    print(f"  ✓ {sensor_id}: {frame_count} 帧")
            else:
                print(f"  ⚠ {sensor_id}: metadata文件不存在")
                self.sensor_metadata[sensor_id] = {'frames': []}

        print(f"\n✓ 加载完成")
        print(f"  时间戳数量: {len(self.timestamps)}")
        print(f"  传感器数量: {len(self.sensors)}")
        print(f"  起始时间: {self.start_timestamp:.3f}")
        print(f"  时间范围: {self.timestamps[0]:.3f}s ~ {self.timestamps[-1]:.3f}s")

    def visualize(self):
        """运行可视化"""
        # 初始化Rerun
        rr.init(f"PoTac - {self.metadata.get('session_name', 'Session')}", spawn=True)

        # 创建布局
        blueprint = self._create_blueprint()
        rr.send_blueprint(blueprint)

        # 记录session信息
        self._log_session_info()

        print(f"\n开始可视化...")

        # 遍历每个时间戳
        for i, timestamp in enumerate(self.timestamps):
            # 设置时间
            rr.set_time("timestamp", timestamp=timestamp)
            rr.set_time("frame", sequence=i)

            # 加载并记录所有传感器图像
            self._log_all_sensor_images(i, timestamp)

            # 进度显示
            if (i + 1) % 10 == 0 or i == len(self.timestamps) - 1:
                print(f"  进度: {i+1}/{len(self.timestamps)} ({(i+1)/len(self.timestamps)*100:.1f}%)")

        print("\n✓ 可视化完成！")
        print("\n使用方法:")
        print("  - 拖动时间轴滑块浏览不同时间点")
        print("  - 点击图像放大查看")
        print("  - 播放/暂停按钮控制自动播放")

    def _create_blueprint(self):
        """创建布局蓝图"""
        sensor_views = []

        # 为每个传感器创建2D视图
        for sensor_id in sorted(self.sensors.keys()):
            sensor_views.append(
                rrb.Spatial2DView(
                    name=sensor_id,
                    origin=f"/sensors/{sensor_id}"
                )
            )

        # 根据传感器数量调整布局
        if len(sensor_views) == 0:
            return rrb.Blueprint(rrb.Horizontal())
        elif len(sensor_views) == 1:
            return rrb.Blueprint(sensor_views[0])
        elif len(sensor_views) == 2:
            return rrb.Blueprint(
                rrb.Horizontal(*sensor_views)
            )
        elif len(sensor_views) == 3:
            # 3个传感器：上方2个VT，下方1个OAK
            return rrb.Blueprint(
                rrb.Vertical(
                    rrb.Horizontal(sensor_views[1], sensor_views[2]),  # vt传感器
                    sensor_views[0],  # oak相机
                    row_shares=[1, 1]
                )
            )
        else:
            # 多个传感器：网格布局
            return rrb.Blueprint(
                rrb.Grid(*sensor_views)
            )

    def _log_session_info(self):
        """记录session信息"""
        info_text = f"# {self.metadata.get('session_name', 'Session')}\n\n"
        info_text += f"**时长**: {self.timestamps[-1] - self.timestamps[0]:.2f}秒  \n"
        info_text += f"**帧数**: {len(self.timestamps)}  \n\n"
        info_text += f"## 传感器\n\n"

        for sensor_id, sensor_info in self.sensors.items():
            sensor_name = sensor_info.get('sensor_name', sensor_id)
            frame_count = len(self.sensor_metadata.get(sensor_id, {}).get('frames', []))
            info_text += f"- **{sensor_id}** ({sensor_name}): {frame_count} 帧\n"

        rr.log("session_info", rr.TextDocument(info_text, media_type=rr.MediaType.MARKDOWN))

    def _log_all_sensor_images(self, frame_idx, timestamp):
        """记录所有传感器的图像"""
        # 将相对时间戳转换为绝对时间戳
        absolute_timestamp = timestamp + self.start_timestamp

        for sensor_id, sensor_info in self.sensors.items():
            frames_dir = sensor_info.get('frames_dir', sensor_id)
            sensor_dir = self.session_dir / frames_dir

            # 获取传感器的frames列表
            sensor_meta = self.sensor_metadata.get(sensor_id, {})
            frames = sensor_meta.get('frames', [])

            if not frames:
                continue

            # 找到最接近的帧
            frame_info = self._find_closest_frame(frames, absolute_timestamp)

            if frame_info is None:
                # 如果找不到匹配帧，记录为空
                rr.log(f"sensors/{sensor_id}/image", rr.Clear(recursive=False))
                continue

            # 读取图像
            image_path = sensor_dir / frame_info['filename']

            if not image_path.exists():
                continue

            image = cv2.imread(str(image_path))
            if image is None:
                continue

            # BGR转RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # 记录图像
            rr.log(f"sensors/{sensor_id}/image", rr.Image(image_rgb))

            # 记录帧信息（文本标注）
            info = f"Frame {frame_info['frame_num']}\n"
            info += f"Time: {timestamp:.3f}s\n"
            info += f"Size: {image.shape[1]}×{image.shape[0]}"
            rr.log(f"sensors/{sensor_id}/info", rr.TextLog(info))

    def _find_closest_frame(self, frames, target_timestamp, tolerance=0.1):
        """
        找到最接近目标时间戳的帧

        Args:
            frames: 帧列表
            target_timestamp: 目标时间戳（绝对时间）
            tolerance: 容差（秒）

        Returns:
            最接近的帧，如果超出容差则返回None
        """
        if not frames:
            return None

        min_diff = float('inf')
        closest_frame = None

        for frame in frames:
            diff = abs(frame['timestamp'] - target_timestamp)
            if diff < min_diff:
                min_diff = diff
                closest_frame = frame

        # 检查是否在容差范围内
        if min_diff <= tolerance:
            return closest_frame

        return None


def main():
    parser = argparse.ArgumentParser(
        description='简化版Rerun可视化 - 仅显示传感器图像',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 可视化指定session
  python visualize_simple.py data/session_20251028_135619

  # 可视化最新session
  python visualize_simple.py
        """
    )

    parser.add_argument('session_dir', nargs='?', help='Session目录路径')

    args = parser.parse_args()

    # 处理session_dir参数
    if args.session_dir is None:
        print("查找最新session...")
        data_dir = Path("./data")
        if data_dir.exists():
            sessions = sorted(data_dir.glob("session_*"),
                            key=lambda x: x.stat().st_mtime, reverse=True)
            if sessions:
                session_dir = sessions[0]
                print(f"使用最新session: {session_dir.name}\n")
            else:
                print("错误: 未找到任何session")
                sys.exit(1)
        else:
            print("错误: data目录不存在")
            sys.exit(1)
    else:
        session_dir = Path(args.session_dir)

    if not session_dir.exists():
        print(f"错误: Session目录不存在: {session_dir}")
        sys.exit(1)

    print("="*70)
    print("简化版Rerun可视化 - 多传感器图像")
    print("="*70)
    print()

    try:
        visualizer = SimpleSessionVisualizer(session_dir)
        visualizer.visualize()

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
