# batch_process.py 使用说明

## 功能

批量处理data目录及其子目录下所有session的ArUco数据，包括：
- 递归查找所有有效session
- 批量ArUco标记检测
- 自动更新PKL文件（可选）
- 支持并行处理加速
- 生成详细处理报告
- **性能优化**: 相机标定仅加载一次（全局共享）

## 基本用法

### 1. 预览模式（推荐首次使用）

查看有哪些session将被处理，不实际执行：

```bash
python3 Tools/batch_process.py --dry-run
```

### 2. 基本批量处理

处理data目录下所有session：

```bash
python3 Tools/batch_process.py
```

**默认行为**:
- 跳过已处理的session
- 串行处理（一个一个处理）
- 检测ArUco并更新PKL文件
- 生成两份报告：
  - `batch_aruco_report.txt` - 文本报告
  - `batch_aruco_report.json` - JSON报告

### 3. 并行处理（推荐）

使用多进程加速处理：

```bash
# 使用4个进程（默认）
python3 Tools/batch_process.py --parallel

# 使用8个进程
python3 Tools/batch_process.py --parallel --workers 8
```

**性能提升**:
- 4进程: 约3-4倍加速
- 8进程: 约6-7倍加速

### 4. 强制重新处理

重新处理所有session（包括已处理的）：

```bash
python3 Tools/batch_process.py --force
```

### 5. 仅检测不更新PKL

只做ArUco检测，不更新PKL文件：

```bash
python3 Tools/batch_process.py --skip-update-pkl
```

## 常用组合

### 快速批量处理（推荐）
```bash
python3 Tools/batch_process.py --parallel --workers 8
```

### 重新处理所有数据
```bash
python3 Tools/batch_process.py --force --parallel --workers 8
```

### 仅检测ArUco（不修改PKL）
```bash
python3 Tools/batch_process.py --skip-update-pkl --parallel
```

### 自定义报告路径
```bash
python3 Tools/batch_process.py --report reports/batch_20251104.txt
```

## 输出说明

### 1. 处理过程输出

```
================================================================================
批量ArUco处理工具
================================================================================

搜索session目录: data

找到 20 个有效session:
  1. session_20251028_132253
  2. session_20251028_132424
  ...

处理配置:
  并行处理: 是
  进程数: 8
  强制重新处理: 否
  更新PKL文件: 是

按 Enter 开始处理，或 Ctrl+C 取消...

使用 8 个进程并行处理...
处理进度: 100%|████████████████████████| 20/20 [00:45<00:00,  2.27s/it]

================================================================================
处理完成
================================================================================

耗时: 45.3 秒

总session数:      20
成功处理:         18
跳过 (已处理):    0
失败:             2
总处理帧数:       6234
有效距离测量数:   5891

详细报告已保存: batch_aruco_report.txt
JSON报告已保存: batch_aruco_report.json

✓ 所有处理完成！
```

### 2. 文本报告格式

`batch_aruco_report.txt`:

```
================================================================================
批量ArUco处理报告
================================================================================

生成时间: 2025-11-04 16:30:45

统计摘要
--------------------------------------------------------------------------------
总session数:      20
成功处理:         18
跳过 (已处理):    0
失败:             2
总处理帧数:       6234
有效距离测量数:   5891

详细结果
--------------------------------------------------------------------------------

✓ 成功处理 (18 个):

  session_20251028_132253
    总帧数: 305
    左标记检测: 305/305
    右标记检测: 305/305
    双标记检测: 305/305
    有效距离: 305/305

  session_20251028_132424
    总帧数: 412
    左标记检测: 410/412
    右标记检测: 412/412
    双标记检测: 410/412
    有效距离: 410/412

  ...

⊙ 跳过 (0 个):

✗ 失败 (2 个):

  session_20251028_invalid
    错误: 处理失败: No ArUco markers detected
    详细:
      Traceback...
```

### 3. JSON报告格式

`batch_aruco_report.json`:

```json
{
  "timestamp": "2025-11-04T16:30:45.123456",
  "summary": {
    "total_sessions": 20,
    "successful": 18,
    "skipped": 0,
    "failed": 2,
    "total_frames_processed": 6234,
    "total_valid_distances": 5891
  },
  "results": [
    {
      "session": "session_20251028_132253",
      "full_path": "/home/kirdo/robo/PoTac/data/session_20251028_132253",
      "success": true,
      "skipped": false,
      "message": "ArUco检测和PKL更新完成",
      "stats": {
        "total_frames": 305,
        "left_detected": 305,
        "right_detected": 305,
        "both_detected": 305,
        "valid_distances": 305
      }
    },
    ...
  ]
}
```

## 有效Session要求

脚本会自动识别有效的session，必须包含：
- `aligned_data.pkl` - 主数据文件
- `oak_camera/` - 相机数据目录
- `oak_camera/frames_metadata.json` - 帧元数据

不符合条件的目录会被自动跳过。

## 输出文件

### ArUco检测结果
每个session会生成：
- `oak_camera/aruco_detections_offline.json` - ArUco检测结果

### 更新的PKL文件
如果启用PKL更新（默认），会在原PKL基础上添加：
```python
{
  'data': {
    'aruco': {
      'distance_absolute': [...],      # 绝对距离
      'distance_horizontal': [...],    # 水平距离
      'left_detected': [...],          # 左标记检测状态
      'right_detected': [...],         # 右标记检测状态
      'left_corners': [...],           # 左标记角点
      'right_corners': [...]           # 右标记角点
    }
  }
}
```

## 性能建议

### 串行 vs 并行

| Session数量 | 建议模式 | 命令 |
|------------|---------|------|
| < 5个 | 串行 | `batch_process.py` |
| 5-20个 | 并行 (4进程) | `batch_process.py --parallel` |
| > 20个 | 并行 (8进程) | `batch_process.py --parallel --workers 8` |

### 系统资源

- **CPU**: 每个worker占用1个CPU核心
- **内存**: 每个worker约需500MB-1GB
- **磁盘**: 写入速度是瓶颈（SSD推荐）

**示例**: 8核CPU，建议 `--workers 6`（留2核给系统）

### 相机标定优化 ⭐

批处理脚本已优化为**仅加载一次相机标定**：
- 程序启动时加载OAK相机出厂标定（如果连接）
- 所有session共享同一份标定数据
- 避免重复读取设备，大幅提升处理速度
- 适用于同一台OAK相机录制的所有session

**性能对比**:
- 旧方案: 每个session重新加载标定（~2-3秒/session）
- 新方案: 仅启动时加载一次（~0.1秒/session）
- **提升**: 对于20个session，节省约40-60秒

## 常见问题

### Q1: 提示"未找到有效session"
**原因**: data目录下没有符合条件的session
**解决**: 检查session是否包含必需的文件（pkl和oak_camera目录）

### Q2: 某些session处理失败
**原因**: ArUco标记检测失败或数据损坏
**解决**: 查看报告中的错误详情，检查具体原因

### Q3: 处理很慢
**原因**: 使用串行模式或worker数量不足
**解决**: 使用 `--parallel --workers 8` 加速

### Q4: 如何重新处理已处理的session
**解决**: 使用 `--force` 参数

### Q5: 想保留原PKL文件不修改
**解决**: 使用 `--skip-update-pkl` 参数

## 完整参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--data-dir` | 数据目录路径 | `data` |
| `--parallel` | 启用并行处理 | 否 |
| `--workers` | 并行进程数 | 4 |
| `--force` | 强制重新处理 | 否 |
| `--skip-update-pkl` | 不更新PKL | 否 |
| `--dry-run` | 仅预览 | 否 |
| `--report` | 文本报告路径 | `batch_aruco_report.txt` |
| `--json-report` | JSON报告路径 | `batch_aruco_report.json` |

## 典型工作流

### 第一次使用
```bash
# 1. 预览
python3 Tools/batch_process.py --dry-run

# 2. 处理
python3 Tools/batch_process.py --parallel --workers 8

# 3. 查看报告
cat batch_aruco_report.txt
```

### 定期批量处理
```bash
# 只处理新增的session（跳过已处理）
python3 Tools/batch_process.py --parallel --workers 8
```

### 数据质量检查
```bash
# 重新处理所有，检查一致性
python3 Tools/batch_process.py --force --parallel --workers 8
```

---

**提示**: 建议先用 `--dry-run` 预览，确认无误后再实际处理。
