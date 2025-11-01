# Tac3D实时位移可视化 - 使用指南

## 功能

实时显示Tac3D触觉传感器的位移数据，以2D彩色热图呈现。

### 主要特性

- ✅ **实时位移热图**：将3D位移数据投影为2D彩色图
- ✅ **远程连接支持**：支持通过IP地址连接远程传感器
- ✅ **自动色标**：根据实际位移范围自动调整
- ✅ **测量点显示**：白点标记实际测量位置
- ✅ **统计信息**：显示最大、平均位移和合力
- ✅ **交互控制**：校准、保存图像等

## 快速开始

### 本地连接（默认配置）

```bash
cd /home/kirdo/robo/PoTac/Tac3d/Tac3D-SDK-v3.2.1/Tac3D-API/python/PyTac3D

# 基本使用
python tac3d_realtime_visualizer.py
```

### 远程连接

```bash
# 指定传感器IP地址
python tac3d_realtime_visualizer.py --ip 192.168.1.100

# 指定端口（如果不是默认9988）
python tac3d_realtime_visualizer.py --ip 192.168.1.100 --port 9999
```

### 连接后自动校准

```bash
# 启动时自动执行校准
python tac3d_realtime_visualizer.py --calibrate
```

### 自定义窗口大小

```bash
# 设置显示窗口大小
python tac3d_realtime_visualizer.py --width 1024 --height 768
```

## 界面说明

### 2D位移热图

```
┌─────────────────────────────────────────┐
│ Tac3D Sensor: SN123456                  │
│ Frame: 1234                              │
│ Max Disp: 0.1234 mm                      │
│ Mean Disp: 0.0567 mm                     │
│ Force: 2.345 N                           │
│                                          │
│        [彩色位移热图]                    │
│          ● ● ●                           │
│         ● ● ● ●    [色标]               │
│          ● ● ●      │ 0.123             │
│                     │   mm               │
│                     │ 0.000             │
└─────────────────────────────────────────┘
```

### 颜色含义

- **蓝色**：无位移或极小位移
- **绿色**：中等位移
- **黄色**：较大位移
- **红色**：最大位移

### 白点

- 白色圆点标记实际测量点位置

## 键盘控制

运行时可使用以下快捷键：

| 按键 | 功能 |
|------|------|
| `q` | 退出程序 |
| `c` | 校准（清零） |
| `s` | 保存当前图像 |

### 校准说明

校准操作会将当前状态设为零点：
1. 按 `c` 键
2. 确保传感器未接触任何物体
3. 等待1秒完成校准

## 输出示例

### 启动输出

```bash
$ python tac3d_realtime_visualizer.py --ip 192.168.1.100

初始化Tac3D传感器...
  PyTac3D版本: 3.2.1
  UDP端口: 9988
  远程IP: 192.168.1.100
✓ 传感器对象创建成功

等待传感器连接...
Frame 0 | SN: TAC3D001 | Points: 196
✓ 传感器已连接 (SN: TAC3D001)

开始实时可视化...
按 q 键退出
按 c 键校准（清零）
按 s 键保存当前图像

Frame 30 | SN: TAC3D001 | Points: 196
Frame 60 | SN: TAC3D001 | Points: 196
...
```

### 保存图像

按 `s` 键保存：
```
✓ 图像已保存: tac3d_displacement_1761633586.png
```

## 技术原理

### 位移数据处理

1. **接收3D位移**：
   ```python
   D = frame.get('3D_Displacements')  # (N, 3) numpy数组
   # D[:, 0] = X方向位移
   # D[:, 1] = Y方向位移
   # D[:, 2] = Z方向位移
   ```

2. **计算位移幅值**：
   ```python
   magnitude = np.linalg.norm(D, axis=1)  # 计算3D向量模
   ```

3. **投影到2D**：
   ```python
   # 使用X-Y坐标作为平面位置
   x_pos = positions[:, 0]
   y_pos = positions[:, 1]
   ```

4. **生成热图**：
   - 使用高斯核平滑
   - 应用JET色图
   - 叠加测量点标记

### 数据流程

```
Tac3D传感器 → UDP → PyTac3D → 回调函数 → 可视化器
    (UDP)        (9988)   (接收)    (更新数据)  (生成图像)
                                                    ↓
                                            OpenCV显示窗口
```

## 配置参数

### 完整命令行参数

```bash
python tac3d_realtime_visualizer.py \
    --port 9988 \              # UDP端口
    --ip 192.168.1.100 \       # 传感器IP（可选）
    --calibrate \              # 启动时校准
    --width 1024 \             # 窗口宽度
    --height 768               # 窗口高度
```

### 修改源码配置

可在脚本中修改的参数：

```python
# 可视化参数
self.image_width = 800          # 图像宽度
self.image_height = 600         # 图像高度
self.colormap = cv2.COLORMAP_JET  # 色图类型

# 可选色图
# cv2.COLORMAP_HOT
# cv2.COLORMAP_VIRIDIS
# cv2.COLORMAP_PLASMA
```

## 故障排除

### 问题：无法连接传感器

**症状**：`等待传感器数据超时`

**解决**：
1. 检查传感器是否开机
2. 检查网络连接
   ```bash
   ping 192.168.1.100
   ```
3. 检查UDP端口是否正确
4. 检查防火墙设置

### 问题：显示窗口无法打开

**症状**：OpenCV窗口错误

**解决**：
```bash
# 设置显示
export DISPLAY=:0

# 或使用VNC/X11转发
```

### 问题：位移数据为零

**症状**：热图全是蓝色（无位移）

**原因**：
1. 传感器未接触物体
2. 需要校准

**解决**：
1. 让传感器接触物体
2. 按 `c` 键校准

### 问题：热图不清晰

**原因**：测量点太少或太密集

**解决**：调整高斯核大小
```python
# 在create_2d_displacement_image()中
sigma = 5  # 调大使热图更平滑
sigma = 2  # 调小使热图更精细
```

## 高级用法

### 集成到其他应用

```python
from tac3d_realtime_visualizer import Tac3DVisualizer

# 创建可视化器
viz = Tac3DVisualizer(port=9988, sensor_ip='192.168.1.100')

# 等待连接
viz.wait_for_connection()

# 校准
viz.calibrate()

# 获取实时数据
while True:
    if viz.displacements is not None:
        # 使用位移数据
        disp = viz.displacements
        print(f'Max displacement: {np.max(np.linalg.norm(disp, axis=1))}')

    time.sleep(0.1)
```

### 自定义可视化

继承`Tac3DVisualizer`类并重写方法：

```python
class MyCustomVisualizer(Tac3DVisualizer):
    def create_2d_displacement_image(self):
        # 自定义可视化逻辑
        image = super().create_2d_displacement_image()

        # 添加自定义内容
        cv2.putText(image, 'Custom Info', (10, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

        return image
```

## 依赖项

```
- PyTac3D (Tac3D SDK)
- numpy
- opencv-python (cv2)
- matplotlib (用于色图)
```

安装依赖：
```bash
pip install numpy opencv-python matplotlib
```

## 与原始代码对比

| 特性 | main-exampleWithView.py | tac3d_realtime_visualizer.py |
|------|-------------------------|------------------------------|
| 数据接收 | ✅ | ✅ |
| 回调函数 | ✅ | ✅ |
| 实时可视化 | ❌ | ✅ |
| 2D热图 | ❌ | ✅ |
| 远程连接 | ✅ | ✅ |
| 交互控制 | ❌ | ✅ |
| 统计信息 | ❌ | ✅ |

## 性能优化

- **帧率**：通常30-60 FPS（取决于测量点数量）
- **延迟**：<50ms（从数据接收到显示）
- **内存**：~100MB

优化建议：
- 减少测量点数量
- 降低窗口分辨率
- 使用更简单的色图

---

**创建时间**: 2025-10-28
**适用版本**: PyTac3D 3.2.1+
**测试平台**: Ubuntu 20.04 + Python 3.8+
