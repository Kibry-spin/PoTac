# Tac3D传感器GUI集成完成

## ✅ 集成状态

Tac3D传感器已成功集成到PoTac GUI采集系统中！

## 📦 已完成的工作

### 1. 核心功能模块
- ✅ `src/sensors/tac3d_sensor.py` - Tac3D传感器接口类
- ✅ `src/sensors/sensor_manager.py` - 已集成Tac3D管理功能
- ✅ `src/data/tac3d_data_recorder.py` - Tac3D专用数据记录器
- ✅ `src/data/synchronized_recorder.py` - 已支持自动检测Tac3D传感器

### 2. GUI界面集成
- ✅ `src/gui/tac3d_gui_extensions.py` - GUI扩展模块
- ✅ `src/gui/main_window.py` - 已自动集成5个关键点：
  1. 导入Tac3D GUI扩展模块
  2. 添加Tac3D状态标签（控制面板）
  3. 添加Tac3D配置按钮（底部控制栏）
  4. 添加实时状态更新
  5. 添加到录制系统

### 3. 文档和工具
- ✅ `TAC3D_INTEGRATION_GUIDE.md` - 完整的集成使用文档
- ✅ `TAC3D_GUI_INTEGRATION.md` - GUI集成说明
- ✅ `config_with_tac3d_example.json` - 配置示例
- ✅ `test_tac3d_sensor.py` - 测试脚本
- ✅ `patch_tac3d_gui.py` - 自动集成脚本（已执行）

## 🚀 快速使用指南

### 启动GUI应用

```bash
cd /home/kirdo/robo/PoTac
python main.py
```

### 连接Tac3D传感器

1. **在GUI底部找到 "Tac3D Config" 按钮**（紫色按钮）
2. **点击打开配置对话框**
3. **填写传感器信息**：
   - Sensor ID: `tac3d_1`（或任意唯一ID）
   - UDP Port: `9988`（默认端口）
   - Name: `Tac3D_Sensor`（显示名称）
4. **点击 "Connect" 按钮**
5. **等待连接成功**，状态显示为绿色

### 查看传感器状态

在GUI右侧控制面板中，会显示：
```
Tac3D: [SN] @ [FPS] Hz
```
- 绿色：传感器正常工作
- 黄色：正在连接/等待数据
- 红色：连接错误

### 校准传感器

1. **确保传感器未接触任何物体**
2. 在配置对话框中输入Sensor ID
3. 点击 "Calibrate" 按钮
4. 等待校准完成

### 开始录制

1. **确保Tac3D传感器已连接**（状态显示为绿色）
2. 点击底部 **"Start Recording"** 按钮
3. 录制过程中，Tac3D数据会自动保存
4. 点击 **"Stop Recording"** 停止

### 查看录制数据

录制完成后，数据保存在：
```bash
data/
└── session_YYYYMMDD_HHMMSS/
    ├── oak_camera/              # OAK相机图像
    ├── vt_left/                 # 视触觉传感器
    └── tac3d_1/                 # Tac3D传感器 ⭐
        ├── tac3d_1_data.npz        # 位移数据
        └── tac3d_1_metadata.json   # 元数据
```

### 读取录制数据

```python
import numpy as np

# 加载数据
data = np.load('data/session_xxx/tac3d_1/tac3d_1_data.npz')

# 查看内容
print(f"Displacements: {data['displacements'].shape}")
print(f"Timestamps: {len(data['capture_timestamps'])}")
print(f"Sensor SN: {data['sensor_sn'][0]}")

# 分析位移
displacements = data['displacements']  # (N_frames, 400, 3)
timestamps = data['capture_timestamps']

# 计算每帧最大位移
import numpy as np
for i in range(len(displacements)):
    disp_magnitude = np.linalg.norm(displacements[i], axis=1)
    print(f"Frame {i}: Max = {disp_magnitude.max():.4f} mm")
```

## 🔧 配置文件（可选）

如果要开机自动连接Tac3D传感器，编辑 `config/settings.json`：

```json
{
  "tac3d_sensors": {
    "enabled": true,
    "sensors": [
      {
        "id": "tac3d_1",
        "port": 9988,
        "name": "Tac3D_Sensor",
        "config": {
          "auto_calibrate": false,
          "save_all_data": false
        }
      }
    ]
  }
}
```

## 📊 GUI界面说明

### 新增元素位置

1. **控制面板（右侧）**：
   - Tac3D状态标签（显示传感器SN和FPS）

2. **底部控制栏**：
   - "Tac3D Config" 按钮（紫色）

3. **配置对话框**：
   - 连接/断开传感器
   - 校准传感器
   - 查看已连接传感器列表

## ⚙️ 技术细节

### 数据同步

系统保存3种时间戳用于多传感器对齐：
- `send_timestamps`: Tac3D传感器发送时间
- `recv_timestamps`: UDP接收时间
- `capture_timestamps`: 系统捕获时间 ⭐（推荐用于对齐）

### 录制格式

- **相机传感器**：JPEG图像序列 + metadata.json
- **Tac3D传感器**：NPZ压缩数组 + metadata.json

### 录制速率

- OAK相机: 30 FPS
- 视触觉传感器: 30 FPS
- **Tac3D传感器: 100 FPS** ⭐（高速采集）

## 🧪 测试传感器

不使用GUI，直接测试Tac3D传感器：

```bash
cd /home/kirdo/robo/PoTac
python test_tac3d_sensor.py
```

测试包括：
1. 基本连接测试
2. 数据录制测试（5秒）
3. 校准功能测试

## 🆘 故障排除

### GUI启动失败

**错误**: ImportError
```
ModuleNotFoundError: No module named 'src.gui.tac3d_gui_extensions'
```

**解决**: 确认文件存在
```bash
ls src/gui/tac3d_gui_extensions.py
```

### 连接失败

**症状**: 点击Connect后显示"Failed to connect"

**解决**:
1. 确认Tac3D传感器已启动并发送UDP数据
2. 检查端口号是否正确（默认9988）
3. 检查防火墙：
   ```bash
   sudo ufw status
   sudo ufw allow 9988/udp
   ```
4. 测试网络连接：
   ```bash
   ping <传感器IP>
   ```

### 状态显示为黄色

**症状**: 连接后状态一直显示"waiting..."

**原因**: 未收到数据

**解决**:
1. 确认传感器正在发送UDP数据
2. 检查端口是否被其他程序占用：
   ```bash
   netstat -an | grep 9988
   ```
3. 重启传感器

### 录制时没有Tac3D数据

**症状**: 录制完成后没有tac3d_1目录

**解决**:
1. 确认传感器状态为绿色（有FPS显示）
2. 检查控制台日志是否有错误
3. 重新连接传感器后再录制

## 📚 相关文档

- `TAC3D_INTEGRATION_GUIDE.md` - 完整的技术文档
- `TAC3D_GUI_INTEGRATION.md` - GUI集成详细说明
- `README.md` - 主系统文档

## 🎯 下一步

1. **启动应用测试**:
   ```bash
   python main.py
   ```

2. **连接Tac3D传感器**:
   - 点击"Tac3D Config"按钮
   - 填写信息并连接

3. **录制测试数据**:
   - 开始录制
   - 触碰Tac3D传感器
   - 停止录制

4. **验证数据**:
   ```bash
   ls data/session_*/tac3d_1/
   python -c "import numpy as np; d=np.load('data/session_*/tac3d_1/tac3d_1_data.npz'); print(d.files)"
   ```

## 💡 提示

- 首次使用建议先用 `test_tac3d_sensor.py` 测试连接
- 录制前先校准传感器获得最佳效果
- Tac3D可以高速采集（100Hz），适合动态触觉分析
- 使用 `capture_timestamps` 与其他传感器数据对齐

---

**集成完成时间**: 2025-10-31
**状态**: ✅ 完全集成，可以使用
