# 离线ArUco处理 - 快速开始

## 问题

录制时由于GUI限制，只有约40%的图片有ArUco数据。

## 解决方案

使用 `process_aruco_offline.py` 一步完成检测和PKL更新。

## 快速使用

### 最简单的方式

```bash
# 处理指定session（自动检测+更新PKL）
python process_aruco_offline.py data/session_20251027_192209

# 或处理最新session
python process_aruco_offline.py
```

### 结果

```
✓ 检测结果已保存: oak_camera/aruco_detections_offline.json
✓ PKL文件已更新: aligned_data.pkl
数据覆盖率: 100% (每帧都有ArUco数据)
```

## 其他选项

```bash
# 仅检测不更新PKL
python process_aruco_offline.py data/session_xxx --detect-only

# 使用自定义配置文件
python process_aruco_offline.py data/session_xxx --config my_settings.json

# 批量处理所有session
for session in data/session_*; do
    python process_aruco_offline.py "$session"
done
```

## 验证结果

```bash
# 检查数据完整性
python check_session_integrity.py data/session_xxx

# 分析ArUco频率
python analyze_aruco_frequency.py data/session_xxx
```

## 特性

- ✅ 一步完成检测和PKL更新
- ✅ 自动加载OAK出厂标定（如相机已连接）
- ✅ 100%数据覆盖率（每张图片都有ArUco数据）
- ✅ 进度显示（支持tqdm或简单进度）
- ✅ 详细统计信息
- ✅ 错误处理和恢复

## 技术要求

- OAK相机已连接（推荐，用于加载出厂标定）
- 可选：安装tqdm获得更好的进度显示
  ```bash
  conda activate potac
  pip install tqdm
  ```

## 详细文档

更多信息请参考：`OFFLINE_ARUCO_DETECTION_GUIDE.md`
