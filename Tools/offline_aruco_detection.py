#!/usr/bin/env python3
"""
离线ArUco标记检测脚本
对已录制的session图片进行ArUco检测，生成完整的检测结果

使用方法:
    python offline_aruco_detection.py <session_dir>
    python offline_aruco_detection.py data/session_20251027_192209
"""

import sys
import json
import cv2
import numpy as np
from pathlib import Path

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


class OfflineArUcoDetector:
    """离线ArUco检测器"""

    def __init__(self, session_dir, config_file=None):
        """
        初始化离线检测器

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

    def process_all_frames(self):
        """处理所有帧"""
        print(f"\n开始处理 {self.total_frames} 帧...")

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
                # 添加空结果
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

    def save_results(self, results, output_filename="aruco_detections_offline.json"):
        """
        保存检测结果

        Args:
            results: 检测结果列表
            output_filename: 输出文件名
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
        print(f"\n统计信息:")
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

        return output_path


def main():
    if len(sys.argv) < 2:
        print("用法: python offline_aruco_detection.py <session_dir>")
        print("\n示例:")
        print("  python offline_aruco_detection.py data/session_20251027_192209")
        print("\n或自动使用最新session:")

        # 查找最新session
        data_dir = Path("./data")
        if data_dir.exists():
            sessions = sorted(data_dir.glob("session_*"),
                            key=lambda x: x.stat().st_mtime, reverse=True)
            if sessions:
                session_dir = sessions[0]
                print(f"  使用最新session: {session_dir.name}")
            else:
                print("  未找到任何session")
                sys.exit(1)
        else:
            print("  data目录不存在")
            sys.exit(1)
    else:
        session_dir = sys.argv[1]

    session_dir = Path(session_dir)

    if not session_dir.exists():
        print(f"错误: Session目录不存在: {session_dir}")
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"离线ArUco检测")
    print(f"{'='*80}\n")

    try:
        # 初始化检测器
        detector = OfflineArUcoDetector(session_dir)

        # 处理所有帧
        results = detector.process_all_frames()

        # 保存结果
        output_path = detector.save_results(results)

        print(f"\n{'='*80}")
        print("✓ 检测完成！")
        print(f"{'='*80}\n")

        print("后续步骤:")
        print(f"  1. 查看结果: cat {output_path}")
        print(f"  2. 结果中每帧都有对应的ArUco检测数据")
        print(f"  3. 可以用此数据更新PKL文件或进行分析")

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
