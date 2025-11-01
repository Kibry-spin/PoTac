#!/usr/bin/env python3
"""
Rerun可视化 - 支持离线ArUco处理后的数据
显示传感器图像 + ArUco距离曲线（跳过检测失败的数据）
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


class SessionVisualizerWithAruco:
    """Session可视化器 - 支持ArUco距离显示"""

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

        # 检测时间戳类型（相对 vs 绝对）
        start_time = self.metadata.get('start_time', 0.0)
        if hasattr(start_time, 'timestamp'):
            self.start_timestamp = start_time.timestamp()
        else:
            self.start_timestamp = float(start_time) if start_time else 0.0

        # 判断timestamps是相对还是绝对时间戳
        # 如果第一个timestamp < 1000000000，认为是相对时间戳
        if len(self.timestamps) > 0:
            if self.timestamps[0] < 1000000000:
                self.use_relative_timestamps = True
                print(f"  检测到相对时间戳")
            else:
                self.use_relative_timestamps = False
                print(f"  检测到绝对时间戳")
        else:
            self.use_relative_timestamps = True

        # 传感器信息
        self.sensors = self.metadata.get('sensors', {})

        # ArUco数据
        self.aruco_data = self.aligned_data.get('aruco', {})
        self.has_aruco = bool(self.aruco_data)

        # 加载传感器metadata
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

        if self.has_aruco:
            dist_abs = self.aruco_data.get('distance_absolute', [])
            valid_count = np.sum(~np.isnan(dist_abs))
            print(f"  ArUco数据: {valid_count}/{len(dist_abs)} 有效")

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
            # 如果是相对时间戳，使用相对时间
            # 如果是绝对时间戳，转换为相对时间
            if self.use_relative_timestamps:
                relative_time = timestamp
            else:
                relative_time = timestamp - self.start_timestamp

            rr.set_time("timestamp", timestamp=relative_time)
            rr.set_time("frame", sequence=i)

            # 记录传感器图像
            self._log_sensor_images(i, timestamp)

            # 记录ArUco数据
            if self.has_aruco:
                self._log_aruco_data(i)

            # 进度显示
            if (i + 1) % 20 == 0 or i == len(self.timestamps) - 1:
                print(f"  进度: {i+1}/{len(self.timestamps)} ({(i+1)/len(self.timestamps)*100:.1f}%)")

        print("\n✓ 可视化完成！")
        print("\n使用方法:")
        print("  - 拖动时间轴滑块浏览不同时间点")
        print("  - 点击图像放大查看")
        print("  - 查看ArUco距离曲线变化")

    def _create_blueprint(self):
        """创建布局蓝图"""
        sensor_views = []

        # 传感器图像视图
        for sensor_id in sorted(self.sensors.keys()):
            sensor_views.append(
                rrb.Spatial2DView(
                    name=sensor_id,
                    origin=f"/sensors/{sensor_id}"
                )
            )

        # ArUco距离曲线视图
        if self.has_aruco:
            aruco_plot = rrb.TimeSeriesView(
                name="ArUco Distances",
                origin="/aruco"
            )

        # 根据传感器数量和是否有ArUco数据调整布局
        if not self.has_aruco:
            # 无ArUco数据，只显示图像
            if len(sensor_views) <= 2:
                return rrb.Blueprint(rrb.Horizontal(*sensor_views))
            else:
                return rrb.Blueprint(
                    rrb.Vertical(
                        rrb.Horizontal(*sensor_views[:2]),
                        rrb.Horizontal(*sensor_views[2:]) if len(sensor_views) > 2 else sensor_views[2],
                        row_shares=[1, 1]
                    )
                )
        else:
            # 有ArUco数据：图像 + 距离曲线
            if len(sensor_views) <= 2:
                return rrb.Blueprint(
                    rrb.Vertical(
                        rrb.Horizontal(*sensor_views),
                        aruco_plot,
                        row_shares=[2, 1]
                    )
                )
            else:
                # 多个传感器：上方传感器，下方OAK+ArUco
                return rrb.Blueprint(
                    rrb.Vertical(
                        rrb.Horizontal(*sensor_views[1:]),  # VT传感器
                        rrb.Horizontal(
                            sensor_views[0],  # OAK相机
                            aruco_plot,
                            column_shares=[2, 1]
                        ),
                        row_shares=[1, 1]
                    )
                )

    def _log_session_info(self):
        """记录session信息"""
        info_text = f"# {self.metadata.get('session_name', 'Session')}\n\n"

        if self.use_relative_timestamps:
            duration = self.timestamps[-1] - self.timestamps[0]
        else:
            duration = (self.timestamps[-1] - self.timestamps[0])

        info_text += f"**时长**: {duration:.2f}秒  \n"
        info_text += f"**帧数**: {len(self.timestamps)}  \n\n"

        info_text += f"## 传感器\n\n"
        for sensor_id, sensor_info in self.sensors.items():
            sensor_name = sensor_info.get('sensor_name', sensor_id)
            frame_count = len(self.sensor_metadata.get(sensor_id, {}).get('frames', []))
            info_text += f"- **{sensor_id}** ({sensor_name}): {frame_count} 帧\n"

        if self.has_aruco:
            info_text += f"\n## ArUco检测\n\n"
            dist_abs = self.aruco_data.get('distance_absolute', [])
            valid_count = np.sum(~np.isnan(dist_abs))
            info_text += f"- 有效检测: {valid_count}/{len(dist_abs)} ({valid_count/len(dist_abs)*100:.1f}%)  \n"

            if valid_count > 0:
                info_text += f"- 距离范围: {np.nanmin(dist_abs):.2f} - {np.nanmax(dist_abs):.2f} mm  \n"
                info_text += f"- 平均距离: {np.nanmean(dist_abs):.2f} mm  \n"

        rr.log("session_info", rr.TextDocument(info_text, media_type=rr.MediaType.MARKDOWN))

    def _log_sensor_images(self, frame_idx, timestamp):
        """记录传感器图像"""
        # 时间戳转换
        if self.use_relative_timestamps:
            absolute_timestamp = timestamp + self.start_timestamp
        else:
            absolute_timestamp = timestamp

        for sensor_id, sensor_info in self.sensors.items():
            frames_dir = sensor_info.get('frames_dir', sensor_id)
            sensor_dir = self.session_dir / frames_dir

            sensor_meta = self.sensor_metadata.get(sensor_id, {})
            frames = sensor_meta.get('frames', [])

            if not frames:
                continue

            # 找到最接近的帧
            frame_info = self._find_closest_frame(frames, absolute_timestamp)

            if frame_info is None:
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

    def _log_aruco_data(self, frame_idx):
        """记录ArUco距离数据（跳过检测失败的数据）"""
        if not self.has_aruco or frame_idx >= len(self.aruco_data.get('distance_absolute', [])):
            return

        # 获取距离数据
        dist_abs = self.aruco_data.get('distance_absolute', [])[frame_idx]
        dist_h = self.aruco_data.get('distance_horizontal', [])[frame_idx]

        # 只记录有效数据（非NaN）
        if not np.isnan(dist_abs):
            rr.log("aruco/distance_absolute", rr.Scalars(dist_abs))
        else:
            # 跳过无效数据，不记录（曲线会断开）
            pass

        if dist_h is not None and not np.isnan(dist_h):
            rr.log("aruco/distance_horizontal", rr.Scalars(dist_h))

        # 检测状态
        left_detected = self.aruco_data.get('left_detected', [])[frame_idx] if frame_idx < len(self.aruco_data.get('left_detected', [])) else False
        right_detected = self.aruco_data.get('right_detected', [])[frame_idx] if frame_idx < len(self.aruco_data.get('right_detected', [])) else False

        status = "✓✓" if (left_detected and right_detected) else "✓✗" if left_detected else "✗✓" if right_detected else "✗✗"
        rr.log("aruco/status", rr.TextLog(f"L{status[0]} R{status[1]}"))

    def _find_closest_frame(self, frames, target_timestamp, tolerance=0.1):
        """找到最接近目标时间戳的帧"""
        if not frames:
            return None

        min_diff = float('inf')
        closest_frame = None

        for frame in frames:
            diff = abs(frame['timestamp'] - target_timestamp)
            if diff < min_diff:
                min_diff = diff
                closest_frame = frame

        if min_diff <= tolerance:
            return closest_frame

        return None


def main():
    parser = argparse.ArgumentParser(
        description='Rerun可视化 - 支持离线ArUco处理后的数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 可视化指定session（自动检测是否有ArUco数据）
  python vis_rerun.py data/session_20251028_143946

  # 可视化最新session
  python vis_rerun.py
        """
    )

    parser.add_argument('session_dir', nargs='?', help='Session目录路径')

    args = parser.parse_args()

    # 确定项目根目录（脚本在Tools目录，向上一级）
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # 处理session_dir参数
    if args.session_dir is None:
        print("查找最新session...")
        data_dir = project_root / "data"
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
        # 如果是相对路径，从项目根目录解析
        if not session_dir.is_absolute():
            session_dir = project_root / session_dir

    if not session_dir.exists():
        print(f"错误: Session目录不存在: {session_dir}")
        sys.exit(1)

    print("="*70)
    print("Rerun可视化 - 传感器图像 + ArUco距离")
    print("="*70)
    print()

    try:
        visualizer = SessionVisualizerWithAruco(session_dir)
        visualizer.visualize()

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
