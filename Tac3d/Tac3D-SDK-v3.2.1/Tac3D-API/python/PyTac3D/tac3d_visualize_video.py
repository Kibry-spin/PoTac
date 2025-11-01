#!/usr/bin/env python3
"""
Tac3D位移数据可视化脚本
从HDF5/NPZ文件读取displacement数据，生成2D热图视频
"""

import h5py
import numpy as np
import cv2
from pathlib import Path
from datetime import datetime
import argparse


class Tac3DVideoVisualizer:
    """Tac3D位移数据视频可视化器"""

    def __init__(self, data_file, output_path=None, fps=30, width=800, height=600):
        """
        初始化可视化器

        Args:
            data_file: 输入数据文件路径（HDF5或NPZ）
            output_path: 输出视频路径，None则自动生成
            fps: 输出视频帧率
            width: 视频宽度
            height: 视频高度
        """
        self.data_file = Path(data_file)
        self.output_path = output_path
        self.fps = fps
        self.image_width = width
        self.image_height = height
        self.colormap = cv2.COLORMAP_JET

        # 数据容器
        self.displacements = None
        self.positions = None
        self.frame_indices = None
        self.send_timestamps = None
        self.recv_timestamps = None
        self.sensor_sn = ''
        self.total_frames = 0

        print(f'初始化Tac3D视频可视化器...')
        print(f'  输入文件: {self.data_file}')
        print(f'  输出尺寸: {width}x{height}')
        print(f'  输出帧率: {fps} FPS')

    def load_data(self):
        """加载数据文件"""
        if not self.data_file.exists():
            raise FileNotFoundError(f'数据文件不存在: {self.data_file}')

        file_ext = self.data_file.suffix.lower()

        if file_ext == '.h5':
            self._load_hdf5()
        elif file_ext == '.npz':
            self._load_npz()
        else:
            raise ValueError(f'不支持的文件格式: {file_ext}')

        print(f'✓ 数据加载完成')
        print(f'  传感器SN: {self.sensor_sn}')
        print(f'  总帧数: {self.total_frames}')
        print(f'  位移数据形状: {self.displacements.shape}')
        print(f'  测量点数量: {self.displacements.shape[1]}')

    def _load_hdf5(self):
        """加载HDF5格式数据"""
        with h5py.File(self.data_file, 'r') as f:
            self.displacements = f['displacements'][:]

            # 尝试加载位置数据
            if 'positions' in f:
                self.positions = f['positions'][:]

            self.frame_indices = f['frame_indices'][:]
            self.send_timestamps = f['send_timestamps'][:]
            self.recv_timestamps = f['recv_timestamps'][:]

            # 读取元数据
            self.sensor_sn = f['metadata'].attrs['sensor_sn']
            self.total_frames = f['metadata'].attrs['total_frames']

    def _load_npz(self):
        """加载NPZ格式数据"""
        data = np.load(self.data_file)

        self.displacements = data['displacements']

        # 尝试加载位置数据
        if 'positions' in data:
            self.positions = data['positions']

        self.frame_indices = data['frame_indices']
        self.send_timestamps = data['send_timestamps']
        self.recv_timestamps = data['recv_timestamps']

        # 读取元数据
        self.sensor_sn = str(data['sensor_sn'][0])
        self.total_frames = int(data['total_frames'])

    def create_displacement_image(self, frame_idx, global_max):
        """
        创建单帧位移热图（20×20网格，简洁版）

        Args:
            frame_idx: 帧索引
            global_max: 全局最大位移值（用于归一化）

        Returns:
            numpy.ndarray: BGR格式图像
        """
        # 获取当前帧的位移数据
        displacements = self.displacements[frame_idx]

        # 计算位移幅值
        disp_magnitude = np.linalg.norm(displacements, axis=1)

        # 假设数据是20×20的网格（400个点）
        nx, ny = 20, 20
        if len(disp_magnitude) != nx * ny:
            raise ValueError(f'数据点数量({len(disp_magnitude)})不是20×20=400个点')

        # Reshape为20×20网格
        disp_grid = disp_magnitude.reshape(ny, nx)

        # 使用全局最大值归一化到0-255
        if global_max > 0:
            disp_norm = (disp_grid / global_max * 255).astype(np.uint8)
        else:
            disp_norm = np.zeros_like(disp_grid, dtype=np.uint8)

        # 放大到目标分辨率（使用双线性插值使其平滑）
        disp_resized = cv2.resize(disp_norm, (self.image_width, self.image_height),
                                  interpolation=cv2.INTER_LINEAR)

        # 应用色图
        colored_image = cv2.applyColorMap(disp_resized, self.colormap)

        return colored_image

    def generate_video(self):
        """生成视频"""
        # 确定输出路径
        if self.output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.output_path = self.data_file.parent / f'tac3d_video_{timestamp}.mp4'
        else:
            self.output_path = Path(self.output_path)

        print(f'\n开始生成视频...')
        print(f'  输出路径: {self.output_path}')

        # 计算全局最大位移值（整个视频）
        print(f'  计算全局最大位移值...')
        all_magnitudes = np.linalg.norm(self.displacements, axis=2)  # Shape: (N_frames, N_points)
        global_max = all_magnitudes.max()
        print(f'  ✓ 全局最大位移: {global_max:.6f} mm')

        # 创建VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(
            str(self.output_path),
            fourcc,
            self.fps,
            (self.image_width, self.image_height)
        )

        if not video_writer.isOpened():
            raise RuntimeError('无法创建视频写入器')

        # 生成每一帧
        for i in range(self.total_frames):
            try:
                image = self.create_displacement_image(i, global_max)
                video_writer.write(image)

                # 进度显示
                if (i + 1) % 10 == 0 or i == self.total_frames - 1:
                    progress = (i + 1) / self.total_frames * 100
                    print(f'\r  进度: {i+1}/{self.total_frames} ({progress:.1f}%)',
                          end='', flush=True)

            except Exception as e:
                print(f'\n⚠ 警告: 第{i}帧处理失败: {e}')
                continue

        video_writer.release()
        print(f'\n✓ 视频生成完成: {self.output_path}')

        # 显示视频信息
        duration = self.total_frames / self.fps
        print(f'\n视频信息:')
        print(f'  总帧数: {self.total_frames}')
        print(f'  帧率: {self.fps} FPS')
        print(f'  时长: {duration:.2f} 秒')
        print(f'  分辨率: {self.image_width}x{self.image_height}')
        print(f'  全局最大位移: {global_max:.6f} mm (红色)')

        return self.output_path


def main():
    parser = argparse.ArgumentParser(
        description='Tac3D位移数据可视化 - 生成2D热图视频',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本使用
  python tac3d_visualize_video.py data.h5

  # 指定输出路径和帧率
  python tac3d_visualize_video.py data.h5 --output result.mp4 --fps 60

  # 自定义分辨率
  python tac3d_visualize_video.py data.h5 --width 1280 --height 720

  # 使用NPZ文件
  python tac3d_visualize_video.py data.npz
        """
    )

    parser.add_argument('input', type=str,
                       help='输入数据文件 (HDF5或NPZ格式)')
    parser.add_argument('--output', type=str, default=None,
                       help='输出视频路径（默认自动生成）')
    parser.add_argument('--fps', type=int, default=30,
                       help='视频帧率 (默认: 30)')
    parser.add_argument('--width', type=int, default=800,
                       help='视频宽度 (默认: 800)')
    parser.add_argument('--height', type=int, default=600,
                       help='视频高度 (默认: 600)')

    args = parser.parse_args()

    try:
        # 创建可视化器
        visualizer = Tac3DVideoVisualizer(
            data_file=args.input,
            output_path=args.output,
            fps=args.fps,
            width=args.width,
            height=args.height
        )

        # 加载数据
        visualizer.load_data()

        # 生成视频
        visualizer.generate_video()

        print('\n✓ 完成')
        return 0

    except Exception as e:
        print(f'\n错误: {e}')
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
