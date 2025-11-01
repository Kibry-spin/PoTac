#!/usr/bin/env python3
"""
Tac3D位移数据录制脚本
仅保存displacement数据为HDF5/NPZ格式
"""

import PyTac3D
import time
import numpy as np
import h5py
from pathlib import Path
from datetime import datetime
import threading


class Tac3DRecorder:
    """Tac3D位移数据录制器"""

    def __init__(self, port=9988, output_dir='./tac3d_data'):
        """
        初始化录制器

        Args:
            port: UDP接收端口
            output_dir: 数据保存目录
        """
        self.port = port
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 传感器信息
        self.sensor_sn = ''

        # 录制状态
        self.recording = False
        self.record_lock = threading.Lock()

        # 录制数据
        self.displacements_list = []  # 位移数据列表
        self.positions_list = []  # 位置数据列表（可选）
        self.frame_indices = []  # 帧序号
        self.send_timestamps = []  # 发送时间戳
        self.recv_timestamps = []  # 接收时间戳

        # 统计
        self.total_frames = 0
        self.recorded_frames = 0

        print(f'初始化Tac3D录制器...')
        print(f'  PyTac3D版本: {PyTac3D.PYTAC3D_VERSION}')
        print(f'  UDP端口: {self.port}')
        print(f'  保存目录: {self.output_dir}')

        # 创建传感器对象
        self.sensor = PyTac3D.Sensor(
            recvCallback=self._data_callback,
            port=self.port,
            maxQSize=100,  # 增大队列以防丢帧
            callbackParam='Tac3D Recorder'
        )

        print('✓ 传感器对象创建成功')

    def _data_callback(self, frame, param):
        """数据接收回调函数"""
        # 更新传感器信息
        self.sensor_sn = frame['SN']
        self.total_frames += 1

        # 如果正在录制，保存数据
        if self.recording:
            with self.record_lock:
                # 获取位移数据
                displacements = frame.get('3D_Displacements')
                positions = frame.get('3D_Positions')

                if displacements is not None:
                    self.displacements_list.append(displacements.copy())

                    # 同时保存位置（用于后续分析）
                    if positions is not None:
                        self.positions_list.append(positions.copy())

                    # 保存元数据
                    self.frame_indices.append(frame['index'])
                    self.send_timestamps.append(frame['sendTimestamp'])
                    self.recv_timestamps.append(frame['recvTimestamp'])

                    self.recorded_frames += 1

                    # 每50帧打印一次进度
                    if self.recorded_frames % 50 == 0:
                        print(f"\r录制中... 已录制 {self.recorded_frames} 帧", end='', flush=True)

    def wait_for_connection(self, timeout=10):
        """等待传感器连接"""
        print('\n等待传感器连接...')
        self.sensor.waitForFrame()

        start_time = time.time()
        while not self.sensor_sn:
            time.sleep(0.1)
            if time.time() - start_time > timeout:
                raise TimeoutError(f'等待传感器连接超时 ({timeout}秒)')

        print(f'✓ 传感器已连接 (SN: {self.sensor_sn})')
        return True

    def calibrate(self, wait_time=2):
        """校准传感器"""
        if not self.sensor_sn:
            print('⚠ 传感器尚未连接，无法校准')
            return False

        print(f'\n准备校准，请确保传感器未接触物体...')
        print(f'等待 {wait_time} 秒...')
        time.sleep(wait_time)

        print('发送校准信号...')
        self.sensor.calibrate(self.sensor_sn)

        print('✓ 校准完成')
        time.sleep(1)
        return True

    def start_recording(self):
        """开始录制"""
        if self.recording:
            print('⚠ 已在录制中')
            return False

        with self.record_lock:
            # 清空之前的数据
            self.displacements_list = []
            self.positions_list = []
            self.frame_indices = []
            self.send_timestamps = []
            self.recv_timestamps = []
            self.recorded_frames = 0

            self.recording = True

        print('\n✓ 开始录制...')
        return True

    def stop_recording(self):
        """停止录制"""
        if not self.recording:
            print('⚠ 未在录制中')
            return False

        self.recording = False
        print(f'\n✓ 停止录制')
        print(f'  已录制 {self.recorded_frames} 帧')

        return True

    def save_hdf5(self, filename=None):
        """
        保存为HDF5格式

        Args:
            filename: 输出文件名（不含扩展名）
        """
        if self.recorded_frames == 0:
            print('⚠ 没有录制数据，无法保存')
            return None

        # 生成文件名
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'tac3d_{self.sensor_sn}_{timestamp}'

        filepath = self.output_dir / f'{filename}.h5'

        print(f'\n保存数据到HDF5: {filepath}')

        with h5py.File(filepath, 'w') as f:
            # 创建元数据组
            metadata = f.create_group('metadata')
            metadata.attrs['sensor_sn'] = self.sensor_sn
            metadata.attrs['total_frames'] = self.recorded_frames
            metadata.attrs['recording_date'] = datetime.now().isoformat()
            metadata.attrs['pytac3d_version'] = PyTac3D.PYTAC3D_VERSION

            # 保存时间戳
            f.create_dataset('frame_indices', data=np.array(self.frame_indices))
            f.create_dataset('send_timestamps', data=np.array(self.send_timestamps))
            f.create_dataset('recv_timestamps', data=np.array(self.recv_timestamps))

            # 保存位移数据 (shape: [N_frames, N_points, 3])
            displacements_array = np.array(self.displacements_list)
            f.create_dataset('displacements', data=displacements_array, compression='gzip')

            # 保存位置数据（如果有）
            if len(self.positions_list) > 0:
                positions_array = np.array(self.positions_list)
                f.create_dataset('positions', data=positions_array, compression='gzip')

            print(f'  位移数据形状: {displacements_array.shape}')
            print(f'  数据点数量: {displacements_array.shape[1]}')
            print(f'  录制帧数: {displacements_array.shape[0]}')

        print(f'✓ 保存成功: {filepath}')
        return filepath

    def save_npz(self, filename=None):
        """
        保存为NPZ格式（NumPy压缩格式）

        Args:
            filename: 输出文件名（不含扩展名）
        """
        if self.recorded_frames == 0:
            print('⚠ 没有录制数据，无法保存')
            return None

        # 生成文件名
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'tac3d_{self.sensor_sn}_{timestamp}'

        filepath = self.output_dir / f'{filename}.npz'

        print(f'\n保存数据到NPZ: {filepath}')

        # 转换为numpy数组
        displacements_array = np.array(self.displacements_list)

        # 准备保存的数据
        save_dict = {
            'displacements': displacements_array,
            'frame_indices': np.array(self.frame_indices),
            'send_timestamps': np.array(self.send_timestamps),
            'recv_timestamps': np.array(self.recv_timestamps),
            'sensor_sn': np.array([self.sensor_sn], dtype='U'),  # 字符串
            'total_frames': self.recorded_frames
        }

        # 添加位置数据（如果有）
        if len(self.positions_list) > 0:
            save_dict['positions'] = np.array(self.positions_list)

        # 保存
        np.savez_compressed(filepath, **save_dict)

        print(f'  位移数据形状: {displacements_array.shape}')
        print(f'  数据点数量: {displacements_array.shape[1]}')
        print(f'  录制帧数: {displacements_array.shape[0]}')
        print(f'✓ 保存成功: {filepath}')

        return filepath

    def interactive_record(self, duration=None, auto_save=True, save_format='hdf5'):
        """
        交互式录制

        Args:
            duration: 录制时长（秒），None表示手动停止
            auto_save: 是否自动保存
            save_format: 保存格式 ('hdf5' 或 'npz')
        """
        print('\n' + '='*60)
        print('交互式录制模式')
        print('='*60)
        print('命令:')
        print('  r - 开始录制')
        print('  s - 停止录制')
        print('  c - 校准')
        print('  q - 退出')
        print('='*60)

        try:
            while True:
                cmd = input('\n输入命令: ').strip().lower()

                if cmd == 'r':
                    self.start_recording()
                    if duration:
                        print(f'将录制 {duration} 秒...')
                        time.sleep(duration)
                        self.stop_recording()
                        if auto_save:
                            if save_format == 'hdf5':
                                self.save_hdf5()
                            else:
                                self.save_npz()
                    else:
                        print('录制中... (输入 s 停止)')

                elif cmd == 's':
                    self.stop_recording()
                    if auto_save and self.recorded_frames > 0:
                        if save_format == 'hdf5':
                            self.save_hdf5()
                        else:
                            self.save_npz()

                elif cmd == 'c':
                    self.calibrate()

                elif cmd == 'q':
                    if self.recording:
                        print('正在录制中，先停止录制...')
                        self.stop_recording()
                        if auto_save and self.recorded_frames > 0:
                            if save_format == 'hdf5':
                                self.save_hdf5()
                            else:
                                self.save_npz()
                    print('退出...')
                    break

                else:
                    print('无效命令')

        except KeyboardInterrupt:
            print('\n\n检测到Ctrl+C，退出...')
            if self.recording:
                self.stop_recording()
                if auto_save and self.recorded_frames > 0:
                    if save_format == 'hdf5':
                        self.save_hdf5()
                    else:
                        self.save_npz()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Tac3D位移数据录制脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互式录制（HDF5格式）
  python tac3d_record_displacement.py

  # 自动录制10秒（NPZ格式）
  python tac3d_record_displacement.py --duration 10 --format npz

  # 指定输出目录
  python tac3d_record_displacement.py --output ./my_data

  # 远程连接
  python tac3d_record_displacement.py --port 9988
        """
    )

    parser.add_argument('--port', type=int, default=9988,
                       help='UDP接收端口 (默认: 9988)')
    parser.add_argument('--output', type=str, default='./tac3d_data',
                       help='数据保存目录 (默认: ./tac3d_data)')
    parser.add_argument('--duration', type=float, default=None,
                       help='自动录制时长（秒），不指定则手动控制')
    parser.add_argument('--format', type=str, default='hdf5',
                       choices=['hdf5', 'npz'],
                       help='保存格式 (默认: hdf5)')
    parser.add_argument('--calibrate', action='store_true',
                       help='连接后自动校准')
    parser.add_argument('--filename', type=str, default=None,
                       help='输出文件名（不含扩展名）')

    args = parser.parse_args()

    try:
        # 创建录制器
        recorder = Tac3DRecorder(
            port=args.port,
            output_dir=args.output
        )

        # 等待连接
        recorder.wait_for_connection(timeout=30)

        # 可选：自动校准
        if args.calibrate:
            recorder.calibrate(wait_time=2)

        # 根据是否指定duration选择模式
        if args.duration is not None:
            # 自动录制模式
            print(f'\n自动录制模式: {args.duration} 秒')
            recorder.start_recording()
            time.sleep(args.duration)
            recorder.stop_recording()

            # 保存
            if args.format == 'hdf5':
                recorder.save_hdf5(args.filename)
            else:
                recorder.save_npz(args.filename)
        else:
            # 交互式模式
            recorder.interactive_record(save_format=args.format)

        print('\n✓ 录制完成')

    except Exception as e:
        print(f'\n错误: {e}')
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
