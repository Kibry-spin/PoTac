#!/usr/bin/env python3
"""
更新PKL文件的ArUco数据
使用离线检测的结果更新或创建PKL文件
"""

import sys
import json
import pickle
import numpy as np
from pathlib import Path


def update_pkl_with_offline_detections(session_dir, offline_json_path=None):
    """
    使用离线检测结果更新PKL文件

    Args:
        session_dir: session目录
        offline_json_path: 离线检测结果JSON路径（默认自动查找）
    """
    session_dir = Path(session_dir)

    # 查找离线检测结果
    if offline_json_path is None:
        offline_json_path = session_dir / "oak_camera" / "aruco_detections_offline.json"

    if not offline_json_path.exists():
        print(f"错误: 离线检测结果不存在: {offline_json_path}")
        print("请先运行: python offline_aruco_detection.py")
        return False

    # 读取离线检测结果
    with open(offline_json_path, 'r') as f:
        offline_data = json.load(f)

    detections = offline_data['detections']
    total_frames = offline_data['total_frames']

    print(f"Session: {session_dir.name}")
    print(f"离线检测帧数: {total_frames}")

    # 读取或创建PKL文件
    pkl_path = session_dir / "aligned_data.pkl"

    if pkl_path.exists():
        print(f"✓ 找到现有PKL文件，将更新ArUco数据")
        with open(pkl_path, 'rb') as f:
            pkl_data = pickle.load(f)
    else:
        print(f"✓ 创建新的PKL文件")
        # 创建基础结构
        pkl_data = {
            'metadata': {
                'session_name': session_dir.name,
                'sensors': {},
                'aruco': {
                    'enabled': True,
                    'marker_ids': [0, 1],
                    'marker_size': 0.015,
                    'calibrated': detections[0].get('calibrated', False) if detections else False,
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

    for det in detections:
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
        'frame_count': total_frames,
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

    print(f"\n✓ PKL文件已更新: {pkl_path}")
    print(f"\n更新内容:")
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
    if len(sys.argv) < 2:
        print("用法: python update_pkl_with_offline.py <session_dir>")
        print("\n示例:")
        print("  python update_pkl_with_offline.py data/session_20251027_192209")
        sys.exit(1)

    session_dir = Path(sys.argv[1])

    if not session_dir.exists():
        print(f"错误: Session目录不存在: {session_dir}")
        sys.exit(1)

    print(f"\n{'='*80}")
    print(f"更新PKL文件")
    print(f"{'='*80}\n")

    try:
        success = update_pkl_with_offline_detections(session_dir)

        if success:
            print(f"\n{'='*80}")
            print("✓ 更新完成！")
            print(f"{'='*80}\n")
            print("现在PKL文件包含完整的ArUco数据（每帧都有）")
        else:
            sys.exit(1)

    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
