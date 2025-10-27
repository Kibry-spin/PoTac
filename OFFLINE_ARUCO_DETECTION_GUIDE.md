# 离线ArUco检测脚本使用指南

## 概述

由于录制时ArUco数据保存频率低（仅12 FPS，而图片是29 FPS），导致只有40.9%的图片有对应的ArUco数据。

**离线检测脚本**可以对所有已录制的图片进行ArUco检测，确保**每张图片都有对应的ArUco数据**。

## 脚本说明

### ⭐ `process_aruco_offline.py` - 一体化脚本（推荐）

**功能**：整合了检测和PKL更新，一步完成
- 读取session中的所有图片
- 对每张图片进行ArUco标记检测
- 计算距离（像素、3D绝对、水平）
- 保存检测结果为JSON文件
- 自动更新PKL文件

**输出文件**：
- `<session_dir>/oak_camera/aruco_detections_offline.json` - 检测结果
- `<session_dir>/aligned_data.pkl` - 更新后的PKL文件

### 1. `offline_aruco_detection.py` - 仅离线检测

**功能**：
- 读取session中的所有图片
- 对每张图片进行ArUco标记检测
- 计算距离（像素、3D绝对、水平）
- 保存检测结果为JSON文件

**输出文件**：`<session_dir>/oak_camera/aruco_detections_offline.json`

### 2. `update_pkl_with_offline.py` - 仅更新PKL

**功能**：
- 读取离线检测结果
- 更新或创建PKL文件
- 确保ArUco数据与图片数量一致

**输出文件**：更新 `<session_dir>/aligned_data.pkl`

## 使用方法

### 方法A：使用一体化脚本（推荐）

```bash
cd /home/kirdo/robo/PoTac

# 完整处理（检测+更新PKL）- 一步完成
python process_aruco_offline.py data/session_20251027_192209

# 或使用最新session
python process_aruco_offline.py

# 仅检测不更新PKL
python process_aruco_offline.py data/session_20251027_192209 --detect-only
```

**预期输出**：
```
================================================================================
离线ArUco处理
================================================================================

Session: session_20251027_192209
总帧数: 333
检测到OAK设备，加载出厂标定...
✓ 已加载OAK出厂标定 (1280x720)
  fx=671.38, fy=670.96
  cx=626.53, cy=347.27

================================================================================
步骤 1/2: ArUco标记检测
================================================================================

开始ArUco检测 (333 帧)...
处理中... 333/333 (100.0%)

✓ 检测结果已保存: data/session_20251027_192209/oak_camera/aruco_detections_offline.json

检测统计:
  总帧数: 333
  左标记检测率: 333/333 (100.0%)
  右标记检测率: 329/333 (98.8%)
  双标记检测率: 329/333 (98.8%)
  有效距离测量: 329

距离统计 (mm):
  平均: 30.82
  标准差: 0.06
  范围: 30.66 - 30.98

================================================================================
步骤 2/2: 更新PKL文件
================================================================================

开始更新PKL文件...
✓ 找到现有PKL文件
✓ PKL文件已更新: data/session_20251027_192209/aligned_data.pkl

PKL内容:
  时间戳数量: 333
  ArUco数据点: 333
  有效距离测量: 329

统计信息:
  左标记检测率: 100.0%
  右标记检测率: 98.8%
  平均距离: 30.82 mm
  距离范围: 30.66 - 30.98 mm

================================================================================
✓ 处理完成！
================================================================================

ArUco数据已完整处理并更新到PKL文件
  JSON文件: data/session_20251027_192209/oak_camera/aruco_detections_offline.json
  PKL文件: data/session_20251027_192209/aligned_data.pkl

数据覆盖率: 100% (每帧都有ArUco数据)
```

### 方法B：分步执行（旧方法）

#### 步骤1：运行离线检测

```bash
cd /home/kirdo/robo/PoTac

# 对指定session进行离线检测
python offline_aruco_detection.py data/session_20251027_192209

# 或使用最新session
python offline_aruco_detection.py
```

**预期输出**：
```
================================================================================
离线ArUco检测
================================================================================

Session: session_20251027_192209
总帧数: 411
检测到OAK设备，加载出厂标定...
✓ 已加载OAK出厂标定 (1280x720)
  fx=857.12, fy=857.56
  cx=639.45, cy=359.78

开始处理 411 帧...
检测进度: 100%|██████████████████████████| 411/411 [00:15<00:00, 26.34it/s]

✓ 检测结果已保存: data/session_20251027_192209/oak_camera/aruco_detections_offline.json

统计信息:
  总帧数: 411
  左标记检测率: 411/411 (100.0%)
  右标记检测率: 411/411 (100.0%)
  双标记检测率: 411/411 (100.0%)
  有效距离测量: 411

距离统计 (mm):
  平均: 77.19
  标准差: 0.17
  范围: 76.76 - 77.66

================================================================================
✓ 检测完成！
================================================================================
```

### 步骤2：更新PKL文件

```bash
# 使用离线检测结果更新PKL
python update_pkl_with_offline.py data/session_20251027_192209
```

**预期输出**：
```
================================================================================
更新PKL文件
================================================================================

Session: session_20251027_192209
离线检测帧数: 411
✓ 找到现有PKL文件，将更新ArUco数据

✓ PKL文件已更新: data/session_20251027_192209/aligned_data.pkl

更新内容:
  时间戳数量: 411
  ArUco数据点: 411
  有效距离测量: 411

统计信息:
  左标记检测率: 100.0%
  右标记检测率: 100.0%
  平均距离: 77.19 mm
  距离范围: 76.76 - 77.66 mm

================================================================================
✓ 更新完成！
================================================================================

现在PKL文件包含完整的ArUco数据（每帧都有）
```

### 步骤3：验证结果

```bash
# 检查更新后的数据完整性
python check_session_integrity.py data/session_20251027_192209

# 分析ArUco频率（现在应该100%）
python analyze_aruco_frequency.py data/session_20251027_192209
```

**预期**：
```
📊 数据对比:
   图片保存: 411 张 @ 28.97 FPS
   ArUco数据: 411 条 @ 28.97 Hz
   保存率: 100.0%
   丢失数据: 0 条 (0.0%)

总体评估: ✅ 优秀
```

## 输出文件格式

### aruco_detections_offline.json

```json
{
  "session_name": "session_20251027_192209",
  "total_frames": 411,
  "oak_camera_dir": "oak_camera",

  "statistics": {
    "left_detection_count": 411,
    "left_detection_rate": 100.0,
    "right_detection_count": 411,
    "right_detection_rate": 100.0,
    "both_detection_count": 411,
    "both_detection_rate": 100.0,
    "valid_distance_measurements": 411
  },

  "distance_statistics": {
    "mean": 77.19,
    "std": 0.17,
    "min": 76.76,
    "max": 77.66,
    "median": 77.20
  },

  "detections": [
    {
      "frame_num": 0,
      "filename": "frame_000000.jpg",
      "timestamp": 1761563140.534,
      "frame_seq_num": 12345,

      "left_detected": true,
      "right_detected": true,

      "marker_distance": 520.5,          // 像素距离
      "real_distance_3d": 77.19,         // 3D绝对距离 (mm)
      "horizontal_distance": 77.18,      // 水平距离 (mm)

      "left_marker": {
        "id": 0,
        "corners": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
        "tvec": [x, y, z],  // 3D位置 (米)
        "rvec": [rx, ry, rz]
      },

      "right_marker": {
        "id": 1,
        "corners": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
        "tvec": [x, y, z],
        "rvec": [rx, ry, rz]
      },

      "calibrated": true
    },
    // ... 411条记录
  ]
}
```

## 使用场景

### 场景1：修复现有session的数据缺失

**方法A：使用一体化脚本（推荐）**
```bash
# 一步完成检测和PKL更新
python process_aruco_offline.py data/session_20251027_190540

# 验证结果
python check_session_integrity.py data/session_20251027_190540
```

**方法B：分步执行**
```bash
# 1. 检查现有session的ArUco数据完整性
python analyze_aruco_frequency.py data/session_20251027_190540

# 输出显示：保存率只有40.9%

# 2. 运行离线检测
python offline_aruco_detection.py data/session_20251027_190540

# 3. 更新PKL文件
python update_pkl_with_offline.py data/session_20251027_190540

# 4. 再次检查，现在应该100%
python analyze_aruco_frequency.py data/session_20251027_190540
```

### 场景2：批量处理多个session

**方法A：使用一体化脚本**
```bash
# 处理所有session - 一步完成
for session in data/session_*; do
    echo "处理: $session"
    python process_aruco_offline.py "$session"
done
```

**方法B：分步执行**
```bash
# 处理所有session
for session in data/session_*; do
    echo "处理: $session"
    python offline_aruco_detection.py "$session"
    python update_pkl_with_offline.py "$session"
done
```

### 场景3：只需要检测结果，不更新PKL

```bash
# 只运行离线检测，生成JSON文件
python process_aruco_offline.py data/session_20251027_192209 --detect-only

# 或使用原始脚本
python offline_aruco_detection.py data/session_20251027_192209

# JSON文件可以用于其他分析
cat data/session_20251027_192209/oak_camera/aruco_detections_offline.json
```

## 技术细节

### 相机标定

脚本会尝试从连接的OAK设备读取出厂标定：

- **如果OAK相机已连接**：使用出厂标定（精度最高）
- **如果OAK相机未连接**：使用默认标定（精度可能降低）

**建议**：运行离线检测时保持OAK相机连接。

### 性能

- **处理速度**：约25-30帧/秒
- **411帧处理时间**：约15秒
- **内存占用**：低（逐帧处理）

### 数据一致性

离线检测确保：
- ✅ **每张图片都有ArUco数据**（即使未检测到标记）
- ✅ **时间戳与图片metadata完全对应**
- ✅ **帧序号与图片一致**

## 与实时检测的对比

| 特性 | 实时检测（录制时） | 离线检测 |
|------|-------------------|---------|
| **数据完整性** | 40.9% (168/411) | 100% (411/411) |
| **处理速度** | 受GUI限制 (~12 FPS) | 全速 (~25-30 FPS) |
| **相机标定** | OAK出厂标定 | OAK出厂标定（如已连接） |
| **时效性** | 实时 | 后处理 |
| **灵活性** | 固定 | 可重新处理 |

## 常见问题

### Q1: 离线检测需要OAK相机连接吗？

**A**: 不是必须的，但强烈建议：
- **已连接**：使用OAK出厂标定，距离精度高
- **未连接**：使用默认标定，距离精度可能降低

### Q2: 可以重复运行吗？

**A**: 可以。每次运行会覆盖之前的结果。

### Q3: JSON文件很大怎么办？

**A**: 每帧约1-2KB，411帧约400KB-800KB，不算大。如果需要压缩：
```bash
gzip aruco_detections_offline.json
```

### Q4: 离线检测的准确性如何？

**A**: 与实时检测完全相同：
- 使用相同的ArUco检测器
- 使用相同的相机标定
- 使用相同的距离计算算法

### Q5: 可以只检测部分帧吗？

**A**: 可以修改脚本，添加帧范围参数。当前版本检测所有帧。

## 下一步建议

### 1. 修复实时录制系统

详见 `ARUCO_FREQUENCY_ANALYSIS.md`，在camera loop中直接保存ArUco数据，避免未来录制时数据丢失。

### 2. 自动化后处理流程

创建脚本在录制结束后自动运行离线检测：
```bash
# 在GUI的stop_recording后自动调用
python offline_aruco_detection.py <session_dir>
python update_pkl_with_offline.py <session_dir>
```

### 3. 数据验证

使用可视化工具验证离线检测结果：
```bash
python visualize_session.py data/session_20251027_192209
```

## 总结

**离线ArUco检测**解决了当前系统的数据完整性问题：

✅ **修复前**：
- 图片：411张
- ArUco数据：168条（40.9%）
- 问题：数据缺失严重

✅ **修复后**：
- 图片：411张
- ArUco数据：411条（100%）
- 效果：每张图片都有对应数据

### 可用工具

#### 🌟 推荐工具

**`process_aruco_offline.py`** - 一体化脚本
- ✅ 一步完成检测和PKL更新
- ✅ 自动化工作流程
- ✅ 支持 `--detect-only` 选项
- ✅ 自动查找最新session

```bash
# 最简单的使用方式
python process_aruco_offline.py data/session_20251027_192209
```

#### 传统工具（分步执行）

**`offline_aruco_detection.py`** - 离线检测
- 仅进行ArUco检测
- 生成JSON结果文件

**`update_pkl_with_offline.py`** - PKL更新
- 读取JSON结果
- 更新PKL文件

#### 辅助工具

**`check_session_integrity.py`** - 数据完整性检查
- 验证图片和metadata数量是否一致

**`analyze_aruco_frequency.py`** - ArUco频率分析
- 分析ArUco数据保存率和频率

现在可以对所有已录制的session进行补充检测，获得完整的ArUco距离数据！
