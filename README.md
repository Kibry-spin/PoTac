# PoTac - 多模态数据采集系统

一个集成OAK相机、视触觉传感器(VT)和Tac3D触觉传感器的多模态数据采集系统，支持ArUco标记距离控制的自动录制和语音提示。

## 系统架构

```
PoTac/
├── src/                          # 源代码
│   ├── sensors/                  # 传感器驱动
│   │   ├── oak_camera.py         # OAK-D相机（RGB + ArUco检测）
│   │   ├── vt_sensor.py          # 视触觉传感器（visuotactile）
│   │   └── tac3d_sensor.py       # Tac3D触觉传感器（PyTac3D）
│   ├── data/                     # 数据管理
│   │   ├── synchronized_recorder.py  # 多传感器同步录制
│   │   ├── auto_recorder.py      # 基于距离的自动录制
│   │   └── tac3d_data_recorder.py    # Tac3D数据录制
│   ├── gui/                      # 图形界面
│   │   └── main_window.py        # 主窗口（Kivy）
│   ├── vision/                   # 视觉算法
│   │   └── aruco_detector_optimized.py  # ArUco检测
│   └── utils/                    # 工具类
│       └── voice_manager.py      # 语音提示管理
├── Tools/                        # 实用脚本 ⭐
├── config/                       # 配置文件
│   └── settings.json            # 系统配置
├── Assets/                       # 资源文件
│   └── Potac-Voice/             # 语音素材
└── data/                         # 录制数据存储
    └── session_YYYYMMDD_HHMMSS/ # 按时间组织的session
```

### 核心组件

| 组件 | 功能 | 文件 |
|------|------|------|
| **OAK相机** | RGB图像 + ArUco标记检测 | `sensors/oak_camera.py` |
| **VT传感器** | 视触觉传感器（光学触觉） | `sensors/vt_sensor.py` |
| **Tac3D传感器** | 3D触觉传感器（位移场） | `sensors/tac3d_sensor.py` |
| **同步录制器** | 多传感器时间对齐录制 | `data/synchronized_recorder.py` |
| **自动录制器** | 基于ArUco距离的自动控制 | `data/auto_recorder.py` |
| **语音管理器** | 录制过程语音提示 | `utils/voice_manager.py` |

### 数据流程

```
传感器数据 → 时间对齐 → 同步录制 → Session存储
    ↓
ArUco检测 → 距离计算 → 自动控制 → 语音提示
```

---

## Tools 目录脚本说明

### 📊 数据处理工具

#### 1. `process_aruco_offline.py` - 离线ArUco处理 ⭐⭐⭐
**功能**: 对已录制的session进行ArUco标记检测，计算标记间距离

**使用场景**:
- 录制时未开启ArUco检测
- 需要重新处理ArUco数据
- 更新距离计算参数

**用法**:
```bash
# 处理指定session（检测 + 更新PKL）
python3 Tools/process_aruco_offline.py data/session_20251101_144648

# 仅检测，不更新PKL
python3 Tools/process_aruco_offline.py data/session_xxx --detect-only

# 处理最新session
python3 Tools/process_aruco_offline.py
```

**输出**:
- `oak_camera/aruco_detections_offline.json` - 检测结果
- `aligned_data.pkl` - 更新后的PKL文件（包含ArUco数据）

---

### 📈 可视化工具

#### 2. `vis_rerun.py` - Rerun可视化 ⭐⭐⭐
**功能**: 使用Rerun可视化session数据（相机、传感器、ArUco曲线）

**特性**:
- 自动检测所有传感器类型（OAK/VT/Tac3D）
- 支持ArUco距离曲线显示
- 时间轴控制，可暂停/拖动查看
- 自适应布局

**用法**:
```bash
# 可视化指定session
python3 Tools/vis_rerun.py data/session_20251101_144648

# 可视化最新session
python3 Tools/vis_rerun.py

# 从Tools目录运行
cd Tools
python3 vis_rerun.py
```

**功能**:
- 显示所有传感器图像（OAK相机、VT传感器、Tac3D热图）
- 显示ArUco距离变化曲线
- 时间同步回放

---

### 🔧 调试工具

#### 3. `inspect_pkl_content.py` - PKL数据检查
**功能**: 检查session的PKL文件内容和结构

**用法**:
```bash
python3 Tools/inspect_pkl_content.py data/session_xxx
```

**输出**:
- Session元数据
- 传感器信息
- 时间戳统计
- ArUco数据概览

#### 4. `check_session_integrity.py` - Session完整性检查
**功能**: 验证session的文件完整性

**用法**:
```bash
python3 Tools/check_session_integrity.py data/session_xxx
```

**检查项**:
- PKL文件存在性
- 图像序列完整性
- Tac3D数据文件
- metadata文件

---

### 🎙️ 测试工具

#### 5. `test_voice_manager.py` - 语音功能测试
**功能**: 测试语音提示系统

**用法**:
```bash
# 测试完整录制流程
python3 Tools/test_voice_manager.py

# 测试单个语音
python3 Tools/test_voice_manager.py --mode individual
```

---

## 快速开始

### 1. 启动GUI录制

```bash
# 激活环境
conda activate potac

# 启动系统
python3 main.py
```

### 2. 配置自动录制

编辑 `config/settings.json`:
```json
{
  "recording": {
    "distance_based_auto_recording": {
      "enabled": true,              // 启用自动录制
      "start_threshold_mm": 85.0,   // 开始录制距离阈值
      "stop_threshold_mm": 90.0,    // 停止录制距离阈值
      "voice_prompts_enabled": true // 启用语音提示
    }
  }
}
```

### 3. 录制流程

1. **启动传感器**: 点击"Start OAK Camera"
2. **等待ArUco检测**: 确保两个标记都被检测到
3. **启用自动录制**: 点击"Enable Auto-Rec"（如果配置文件已启用则自动启用）
4. **靠近标记**: 将手或物体移近标记（< 85mm）
   - 🔊 语音："Start Recording"
   - 系统自动开始录制
5. **移开标记**: 完成操作后移开（> 90mm）
   - 系统自动停止录制
   - 🔊 语音："Saving and processing recorded data..."
   - 🔊 语音："Save success! Ready for next record."
6. **重复录制**: 冷却2秒后可继续下一次录制

### 4. 数据处理和可视化

```bash
# 离线处理ArUco（如果录制时未处理）
python3 Tools/process_aruco_offline.py data/session_20251101_144648

# 可视化数据
python3 Tools/vis_rerun.py data/session_20251101_144648
```

---

## 数据格式

### Session目录结构

```
data/session_20251101_144648/
├── aligned_data.pkl              # 时间对齐的数据（主文件）
├── oak_camera/                   # OAK相机数据
│   ├── frame_000000.jpg
│   ├── frames_metadata.json
│   └── aruco_detections_offline.json  # ArUco检测结果
├── vt_0/                         # VT传感器0
│   ├── frame_000000.jpg
│   └── frames_metadata.json
└── tac3d_1/                      # Tac3D传感器1
    ├── tac3d_1_data.npz          # NPZ位移数据
    ├── tac3d_1_metadata.json     # 元数据
    ├── frame_000000.jpg          # 热图序列
    └── frames_metadata.json
```

### PKL数据结构

```python
{
    'metadata': {
        'session_name': 'session_20251101_144648',
        'start_time': datetime,
        'sensors': {
            'oak_camera': {...},
            'vt_0': {...},
            'tac3d_1': {...}
        }
    },
    'data': {
        'timestamps': [t1, t2, ...],  # 对齐的时间戳
        'aruco': {                     # ArUco数据
            'distance_absolute': [...],
            'distance_horizontal': [...],
            'left_detected': [...],
            'right_detected': [...]
        }
    }
}
```

---

## 传感器配置

### OAK相机 (config/settings.json)
```json
{
  "oak_camera": {
    "resolution": "1080p",
    "fps": 30,
    "aruco_enabled": true
  }
}
```

### Tac3D传感器
```json
{
  "tac3d_sensors": {
    "enabled": false,
    "sensors": [
      {
        "id": "tac3d_1",
        "port": 9988,
        "ip": null,              // 本地传感器
        "name": "Tac3D_Finger",
        "enabled": false
      }
    ]
  }
}
```

**连接Tac3D**:
1. GUI中点击"Connect Tac3D"
2. 配置端口和IP（本地传感器留空IP）
3. 点击连接

---

## 常用命令速查

```bash
# 启动系统
python3 main.py

# 离线处理ArUco
python3 Tools/process_aruco_offline.py <session_dir>

# 可视化session
python3 Tools/vis_rerun.py <session_dir>

# 检查数据完整性
python3 Tools/check_session_integrity.py <session_dir>

# 查看PKL内容
python3 Tools/inspect_pkl_content.py <session_dir>

# 测试语音功能
python3 Tools/test_voice_manager.py
```

---

## 故障排除

### 问题1: ArUco检测失败
**解决**:
- 确保标记ID正确（默认: 0和1）
- 检查光照条件
- 调整相机焦距

### 问题2: Tac3D连接失败
**解决**:
- 检查传感器电源
- 确认IP和端口配置
- 测试网络连通性: `ping <tac3d_ip>`

### 问题3: 自动录制不触发
**解决**:
- 确认ArUco两个标记都被检测到
- 检查距离阈值设置
- 查看GUI状态显示

### 问题4: 语音无输出
**解决**:
```bash
# 安装playsound
pip install playsound

# 检查语音文件
ls Assets/Potac-Voice/

# 测试语音
python3 Tools/test_voice_manager.py
```

---

## 系统要求

### 硬件
- OAK-D相机
- 视触觉传感器（可选）
- Tac3D触觉传感器（可选）
- 音频输出设备（用于语音提示）

### 软件依赖
```bash
# 核心依赖
pip install depthai opencv-python numpy kivy

# ArUco检测
pip install opencv-contrib-python

# 可视化
pip install rerun-sdk

# 语音提示
pip install playsound

# Tac3D传感器
# 安装PyTac3D（见Tac3D SDK文档）
```

---

## 贡献者

- 主要开发: Claude Code
- 项目负责: kirdo

## 许可证

[待添加]

---

## 相关文档

- **语音提示详细说明**: `VOICE_PROMPTS_GUIDE.md`
- **Tac3D配置说明**: `TAC3D_IP_CONFIG.md`
- **系统配置**: `config/settings.json`

---

**最后更新**: 2025-11-04
**版本**: v1.0
