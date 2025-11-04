#!/usr/bin/env python3
"""
批量ArUco处理工具
遍历data目录及其子目录，批量处理所有session的ArUco数据
"""

import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any
import json
import multiprocessing as mp
from datetime import datetime
import traceback

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 尝试导入tqdm（如果没有则使用简单进度显示）
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("提示: 安装tqdm可获得更好的进度显示 (pip install tqdm)")


class SimpleBatchProcessor:
    """简化的批量ArUco处理器"""

    def __init__(self, force_reprocess=False, skip_update_pkl=False):
        self.force_reprocess = force_reprocess
        self.skip_update_pkl = skip_update_pkl
        self.results = []

        # 全局相机标定数据（只加载一次）
        self.camera_matrix = None
        self.dist_coeffs = None
        self.calibration_loaded = False

        # 在初始化时加载相机标定
        self._load_camera_calibration_once()

    def _load_camera_calibration_once(self):
        """批量处理前只加载一次相机标定（性能优化）"""
        try:
            import depthai as dai
            import cv2
            import numpy as np

            devices = dai.Device.getAllAvailableDevices()
            if devices:
                print("✓ 检测到OAK设备，加载出厂标定（全局加载，仅一次）...")
                device = dai.Device()
                calib_data = device.readCalibration()

                # 获取RGB相机标定
                rgb_socket = dai.CameraBoardSocket.CAM_A

                # 使用标准1080p分辨率
                width, height = 1920, 1080

                intrinsics = calib_data.getCameraIntrinsics(rgb_socket, width, height)
                distortion = calib_data.getDistortionCoefficients(rgb_socket)

                self.camera_matrix = np.array([
                    [intrinsics[0][0], 0, intrinsics[0][2]],
                    [0, intrinsics[1][1], intrinsics[1][2]],
                    [0, 0, 1]
                ], dtype=np.float64)

                self.dist_coeffs = np.array(distortion, dtype=np.float64)

                device.close()

                self.calibration_loaded = True
                print(f"  相机标定已加载 ({width}x{height})")
                print(f"  fx={intrinsics[0][0]:.2f}, fy={intrinsics[1][1]:.2f}")
                print(f"  cx={intrinsics[0][2]:.2f}, cy={intrinsics[1][2]:.2f}")
            else:
                print("⚠ 未检测到OAK设备，将使用默认标定")
                self.calibration_loaded = False

        except Exception as e:
            print(f"⚠ 加载相机标定失败: {e}")
            print("  将使用默认标定")
            self.calibration_loaded = False

    def is_valid_session(self, session_dir: Path) -> bool:
        """判断是否是有效的session目录"""
        # 检查是否有aligned_data.pkl
        pkl_file = session_dir / 'aligned_data.pkl'
        if not pkl_file.exists():
            return False

        # 检查是否有oak_camera目录
        oak_dir = session_dir / 'oak_camera'
        if not oak_dir.exists():
            return False

        # 检查是否有frames_metadata.json
        metadata_file = oak_dir / 'frames_metadata.json'
        if not metadata_file.exists():
            return False

        return True

    def should_skip_session(self, session_dir: Path) -> tuple:
        """判断是否应该跳过此session"""
        # 检查是否已有ArUco检测结果
        output_file = session_dir / 'oak_camera' / 'aruco_detections_offline.json'

        if output_file.exists() and not self.force_reprocess:
            return True, "已处理（使用--force强制重新处理）"

        return False, ""

    def find_all_sessions(self, data_dir: Path) -> List[Path]:
        """递归查找data目录下所有session"""
        sessions = []

        print(f"\n搜索session目录: {data_dir}")

        # 递归查找所有可能的session目录
        for path in data_dir.rglob('session_*'):
            if path.is_dir() and self.is_valid_session(path):
                sessions.append(path)

        # 按名称排序
        sessions.sort()

        return sessions

    def process_single_session(self, session_dir: Path) -> Dict[str, Any]:
        """处理单个session的ArUco数据"""
        result = {
            'session': str(session_dir.relative_to(Path('data'))),
            'full_path': str(session_dir),
            'success': False,
            'skipped': False,
            'message': '',
            'stats': {}
        }

        try:
            # 检查是否跳过
            should_skip, skip_reason = self.should_skip_session(session_dir)
            if should_skip:
                result['skipped'] = True
                result['success'] = True
                result['message'] = skip_reason
                return result

            # 导入处理器（延迟导入避免启动慢）
            sys.path.insert(0, str(project_root / 'Tools'))
            from process_aruco_offline import OfflineArUcoProcessor

            # 创建处理器
            processor = OfflineArUcoProcessor(session_dir)

            # 如果有全局标定数据，应用到处理器（避免重复加载）
            if self.calibration_loaded:
                processor.aruco_detector.set_camera_calibration(
                    self.camera_matrix,
                    self.dist_coeffs
                )
                processor.aruco_detector.update_config({'estimate_pose': True})

            # 1. ArUco检测 - 使用正确的方法名
            detection_results = processor.detect_all_frames()

            if not detection_results:
                result['message'] = '检测失败或无检测结果'
                return result

            # 保存JSON（获取统计信息）
            _, json_data = processor.save_detection_json(detection_results)

            # 2. 更新PKL（如果需要）- 使用正确的方法名
            if not self.skip_update_pkl:
                processor.update_pkl(detection_results)
                result['message'] = 'ArUco检测和PKL更新完成'
            else:
                result['message'] = 'ArUco检测完成（跳过PKL更新）'

            # 3. 统计信息（从JSON数据提取）
            stats = json_data.get('statistics', {})
            result['stats'] = {
                'total_frames': json_data.get('total_frames', 0),
                'left_detected': stats.get('left_detection_count', 0),
                'right_detected': stats.get('right_detection_count', 0),
                'both_detected': stats.get('both_detection_count', 0),
                'valid_distances': stats.get('valid_distance_measurements', 0)
            }

            result['success'] = True

        except Exception as e:
            result['message'] = f'处理失败: {str(e)}'
            result['error'] = traceback.format_exc()

        return result

    def process_batch_parallel(self, sessions: List[Path], num_workers: int) -> List[Dict]:
        """并行批量处理"""
        print(f"\n使用 {num_workers} 个进程并行处理...")

        with mp.Pool(num_workers) as pool:
            if HAS_TQDM:
                results = list(tqdm(
                    pool.imap(self.process_single_session, sessions),
                    total=len(sessions),
                    desc="处理进度"
                ))
            else:
                results = []
                for i, result in enumerate(pool.imap(self.process_single_session, sessions)):
                    results.append(result)
                    print(f"进度: {i+1}/{len(sessions)} ({(i+1)/len(sessions)*100:.1f}%)")

        return results

    def process_batch_serial(self, sessions: List[Path]) -> List[Dict]:
        """串行批量处理"""
        print(f"\n串行处理...")

        results = []
        if HAS_TQDM:
            for session in tqdm(sessions, desc="处理进度"):
                result = self.process_single_session(session)
                results.append(result)
        else:
            for i, session in enumerate(sessions):
                print(f"\n[{i+1}/{len(sessions)}] 处理: {session.name}")
                result = self.process_single_session(session)
                results.append(result)

                # 显示结果
                if result['success']:
                    if result['skipped']:
                        print(f"  ⊙ 跳过: {result['message']}")
                    else:
                        stats = result['stats']
                        print(f"  ✓ 成功: {stats['valid_distances']}/{stats['total_frames']} 有效距离")
                else:
                    print(f"  ✗ 失败: {result['message']}")

        return results

    def generate_summary(self, results: List[Dict]) -> Dict[str, Any]:
        """生成统计摘要"""
        total = len(results)
        successful = sum(1 for r in results if r['success'] and not r['skipped'])
        skipped = sum(1 for r in results if r['skipped'])
        failed = sum(1 for r in results if not r['success'])

        total_frames = sum(r['stats'].get('total_frames', 0) for r in results if r['success'])
        total_valid_distances = sum(r['stats'].get('valid_distances', 0)
                                   for r in results if r['success'])

        return {
            'total_sessions': total,
            'successful': successful,
            'skipped': skipped,
            'failed': failed,
            'total_frames_processed': total_frames,
            'total_valid_distances': total_valid_distances
        }

    def save_report(self, results: List[Dict], summary: Dict, output_file: str):
        """保存详细报告"""
        report_path = Path(output_file)

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("批量ArUco处理报告\n")
            f.write("="*80 + "\n\n")

            # 生成时间
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # 统计摘要
            f.write("统计摘要\n")
            f.write("-"*80 + "\n")
            f.write(f"总session数:      {summary['total_sessions']}\n")
            f.write(f"成功处理:         {summary['successful']}\n")
            f.write(f"跳过 (已处理):    {summary['skipped']}\n")
            f.write(f"失败:             {summary['failed']}\n")
            f.write(f"总处理帧数:       {summary['total_frames_processed']}\n")
            f.write(f"有效距离测量数:   {summary['total_valid_distances']}\n\n")

            # 详细结果
            f.write("详细结果\n")
            f.write("-"*80 + "\n\n")

            # 按状态分组
            successful = [r for r in results if r['success'] and not r['skipped']]
            skipped = [r for r in results if r['skipped']]
            failed = [r for r in results if not r['success']]

            if successful:
                f.write(f"✓ 成功处理 ({len(successful)} 个):\n\n")
                for r in successful:
                    stats = r['stats']
                    f.write(f"  {r['session']}\n")
                    f.write(f"    总帧数: {stats['total_frames']}\n")
                    f.write(f"    左标记检测: {stats['left_detected']}/{stats['total_frames']}\n")
                    f.write(f"    右标记检测: {stats['right_detected']}/{stats['total_frames']}\n")
                    f.write(f"    双标记检测: {stats['both_detected']}/{stats['total_frames']}\n")
                    f.write(f"    有效距离: {stats['valid_distances']}/{stats['total_frames']}\n\n")

            if skipped:
                f.write(f"\n⊙ 跳过 ({len(skipped)} 个):\n\n")
                for r in skipped:
                    f.write(f"  {r['session']}\n")
                    f.write(f"    原因: {r['message']}\n\n")

            if failed:
                f.write(f"\n✗ 失败 ({len(failed)} 个):\n\n")
                for r in failed:
                    f.write(f"  {r['session']}\n")
                    f.write(f"    错误: {r['message']}\n")
                    if 'error' in r:
                        f.write(f"    详细:\n")
                        for line in r['error'].split('\n'):
                            f.write(f"      {line}\n")
                    f.write("\n")

        print(f"\n详细报告已保存: {report_path}")

    def save_json_report(self, results: List[Dict], summary: Dict, output_file: str):
        """保存JSON格式报告"""
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'summary': summary,
            'results': results
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"JSON报告已保存: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='批量ArUco处理工具 - 递归处理data目录下所有session',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

  # 基本用法：处理data目录下所有session
  python3 Tools/batch_process.py

  # 指定data目录
  python3 Tools/batch_process.py --data-dir /path/to/data

  # 并行处理（8个进程）
  python3 Tools/batch_process.py --parallel --workers 8

  # 强制重新处理（即使已有结果）
  python3 Tools/batch_process.py --force

  # 仅检测ArUco，不更新PKL文件
  python3 Tools/batch_process.py --skip-update-pkl

  # 先预览，不实际处理
  python3 Tools/batch_process.py --dry-run

  # 指定报告输出路径
  python3 Tools/batch_process.py --report batch_report_20251104.txt

注意:
  - 默认会跳过已处理的session（使用--force强制重新处理）
  - 并行处理可能导致日志输出混乱，但不影响结果
  - 报告文件会保存在当前目录
        """
    )

    parser.add_argument('--data-dir', default='data',
                       help='数据目录路径（默认: data）')

    parser.add_argument('--parallel', action='store_true',
                       help='启用并行处理（加快速度）')

    parser.add_argument('--workers', type=int, default=4,
                       help='并行处理的进程数（默认: 4）')

    parser.add_argument('--force', action='store_true',
                       help='强制重新处理已有结果的session')

    parser.add_argument('--skip-update-pkl', action='store_true',
                       help='仅检测ArUco，不更新PKL文件')

    parser.add_argument('--dry-run', action='store_true',
                       help='仅列出将要处理的session，不实际处理')

    parser.add_argument('--report', default=None,
                       help='报告输出文件路径（默认: logs/batch_aruco_YYYYMMDD_HHMMSS.txt）')

    parser.add_argument('--json-report', default=None,
                       help='JSON报告输出文件路径（默认: logs/batch_aruco_YYYYMMDD_HHMMSS.json）')

    args = parser.parse_args()

    print("="*80)
    print("批量ArUco处理工具")
    print("="*80)

    # 确保logs目录存在
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)

    # 生成带时间戳的报告文件名（确保不重复）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if args.report is None:
        args.report = logs_dir / f'batch_aruco_{timestamp}.txt'
    else:
        args.report = Path(args.report)

    if args.json_report is None:
        args.json_report = logs_dir / f'batch_aruco_{timestamp}.json'
    else:
        args.json_report = Path(args.json_report)

    # 验证data目录
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"\n错误: 数据目录不存在: {data_dir}")
        return 1

    # 创建处理器
    processor = SimpleBatchProcessor(
        force_reprocess=args.force,
        skip_update_pkl=args.skip_update_pkl
    )

    # 查找所有sessions
    sessions = processor.find_all_sessions(data_dir)

    if not sessions:
        print(f"\n未在 {data_dir} 及其子目录中找到有效的session")
        print("\n有效session需要包含:")
        print("  - aligned_data.pkl")
        print("  - oak_camera/frames_metadata.json")
        return 1

    print(f"\n找到 {len(sessions)} 个有效session:")
    for i, session in enumerate(sessions[:10], 1):
        rel_path = session.relative_to(data_dir)
        print(f"  {i}. {rel_path}")

    if len(sessions) > 10:
        print(f"  ... 还有 {len(sessions) - 10} 个session")

    # Dry-run模式
    if args.dry_run:
        print("\n[DRY RUN] 不会实际处理，仅显示将要处理的session")
        return 0

    # 确认处理
    print(f"\n处理配置:")
    print(f"  并行处理: {'是' if args.parallel else '否'}")
    if args.parallel:
        print(f"  进程数: {args.workers}")
    print(f"  强制重新处理: {'是' if args.force else '否'}")
    print(f"  更新PKL文件: {'否' if args.skip_update_pkl else '是'}")

    try:
        input("\n按 Enter 开始处理，或 Ctrl+C 取消...")
    except KeyboardInterrupt:
        print("\n\n已取消")
        return 0

    # 开始批量处理
    start_time = datetime.now()

    if args.parallel:
        results = processor.process_batch_parallel(sessions, args.workers)
    else:
        results = processor.process_batch_serial(sessions)

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # 生成统计摘要
    summary = processor.generate_summary(results)

    # 显示摘要
    print("\n" + "="*80)
    print("处理完成")
    print("="*80)
    print(f"\n耗时: {duration:.1f} 秒")
    print(f"\n总session数:      {summary['total_sessions']}")
    print(f"成功处理:         {summary['successful']}")
    print(f"跳过 (已处理):    {summary['skipped']}")
    print(f"失败:             {summary['failed']}")
    print(f"总处理帧数:       {summary['total_frames_processed']}")
    print(f"有效距离测量数:   {summary['total_valid_distances']}")

    # 保存报告
    processor.save_report(results, summary, args.report)
    processor.save_json_report(results, summary, args.json_report)

    print("\n✓ 所有处理完成！")

    return 0 if summary['failed'] == 0 else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n错误: {e}")
        traceback.print_exc()
        sys.exit(1)
