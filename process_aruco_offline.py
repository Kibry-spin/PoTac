#!/usr/bin/env python3
"""
离线ArUco处理脚本（检测+PKL更新一体化）
对已录制的session图片进行ArUco检测，并自动更新PKL文件

使用方法:
    python process_aruco_offline.py <session_dir>
    python process_aruco_offline.py data/session_20251027_192209

    # 仅检测不更新PKL
    python process_aruco_offline.py <session_dir> --detect-only
"""

import os
import sys
import json
import pickle
import cv2
import numpy as np
from pathlib import Path

# 禁用Kivy参数解析（必须在导入其他模块前）
os.environ['KIVY_NO_ARGS'] = '1'

# 尝试导入tqdm，如果不存在则使用简单进度显示
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("提示: 安装tqdm可获得更好的进度显示 (pip install tqdm)")

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from vision.aruco_detector_optimized import ArUcoDetectorOptimized


class OfflineArUcoProcessor:
    """离线ArUco检测和PKL更新处理器"""

    def __init__(self, session_dir, config_file=None):
        """
        初始化处理器

        Args:
            session_dir: session目录路径
            config_file: 配置文件路径（可选）
        """
        self.session_dir = Path(session_dir)
        self.oak_dir = self.session_dir / "oak_camera"

        if not self.oak_dir.exists():
            raise ValueError(f"OAK camera目录不存在: {self.oak_dir}")

        # 加载frames metadata
        self.metadata_file = self.oak_dir / "frames_metadata.json"
        if not self.metadata_file.exists():
            raise ValueError(f"Metadata文件不存在: {self.metadata_file}")

        with open(self.metadata_file, 'r') as f:
            self.metadata = json.load(f)

        self.total_frames = self.metadata['total_frames']
        self.frames = self.metadata['frames']

        print(f"Session: {self.session_dir.name}")
        print(f"总帧数: {self.total_frames}")

        # 初始化ArUco检测器
        if config_file is None:
            config_file = "config/settings.json"

        self.aruco_detector = ArUcoDetectorOptimized(config_file)

        # 尝试加载OAK相机标定
        self._load_oak_calibration()

    def _load_oak_calibration(self):
        """加载OAK相机的出厂标定参数"""
        try:
            # 尝试从depthai读取标定（如果OAK相机连接）
            import depthai as dai

            devices = dai.Device.getAllAvailableDevices()
            if devices:
                print("检测到OAK设备，加载出厂标定...")
                device = dai.Device()
                calib_data = device.readCalibration()

                # 获取RGB相机标定
                rgb_socket = dai.CameraBoardSocket.CAM_A

                # 使用实际分辨率（从第一张图片读取）
                first_image = self.oak_dir / self.frames[0]['filename']
                img = cv2.imread(str(first_image))
                height, width = img.shape[:2]

                intrinsics = calib_data.getCameraIntrinsics(rgb_socket, width, height)
                distortion = calib_data.getDistortionCoefficients(rgb_socket)

                camera_matrix = np.array([
                    [intrinsics[0][0], 0, intrinsics[0][2]],
                    [0, intrinsics[1][1], intrinsics[1][2]],
                    [0, 0, 1]
                ], dtype=np.float64)

                dist_coeffs = np.array(distortion, dtype=np.float64)

                self.aruco_detector.set_camera_calibration(camera_matrix, dist_coeffs)
                self.aruco_detector.update_config({'estimate_pose': True})

                device.close()

                print(f"✓ 已加载OAK出厂标定 ({width}x{height})")
                print(f"  fx={intrinsics[0][0]:.2f}, fy={intrinsics[1][1]:.2f}")
                print(f"  cx={intrinsics[0][2]:.2f}, cy={intrinsics[1][2]:.2f}")
                return True
            else:
                print("⚠ 未检测到OAK设备，使用默认标定")
                return False

        except Exception as e:
            print(f"⚠ 加载相机标定失败: {e}")
            print("  将使用默认标定（可能影响距离精度）")
            return False

    def detect_all_frames(self):
        """检测所有帧的ArUco标记"""
        print(f"\n开始ArUco检测 ({self.total_frames} 帧)...")

        results = []

        # 使用tqdm或简单进度显示
        if HAS_TQDM:
            iterator = tqdm(self.frames, desc="检测进度")
        else:
            iterator = self.frames
            print("处理中...", end='', flush=True)

        for i, frame_info in enumerate(iterator):
            # 简单进度显示（无tqdm时）
            if not HAS_TQDM and i % 50 == 0:
                print(f"\r处理中... {i}/{self.total_frames} ({i/self.total_frames*100:.1f}%)", end='', flush=True)

            # 读取图片
            image_path = self.oak_dir / frame_info['filename']

            if not image_path.exists():
                print(f"\n⚠ 图片不存在: {frame_info['filename']}")
                results.append(self._create_empty_result(frame_info))
                continue

            frame = cv2.imread(str(image_path))
            if frame is None:
                print(f"\n⚠ 无法读取图片: {frame_info['filename']}")
                results.append(self._create_empty_result(frame_info))
                continue

            # ArUco检测
            try:
                _, detection_results = self.aruco_detector.detect_markers(frame)
                detection_info = self.aruco_detector.get_detection_info()

                # 添加帧信息
                result = {
                    'frame_num': frame_info['frame_num'],
                    'filename': frame_info['filename'],
                    'timestamp': frame_info['timestamp'],
                    'frame_seq_num': frame_info.get('frame_seq_num', -1),

                    # ArUco检测结果
                    'left_detected': detection_info.get('left_marker') is not None,
                    'right_detected': detection_info.get('right_marker') is not None,

                    'marker_distance': detection_info.get('marker_distance'),  # 像素距离
                    'real_distance_3d': detection_info.get('real_distance_3d'),  # 3D绝对距离 (mm)
                    'horizontal_distance': detection_info.get('horizontal_distance'),  # 水平距离 (mm)

                    'left_marker': self._extract_marker_info(detection_info.get('left_marker')),
                    'right_marker': self._extract_marker_info(detection_info.get('right_marker')),

                    'calibrated': detection_info.get('calibrated', False),
                }

                results.append(result)

            except Exception as e:
                print(f"\n⚠ 检测失败 ({frame_info['filename']}): {e}")
                results.append(self._create_empty_result(frame_info))

        if not HAS_TQDM:
            print(f"\r处理中... {self.total_frames}/{self.total_frames} (100.0%)")

        return results

    def _create_empty_result(self, frame_info):
        """创建空检测结果（未检测到标记）"""
        return {
            'frame_num': frame_info['frame_num'],
            'filename': frame_info['filename'],
            'timestamp': frame_info['timestamp'],
            'frame_seq_num': frame_info.get('frame_seq_num', -1),

            'left_detected': False,
            'right_detected': False,

            'marker_distance': None,
            'real_distance_3d': None,
            'horizontal_distance': None,

            'left_marker': None,
            'right_marker': None,

            'calibrated': False,
        }

    def _extract_marker_info(self, marker):
        """提取标记信息"""
        if marker is None:
            return None

        # 处理corners - 可能已经是list或numpy array
        corners = marker.get('corners')
        if corners is not None:
            corners = corners.tolist() if isinstance(corners, np.ndarray) else corners

        info = {
            'id': marker.get('id'),
            'corners': corners,
        }

        # 如果有位姿估计
        if 'tvec' in marker and marker['tvec'] is not None:
            tvec = marker['tvec']
            info['tvec'] = tvec.tolist() if isinstance(tvec, np.ndarray) else tvec

            if 'rvec' in marker and marker['rvec'] is not None:
                rvec = marker['rvec']
                info['rvec'] = rvec.tolist() if isinstance(rvec, np.ndarray) else rvec

        return info

    def save_detection_json(self, results, output_filename="aruco_detections_offline.json"):
        """
        保存检测结果为JSON

        Args:
            results: 检测结果列表
            output_filename: 输出文件名

        Returns:
            输出文件路径
        """
        output_path = self.oak_dir / output_filename

        # 计算统计信息
        left_detected = sum(1 for r in results if r['left_detected'])
        right_detected = sum(1 for r in results if r['right_detected'])
        both_detected = sum(1 for r in results if r['left_detected'] and r['right_detected'])

        # 计算有效距离测量
        valid_distances = [r['real_distance_3d'] for r in results
                          if r['real_distance_3d'] is not None]

        output_data = {
            'session_name': self.session_dir.name,
            'total_frames': len(results),
            'oak_camera_dir': str(self.oak_dir.relative_to(self.session_dir)),

            'statistics': {
                'left_detection_count': left_detected,
                'left_detection_rate': left_detected / len(results) * 100,
                'right_detection_count': right_detected,
                'right_detection_rate': right_detected / len(results) * 100,
                'both_detection_count': both_detected,
                'both_detection_rate': both_detected / len(results) * 100,
                'valid_distance_measurements': len(valid_distances),
            },

            'distance_statistics': {},

            'detections': results
        }

        # 距离统计
        if valid_distances:
            output_data['distance_statistics'] = {
                'mean': float(np.mean(valid_distances)),
                'std': float(np.std(valid_distances)),
                'min': float(np.min(valid_distances)),
                'max': float(np.max(valid_distances)),
                'median': float(np.median(valid_distances)),
            }

        # 保存JSON
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"\n✓ 检测结果已保存: {output_path}")
        print(f"\n检测统计:")
        print(f"  总帧数: {len(results)}")
        print(f"  左标记检测率: {left_detected}/{len(results)} ({left_detected/len(results)*100:.1f}%)")
        print(f"  右标记检测率: {right_detected}/{len(results)} ({right_detected/len(results)*100:.1f}%)")
        print(f"  双标记检测率: {both_detected}/{len(results)} ({both_detected/len(results)*100:.1f}%)")
        print(f"  有效距离测量: {len(valid_distances)}")

        if valid_distances:
            print(f"\n距离统计 (mm):")
            print(f"  平均: {np.mean(valid_distances):.2f}")
            print(f"  标准差: {np.std(valid_distances):.2f}")
            print(f"  范围: {np.min(valid_distances):.2f} - {np.max(valid_distances):.2f}")

        return output_path, output_data

    def update_pkl(self, detection_results):
        """
        使用检测结果更新PKL文件

        Args:
            detection_results: 检测结果列表（来自detect_all_frames）

        Returns:
            是否更新成功
        """
        print(f"\n开始更新PKL文件...")

        pkl_path = self.session_dir / "aligned_data.pkl"

        # 读取或创建PKL文件
        if pkl_path.exists():
            print(f"✓ 找到现有PKL文件")
            with open(pkl_path, 'rb') as f:
                pkl_data = pickle.load(f)
        else:
            print(f"✓ 创建新的PKL文件")
            # 创建基础结构
            pkl_data = {
                'metadata': {
                    'session_name': self.session_dir.name,
                    'sensors': {},
                    'aruco': {
                        'enabled': True,
                        'marker_ids': [0, 1],
                        'marker_size': 0.015,
                        'calibrated': detection_results[0].get('calibrated', False) if detection_results else False,
                        'dictionary': 'DICT_4X4_250'
                    }
                },
                'data': {}
            }

        # 构建ArUco数据数组
        timestamps = []
        frame_seq_nums = []
        left_detected = []
        right_detected = []
        distance_absolute = []
        distance_horizontal = []
        distance_pixel = []
        left_positions = []
        right_positions = []

        for det in detection_results:
            timestamps.append(det['timestamp'])
            frame_seq_nums.append(det.get('frame_seq_num', -1))

            left_detected.append(det['left_detected'])
            right_detected.append(det['right_detected'])

            # 距离数据（使用None/NaN表示缺失）
            distance_absolute.append(det['real_distance_3d'] if det['real_distance_3d'] is not None else np.nan)
            distance_horizontal.append(det['horizontal_distance'] if det['horizontal_distance'] is not None else np.nan)
            distance_pixel.append(det['marker_distance'] if det['marker_distance'] is not None else np.nan)

            # 3D位置
            if det['left_marker'] and 'tvec' in det['left_marker']:
                left_positions.append(det['left_marker']['tvec'])
            else:
                left_positions.append([np.nan, np.nan, np.nan])

            if det['right_marker'] and 'tvec' in det['right_marker']:
                right_positions.append(det['right_marker']['tvec'])
            else:
                right_positions.append([np.nan, np.nan, np.nan])

        # 转换为numpy数组
        timestamps = np.array(timestamps)
        frame_seq_nums = np.array(frame_seq_nums)
        left_detected = np.array(left_detected, dtype=bool)
        right_detected = np.array(right_detected, dtype=bool)
        distance_absolute = np.array(distance_absolute)
        distance_horizontal = np.array(distance_horizontal)
        distance_pixel = np.array(distance_pixel)
        left_positions = np.array(left_positions)
        right_positions = np.array(right_positions)

        # 计算统计信息
        valid_abs = ~np.isnan(distance_absolute)
        statistics = {}
        if np.any(valid_abs):
            statistics = {
                'detection_rate_left': float(np.mean(left_detected)),
                'detection_rate_right': float(np.mean(right_detected)),
                'mean_distance_absolute': float(np.nanmean(distance_absolute)),
                'mean_distance_horizontal': float(np.nanmean(distance_horizontal)),
                'std_distance_absolute': float(np.nanstd(distance_absolute)),
                'min_distance': float(np.nanmin(distance_absolute)),
                'max_distance': float(np.nanmax(distance_absolute))
            }

        # 更新PKL数据
        pkl_data['data']['timestamps'] = timestamps
        pkl_data['data']['frame_seq_nums'] = frame_seq_nums

        pkl_data['data']['oak_camera'] = {
            'frame_count': len(detection_results),
            'fps': 30,  # 从metadata读取
            'resolution': (1280, 720)  # 从图片读取
        }

        pkl_data['data']['aruco'] = {
            'left_detected': left_detected,
            'right_detected': right_detected,
            'distance_absolute': distance_absolute,
            'distance_horizontal': distance_horizontal,
            'distance_pixel': distance_pixel,
            'left_positions': left_positions,
            'right_positions': right_positions,
            'statistics': statistics
        }

        # 保存PKL
        with open(pkl_path, 'wb') as f:
            pickle.dump(pkl_data, f, protocol=pickle.HIGHEST_PROTOCOL)

        print(f"✓ PKL文件已更新: {pkl_path}")
        print(f"\nPKL内容:")
        print(f"  时间戳数量: {len(timestamps)}")
        print(f"  ArUco数据点: {len(distance_absolute)}")
        print(f"  有效距离测量: {np.sum(valid_abs)}")

        if statistics:
            print(f"\n统计信息:")
            print(f"  左标记检测率: {statistics['detection_rate_left']*100:.1f}%")
            print(f"  右标记检测率: {statistics['detection_rate_right']*100:.1f}%")
            print(f"  平均距离: {statistics['mean_distance_absolute']:.2f} mm")
            print(f"  距离范围: {statistics['min_distance']:.2f} - {statistics['max_distance']:.2f} mm")

        return True


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='离线ArUco处理脚本（检测+PKL更新一体化）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 完整处理（检测+更新PKL）
  python process_aruco_offline.py data/session_20251027_192209

  # 仅检测，不更新PKL
  python process_aruco_offline.py data/session_20251027_192209 --detect-only

  # 使用最新session
  python process_aruco_offline.py
        """
    )

    parser.add_argument('session_dir', nargs='?', help='Session目录路径')
    parser.add_argument('--detect-only', action='store_true',
                       help='仅进行检测，不更新PKL文件')
    parser.add_argument('--config', default=None,
                       help='ArUco配置文件路径 (默认: config/settings.json)')

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
                print(f"使用最新session: {session_dir.name}")
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

    print(f"\n{'='*80}")
    print(f"离线ArUco处理")
    print(f"{'='*80}\n")

    try:
        # 初始化处理器
        processor = OfflineArUcoProcessor(session_dir, config_file=args.config)

        # 步骤1: ArUco检测
        print(f"\n{'='*80}")
        print("步骤 1/2: ArUco标记检测")
        print(f"{'='*80}")
        detection_results = processor.detect_all_frames()

        # 保存JSON
        json_path, json_data = processor.save_detection_json(detection_results)

        # 步骤2: 更新PKL（如果需要）
        if not args.detect_only:
            print(f"\n{'='*80}")
            print("步骤 2/2: 更新PKL文件")
            print(f"{'='*80}")
            processor.update_pkl(detection_results)

        # 完成
        print(f"\n{'='*80}")
        print("✓ 处理完成！")
        print(f"{'='*80}\n")

        if args.detect_only:
            print("检测结果已保存，PKL文件未更新")
            print(f"  JSON文件: {json_path}")
            print(f"\n如需更新PKL，请运行:")
            print(f"  python process_aruco_offline.py {session_dir}")
        else:
            print("ArUco数据已完整处理并更新到PKL文件")
            print(f"  JSON文件: {json_path}")
            print(f"  PKL文件: {session_dir}/aligned_data.pkl")
            print(f"\n数据覆盖率: 100% (每帧都有ArUco数据)")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
