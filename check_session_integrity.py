#!/usr/bin/env python3
"""
录制Session完整性检查工具
检查图片数量和metadata记录是否一致
"""

import json
import sys
from pathlib import Path


def check_sensor_integrity(sensor_dir):
    """
    检查单个传感器目录的完整性

    Returns:
        dict: 检查结果
    """
    sensor_dir = Path(sensor_dir)
    sensor_name = sensor_dir.name

    result = {
        'sensor': sensor_name,
        'path': str(sensor_dir),
        'image_count': 0,
        'metadata_count': 0,
        'metadata_total_frames': 0,
        'is_consistent': False,
        'missing_count': 0,
        'issues': []
    }

    # 检查目录是否存在
    if not sensor_dir.exists():
        result['issues'].append(f"目录不存在: {sensor_dir}")
        return result

    # 统计图片文件数量
    jpg_files = list(sensor_dir.glob("frame_*.jpg"))
    png_files = list(sensor_dir.glob("frame_*.png"))
    image_files = jpg_files + png_files
    result['image_count'] = len(image_files)

    # 读取metadata文件
    metadata_file = sensor_dir / "frames_metadata.json"
    if not metadata_file.exists():
        result['issues'].append("frames_metadata.json 文件不存在")
        return result

    try:
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        result['metadata_total_frames'] = metadata.get('total_frames', 0)
        frames_list = metadata.get('frames', [])
        result['metadata_count'] = len(frames_list)

        # 检查一致性
        if result['image_count'] == result['metadata_count'] == result['metadata_total_frames']:
            result['is_consistent'] = True
        else:
            result['is_consistent'] = False
            result['missing_count'] = result['image_count'] - result['metadata_count']

            if result['image_count'] != result['metadata_count']:
                result['issues'].append(
                    f"图片数量({result['image_count']})与metadata记录数量({result['metadata_count']})不一致"
                )

            if result['metadata_count'] != result['metadata_total_frames']:
                result['issues'].append(
                    f"metadata记录数量({result['metadata_count']})与total_frames({result['metadata_total_frames']})不一致"
                )

    except Exception as e:
        result['issues'].append(f"读取metadata失败: {e}")

    return result


def check_session(session_dir):
    """
    检查整个session的完整性

    Args:
        session_dir: session目录路径
    """
    session_dir = Path(session_dir)

    print(f"\n{'='*80}")
    print(f"检查Session: {session_dir.name}")
    print(f"路径: {session_dir}")
    print(f"{'='*80}\n")

    if not session_dir.exists():
        print(f"❌ Session目录不存在: {session_dir}")
        return

    # 查找所有传感器目录
    sensor_dirs = []
    for item in session_dir.iterdir():
        if item.is_dir() and (item / "frames_metadata.json").exists():
            sensor_dirs.append(item)

    if not sensor_dirs:
        print("❌ 未找到任何传感器目录（包含frames_metadata.json的目录）")
        return

    print(f"找到 {len(sensor_dirs)} 个传感器目录\n")

    # 检查每个传感器
    all_consistent = True
    results = []

    for sensor_dir in sorted(sensor_dirs):
        result = check_sensor_integrity(sensor_dir)
        results.append(result)

        # 显示结果
        print(f"📁 {result['sensor']}")
        print(f"   路径: {result['path']}")
        print(f"   图片文件: {result['image_count']} 张")
        print(f"   Metadata记录: {result['metadata_count']} 条")
        print(f"   Metadata total_frames: {result['metadata_total_frames']}")

        if result['is_consistent']:
            print(f"   状态: ✅ 一致")
        else:
            print(f"   状态: ❌ 不一致")
            all_consistent = False

            if result['missing_count'] > 0:
                print(f"   ⚠️  缺少 {result['missing_count']} 条metadata记录")
            elif result['missing_count'] < 0:
                print(f"   ⚠️  多了 {-result['missing_count']} 条metadata记录（图片缺失）")

            for issue in result['issues']:
                print(f"   ⚠️  {issue}")

        print()

    # 总结
    print(f"{'='*80}")
    if all_consistent:
        print("✅ 所有传感器数据一致！")
    else:
        print("❌ 发现数据不一致问题")
        print("\n建议：")
        print("  1. 重新录制测试，观察是否仍有问题")
        print("  2. 检查日志中是否有队列满或超时的警告")
        print("  3. 如果问题持续，考虑降低录制帧率或增加队列大小")
    print(f"{'='*80}\n")

    return results


def main():
    if len(sys.argv) > 1:
        session_path = sys.argv[1]
    else:
        # 查找最新的session
        data_dir = Path("./data")
        if not data_dir.exists():
            print("❌ data目录不存在")
            sys.exit(1)

        sessions = sorted(data_dir.glob("session_*"), key=lambda x: x.stat().st_mtime, reverse=True)
        if not sessions:
            print("❌ 未找到任何session")
            sys.exit(1)

        session_path = sessions[0]
        print(f"使用最新的session: {session_path.name}")

    check_session(session_path)


if __name__ == "__main__":
    main()
