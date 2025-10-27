#!/usr/bin/env python3
"""
查看PKL文件的完整内容
"""
import pickle
import numpy as np
import json
from pathlib import Path
import sys


def inspect_pkl(pkl_path):
    """详细检查PKL文件内容"""
    print(f"PKL文件: {pkl_path}")
    print("=" * 80)
    
    # 加载PKL
    with open(pkl_path, 'rb') as f:
        data = pickle.load(f)
    
    print("\n【顶层结构】")
    print(f"主要键: {list(data.keys())}")
    
    # 元数据
    print("\n【元数据 (metadata)】")
    metadata = data['metadata']
    print(f"  session_name: {metadata['session_name']}")
    print(f"  start_time: {metadata.get('start_time', 'N/A')}")
    print(f"  end_time: {metadata.get('end_time', 'N/A')}")
    print(f"  duration: {metadata.get('duration', 0):.2f}秒")
    
    print("\n  传感器 (sensors):")
    for sensor_id, sensor_info in metadata['sensors'].items():
        print(f"    {sensor_id}:")
        for key, value in sensor_info.items():
            print(f"      {key}: {value}")
    
    print("\n  ArUco配置:")
    aruco = metadata['aruco']
    for key, value in aruco.items():
        print(f"    {key}: {value}")
    
    # 数据部分
    print("\n【数据部分 (data)】")
    data_section = data['data']
    print(f"主要数据键: {list(data_section.keys())}")
    
    # 时间戳
    if 'timestamps' in data_section:
        timestamps = data_section['timestamps']
        print(f"\n  时间戳 (timestamps):")
        print(f"    类型: {type(timestamps)}")
        print(f"    形状: {timestamps.shape}")
        print(f"    数据类型: {timestamps.dtype}")
        print(f"    总帧数: {len(timestamps)}")
        print(f"    时间范围: {timestamps[0]:.3f}s - {timestamps[-1]:.3f}s")
        print(f"    前5个时间戳: {timestamps[:5]}")
    
    # 帧序号
    if 'frame_seq_nums' in data_section:
        frame_seq_nums = data_section['frame_seq_nums']
        print(f"\n  帧序号 (frame_seq_nums):")
        print(f"    类型: {type(frame_seq_nums)}")
        print(f"    形状: {frame_seq_nums.shape}")
        print(f"    数据类型: {frame_seq_nums.dtype}")
        print(f"    序号范围: {frame_seq_nums[0]} - {frame_seq_nums[-1]}")
        print(f"    前5个序号: {frame_seq_nums[:5]}")
    
    # OAK相机信息
    if 'oak_camera' in data_section:
        oak = data_section['oak_camera']
        print(f"\n  OAK相机信息:")
        for key, value in oak.items():
            print(f"    {key}: {value}")
    
    # ArUco数据
    if 'aruco' in data_section:
        aruco_data = data_section['aruco']
        print(f"\n  ArUco检测数据:")
        print(f"    数据字段: {list(aruco_data.keys())}")
        
        for key, value in aruco_data.items():
            if key == 'statistics':
                print(f"\n    统计信息 (statistics):")
                for stat_key, stat_val in value.items():
                    if isinstance(stat_val, (int, float)):
                        print(f"      {stat_key}: {stat_val:.4f}")
                    else:
                        print(f"      {stat_key}: {stat_val}")
            elif isinstance(value, np.ndarray):
                print(f"\n    {key}:")
                print(f"      类型: {type(value)}")
                print(f"      形状: {value.shape}")
                print(f"      数据类型: {value.dtype}")
                
                # 显示一些示例数据
                if len(value.shape) == 1:
                    # 1D数组
                    if value.dtype == bool:
                        print(f"      检测率: {np.mean(value)*100:.1f}% ({np.sum(value)}/{len(value)})")
                        print(f"      前5个值: {value[:5]}")
                    else:
                        valid = ~np.isnan(value)
                        if np.any(valid):
                            print(f"      有效值: {np.sum(valid)}/{len(value)}")
                            print(f"      范围: {np.nanmin(value):.2f} - {np.nanmax(value):.2f}")
                            print(f"      平均: {np.nanmean(value):.2f}")
                            print(f"      前5个值: {value[:5]}")
                        else:
                            print(f"      前5个值: {value[:5]}")
                elif len(value.shape) == 2:
                    # 2D数组（如位置数据）
                    print(f"      前3行:")
                    for i in range(min(3, len(value))):
                        print(f"        [{i}]: {value[i]}")
    
    # 其他传感器数据
    other_sensors = [k for k in data_section.keys() 
                    if k not in ['timestamps', 'frame_seq_nums', 'oak_camera', 'aruco']]
    if other_sensors:
        print(f"\n  其他传感器数据:")
        for sensor_id in other_sensors:
            sensor_data = data_section[sensor_id]
            print(f"\n    {sensor_id}:")
            for key, value in sensor_data.items():
                print(f"      {key}: {value}")
    
    print("\n" + "=" * 80)
    print("✓ 检查完成")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        pkl_path = sys.argv[1]
    else:
        # 使用测试数据
        pkl_path = "/home/kirdo/robo/PoTac/data/session_20251027_190540/aligned_data.pkl"
    
    if not Path(pkl_path).exists():
        print(f"错误: 文件不存在: {pkl_path}")
        sys.exit(1)
    
    inspect_pkl(pkl_path)
