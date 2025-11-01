# Tac3D触觉传感器集成指南

## 概述

PoTac多模态数据采集系统现已支持Tac3D远程触觉传感器，通过UDP协议接收位移数据并与其他传感器同步录制。

## 主要特性

- ✅ **UDP数据接收**：通过配置的端口接收Tac3D传感器数据
- ✅ **时间戳对齐**：保存接收时间戳用于多传感器数据对齐
- ✅ **高速采集**：支持100Hz采集频率
- ✅ **位移数据保存**：自动保存displacement数据为NPZ格式
- ✅ **远程校准**：支持通过UDP发送校准信号
- ✅ **同步录制**：与OAK相机、视触觉传感器同步录制

## 安装要求

1. **PyTac3D SDK**（已安装在 `/home/kirdo/robo/PoTac/Tac3d/Tac3D-SDK-v3.2.1/Tac3D-API/python/PyTac3D`）

2. **依赖项**：
   ```bash
   pip install numpy
   ```

## 快速开始

### 1. 基本使用

```python
from src.sensors.tac3d_sensor import Tac3DSensor

# 创建传感器（默认端口9988）
sensor = Tac3DSensor(port=9988, name="My_Tac3D")

# 初始化
sensor.initialize()

# 启动（会等待连接）
sensor.start()

# 获取数据
frame_data = sensor.get_frame()
if frame_data:
    print(f"Sensor SN: {frame_data['SN']}")
    print(f"Frame index: {frame_data['index']}")
    print(f"Recv timestamp: {frame_data['recv_timestamp']}")
    print(f"Displacements shape: {frame_data['displacements'].shape}")

# 停止
sensor.stop()
```

### 2. 配置Tac3D传感器

在配置文件中添加（如 `config.json`）：

```json
{
  "tac3d_sensors": {
    "enabled": true,
    "sensors": [
      {
        "id": "tac3d_finger",
        "port": 9988,
        "name": "Tac3D_Finger",
        "config": {
          "max_queue_size": 5,
          "auto_calibrate": false,
          "save_all_data": false
        }
      }
    ]
  }
}
```

**配置参数说明**：
- `port`: UDP接收端口（默认9988）
- `max_queue_size`: PyTac3D内部队列大小
- `auto_calibrate`: 启动时是否自动校准
- `calibrate_delay`: 自动校准延迟时间（秒）
- `save_all_data`: 是否保存力、力矩数据（默认false，仅保存displacement）

### 3. 集成到采集系统

```python
from src.sensors.tac3d_sensor import Tac3DSensor
from src.data.synchronized_recorder import SynchronizedRecorder

# 创建传感器
tac3d = Tac3DSensor(port=9988, name="Tac3D_Sensor")
tac3d.initialize()
tac3d.start()

# 创建录制器
recorder = SynchronizedRecorder(
    output_dir="./data",
    session_name="multi_sensor_session"
)

# 添加Tac3D传感器
recorder.add_sensor(
    sensor_id="tac3d_sensor",
    sensor_name="Tac3D_Finger",
    sensor_object=tac3d,
    fps=100  # Tac3D高速采集
)

# 添加其他传感器（OAK相机、视触觉传感器等）
# ...

# 开始录制
recorder.start_recording()

# 录制中...
time.sleep(10)

# 停止录制
recorder.stop_recording()
```

### 4. 校准传感器

```python
# 确保传感器未接触任何物体
sensor.calibrate()
```

## 数据格式

### 录制输出

录制后，Tac3D数据保存在：
```
data/
└── session_YYYYMMDD_HHMMSS/
    └── tac3d_sensor/
        ├── tac3d_sensor_data.npz      # 位移数据
        └── tac3d_sensor_metadata.json # 元数据
```

### NPZ文件结构

```python
import numpy as np

data = np.load('tac3d_sensor_data.npz')

# 主要数据
displacements = data['displacements']       # Shape: (N_frames, N_points, 3)
positions = data['positions']               # Shape: (N_frames, N_points, 3)

# 时间戳（用于对齐）
frame_indices = data['frame_indices']       # 帧序号
send_timestamps = data['send_timestamps']   # 传感器发送时间戳
recv_timestamps = data['recv_timestamps']   # UDP接收时间戳
capture_timestamps = data['capture_timestamps']  # 系统捕获时间戳

# 元数据
sensor_sn = str(data['sensor_sn'][0])      # 传感器序列号
total_frames = int(data['total_frames'])    # 总帧数
```

### 时间戳说明

系统保存3种时间戳用于数据对齐：

1. **send_timestamp**: 传感器发送数据的时间戳（来自Tac3D传感器）
2. **recv_timestamp**: PyTac3D接收UDP数据的时间戳
3. **capture_timestamps**: 录制系统捕获数据的时间戳

**推荐使用 `capture_timestamps` 与其他传感器对齐**，因为它与其他传感器使用相同的系统时钟。

## 读取录制数据

```python
import numpy as np

# 加载数据
data = np.load('data/session_xxx/tac3d_sensor/tac3d_sensor_data.npz')

displacements = data['displacements']  # (N_frames, 400, 3) for 20x20 grid
timestamps = data['capture_timestamps']

# 分析位移数据
for i in range(len(displacements)):
    disp = displacements[i]
    disp_magnitude = np.linalg.norm(disp, axis=1)
    max_disp = disp_magnitude.max()
    print(f"Frame {i}: Max displacement = {max_disp:.6f} mm")
```

## 测试脚本

运行测试脚本验证集成：

```bash
cd /home/kirdo/robo/PoTac
python test_tac3d_sensor.py
```

测试包括：
1. 基本连接测试
2. 数据录制测试
3. 校准功能测试

## 网络配置

### 本地传感器（默认）

传感器和采集系统在同一台机器上，使用默认端口9988。

### 远程传感器

如果Tac3D传感器在另一台机器上：

1. **传感器端**：配置UDP发送目标为采集系统的IP地址
2. **采集系统端**：在防火墙中开放UDP端口
   ```bash
   sudo ufw allow 9988/udp
   ```

## 故障排除

### 问题：传感器连接超时

**症状**：`Connection timeout - no data received`

**解决方案**：
1. 检查传感器是否正常工作
2. 验证网络连接：`ping <传感器IP>`
3. 检查防火墙设置
4. 确认UDP端口号正确

### 问题：数据帧率低

**症状**：FPS远低于预期

**解决方案**：
1. 增大 `max_queue_size`
2. 确保网络带宽充足
3. 检查系统负载

### 问题：时间戳不对齐

**症状**：多传感器数据时间戳差异大

**解决方案**：
1. 使用 `capture_timestamps` 而不是 `recv_timestamps`
2. 确保所有传感器在同一台机器上，或使用NTP同步

## 性能优化

### 高速采集（100Hz）

```python
recorder.add_sensor(
    sensor_id="tac3d_sensor",
    sensor_name="Tac3D",
    sensor_object=tac3d,
    fps=100  # 高速采集
)
```

### 减少数据量

只保存displacement，不保存force和moment：

```python
sensor = Tac3DSensor(
    port=9988,
    config={'save_all_data': False}  # 默认配置
)
```

## API参考

### Tac3DSensor 类

**初始化参数**：
- `port` (int): UDP端口，默认9988
- `name` (str): 传感器名称
- `config` (dict): 配置字典

**主要方法**：
- `initialize()`: 初始化传感器连接
- `start()`: 开始接收数据
- `stop()`: 停止接收数据
- `get_frame()`: 获取最新数据帧
- `calibrate()`: 发送校准信号
- `get_status()`: 获取传感器状态
- `get_device_info()`: 获取设备信息

**返回的数据帧结构**：
```python
{
    'SN': str,                    # 传感器序列号
    'index': int,                 # 帧序号
    'send_timestamp': float,      # 发送时间戳
    'recv_timestamp': float,      # 接收时间戳
    'positions': np.ndarray,      # 3D位置 (N_points, 3)
    'displacements': np.ndarray,  # 3D位移 (N_points, 3)
}
```

## 与GUI集成

要在GUI中添加Tac3D传感器支持，需要修改：

1. **src/gui/main_window.py**: 添加Tac3D传感器选项卡
2. **config.json**: 添加tac3d_sensors配置
3. 在录制时添加传感器到SynchronizedRecorder

参考视触觉传感器的实现方式。

## 相关文档

- [PyTac3D SDK文档](../Tac3d/Tac3D-SDK-v3.2.1/Tac3D-API/python/PyTac3D/)
- [主系统README](./README.md)
- [配置文件示例](./config_with_tac3d_example.json)

---

**创建时间**: 2025-10-31
**适用版本**: PoTac v1.0+, PyTac3D v3.2.1+
