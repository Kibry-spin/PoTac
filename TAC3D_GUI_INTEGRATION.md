# Tac3D GUI集成指南

本指南说明如何将Tac3D传感器集成到GUI界面中。

## 方法1：快速集成（推荐）

### 1. 在 `src/gui/main_window.py` 开头添加导入

```python
# 在文件顶部添加
from src.gui.tac3d_gui_extensions import (
    add_tac3d_panel_to_main_window,
    create_tac3d_control_button,
    update_tac3d_status_in_control_panel,
    add_tac3d_to_recording
)
```

### 2. 在 `create_control_panel()` 方法中添加Tac3D状态标签

在visuotactile sensor status label后添加：

```python
# 在 create_control_panel() 方法中
# 找到这行：
# self.vt_sensor_status_label = Label(text='VT Sensors: None connected', ...)

# 在它后面添加：
# Tac3D sensor status
self.tac3d_status_label = Label(
    text='Tac3D: None connected',
    size_hint_y=0.05,
    font_size='12sp',
    color=(1, 1, 0, 1)
)
status_layout.add_widget(self.tac3d_status_label)
```

### 3. 在 `create_control_bar()` 方法中添加Tac3D配置按钮

在 VT Sensor Config 按钮后添加：

```python
# 在 create_control_bar() 方法中
# 找到 VT Sensors 按钮代码后

# Tac3D Sensor Config
tac3d_config_button = create_tac3d_control_button(self)
control_bar.add_widget(tac3d_config_button)
```

### 4. 在 `update()` 方法中添加Tac3D状态更新

在 update_vt_sensor_status() 调用后添加：

```python
# 在 update() 方法中
# 找到：
# self.update_vt_sensor_status()

# 在它后面添加：
# Update Tac3D sensor status
update_tac3d_status_in_control_panel(self)
```

### 5. 在 `start_recording()` 方法中添加Tac3D传感器

在添加visuotactile sensors的代码后添加：

```python
# 在 start_recording() 方法中
# 找到添加 visuotactile sensors 的代码后

# Add all Tac3D sensors
tac3d_count = add_tac3d_to_recording(self, self.sync_recorder)

# 修改 total_sensors 计算
total_sensors = (1 if oak_added else 0) + vt_count + tac3d_count
```

## 方法2：完整手动集成

如果需要更精细的控制，可以参考 `src/gui/tac3d_gui_extensions.py` 中的实现，
手动将相应功能集成到 main_window.py 中。

## 测试步骤

1. 启动GUI应用
2. 点击底部的 "Tac3D Config" 按钮
3. 输入以下信息：
   - Sensor ID: tac3d_1
   - UDP Port: 9988
   - Name: Tac3D_Sensor
4. 点击 "Connect"
5. 确认控制面板显示 "Tac3D: [SN] @ [FPS] Hz"
6. 开始录制，确认Tac3D数据被保存

## 数据验证

录制后检查：
```bash
ls data/session_*/tac3d_1/
# 应该看到：
# - tac3d_1_data.npz
# - tac3d_1_metadata.json
```

读取数据：
```python
import numpy as np
data = np.load('data/session_xxx/tac3d_1/tac3d_1_data.npz')
print(f"Displacements shape: {data['displacements'].shape}")
print(f"Timestamps: {len(data['capture_timestamps'])} frames")
```

## 故障排除

### 问题：Import错误
```
ModuleNotFoundError: No module named 'src.gui.tac3d_gui_extensions'
```
确保文件 `src/gui/tac3d_gui_extensions.py` 存在

### 问题：连接失败
- 确认Tac3D传感器正在发送UDP数据
- 检查端口号是否正确（默认9988）
- 检查防火墙设置

### 问题：录制时没有Tac3D数据
- 确认传感器状态显示为绿色且有FPS
- 检查控制台日志是否有错误信息
- 确认 sensor_manager.py 已正确修改

## 文件位置总结

```
src/
├── sensors/
│   ├── tac3d_sensor.py           # Tac3D传感器类
│   └── sensor_manager.py         # 已修改：添加Tac3D支持
├── data/
│   ├── tac3d_data_recorder.py    # Tac3D数据记录器
│   └── synchronized_recorder.py  # 已修改：自动检测Tac3D
└── gui/
    ├── tac3d_gui_extensions.py   # Tac3D GUI扩展（新文件）
    └── main_window.py             # 需要修改：添加5处集成点
```

## 完整示例代码

参考 `test_tac3d_sensor.py` 了解如何使用Tac3D传感器API。
