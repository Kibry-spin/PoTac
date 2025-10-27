# ArUco检测和保存频率分析

## 问题发现

在检查session数据时发现：
- **OAK相机图片保存**: 411张，29 FPS ✅
- **PKL ArUco数据保存**: 168条，12 FPS ⚠️
- **保存率**: 仅40.9%的帧

## 完整数据流分析

### 1. ArUco检测频率 ✅ 30 FPS

**位置**: `src/sensors/oak_camera.py:337-362`

```python
def _camera_loop(self):
    while self.is_running:
        in_rgb = q_rgb.get()  # 从DepthAI获取帧
        frame = in_rgb.getCvFrame()

        # ✅ 每帧都进行ArUco检测
        if self.aruco_enabled and self.aruco_detector:
            processed_frame, detection_results = self.aruco_detector.detect_markers(frame)
            detection_info = self.aruco_detector.get_detection_info()

            # 保存到成员变量
            self.aruco_detection_results = detection_info
```

**频率**：
- OAK相机配置：30 FPS
- **每帧都检测** ArUco标记
- 检测结果保存到 `self.aruco_detection_results`

### 2. 图片录制频率 ✅ ~29 FPS

**位置**: `src/data/synchronized_recorder.py:60-120`

```python
def _capture_loop(self):
    while self.recording:
        # 获取最新帧（通过get_frame_bgr）
        frame = self.sensor_object.get_frame_bgr()

        if frame is not None:
            # 放入queue
            self.frame_queue.put_nowait(frame_data)
```

**实际测量**（session_20251027_190540）：
- 录制时长：14.187秒
- 保存图片：411张
- **实际帧率：28.97 FPS** ✅

**结论**：图片录制以接近30 FPS的速度运行，正常。

### 3. PKL ArUco数据保存频率 ⚠️ ~12 FPS

**位置**:
1. `main.py:46` - GUI update调度
2. `src/gui/main_window.py:428-431` - ArUco数据保存

```python
# main.py
self.gui_fps = 30.0  # 目标30 FPS
Clock.schedule_interval(self.update, 1.0/self.gui_fps)

# main_window.py update方法
def update(self, dt):
    # 获取最新的ArUco结果
    aruco_results = self.sensor_manager.oak_camera.get_aruco_detection_results()

    # 保存到PKL
    if self.sync_recorder and aruco_results:
        timestamp = time.time() - self.sync_recorder.start_time
        self.sync_recorder.record_frame_data(timestamp, aruco_results)  # ⚠️
```

**实际测量**：
- PKL记录帧数：168条
- 录制时长：13.999秒
- **实际保存频率：12.00 FPS** ⚠️

**问题**：
- GUI update虽然设置为30 FPS，但实际运行时可能由于Kivy渲染负载而降低
- **只保存了40.9%的帧的ArUco数据**

## 数据对比表

| 项目 | 配置频率 | 实际频率 | 数据量 | 说明 |
|------|----------|----------|--------|------|
| ArUco检测 | 30 FPS | ~30 FPS | 每帧 | ✅ 正常 |
| 图片保存 | 30 FPS | 28.97 FPS | 411张 | ✅ 接近配置 |
| PKL ArUco保存 | 30 FPS | 12.00 FPS | 168条 | ⚠️ 低于预期 |
| **保存率** | 100% | **40.9%** | - | ❌ 数据丢失 |

## 问题影响

### 1. 数据不完整
- 411张图片中，只有168张对应了ArUco数据
- **丢失了59.1%的ArUco测量数据**

### 2. 时间对齐问题
- 图片序列：frame_000000.jpg, frame_000001.jpg, ..., frame_000410.jpg（411张）
- ArUco数据：只有168个时间戳
- **无法为每张图片找到对应的ArUco距离数据**

### 3. 分析受限
- 高速运动时，12 FPS可能无法捕捉细节
- 距离变化的采样率低

## 根本原因

### GUI Update频率限制

**代码路径**：
```
Kivy Clock (30 FPS设置)
    ↓
main.py:update() (实际~12 FPS)
    ↓
main_window.py:update()
    ↓
get_aruco_detection_results() (读取最新结果)
    ↓
record_frame_data() (保存到PKL)
```

**瓶颈**：
1. Kivy GUI渲染负载高（显示相机+传感器画面）
2. `update()` 方法中有大量GUI更新操作
3. 实际update频率低于30 FPS目标

### 设计问题

**当前设计**：
- ArUco数据保存依赖GUI update
- GUI受渲染性能限制
- **图片录制和ArUco保存频率不匹配**

## 解决方案

### 方案1：ArUco数据在Camera Loop中直接保存 ✅ 推荐

**优点**：
- 与图片保存同步（都是~29 FPS）
- 不受GUI限制
- 100%数据保存率

**修改位置**：
`src/sensors/oak_camera.py:349-362`

**实现思路**：
```python
def _camera_loop(self):
    while self.is_running:
        # 获取帧
        frame = in_rgb.getCvFrame()

        # ArUco检测
        if self.aruco_enabled:
            detection_info = self.aruco_detector.get_detection_info()

            # ✅ 新增：如果在录制，直接通知PKL saver
            if self.is_recording_callback:
                self.is_recording_callback(timestamp, detection_info)
```

### 方案2：提高GUI update频率 ❌ 不推荐

**尝试**：
- 降低GUI渲染负载
- 简化update方法

**问题**：
- 受Kivy框架限制
- 无法保证稳定30 FPS
- 治标不治本

### 方案3：独立的ArUco数据采集线程 ⚠️ 复杂

**实现**：
- 创建专门线程定时获取ArUco数据
- 不依赖GUI update

**问题**：
- 增加系统复杂度
- 仍需要从camera loop获取数据

## 推荐实现（方案1详细）

### 1. 修改OAK相机，添加回调机制

**文件**: `src/sensors/oak_camera.py`

```python
class OAKCamera:
    def __init__(self):
        self.aruco_data_callback = None  # 新增

    def set_aruco_data_callback(self, callback):
        """设置ArUco数据回调"""
        self.aruco_data_callback = callback

    def _camera_loop(self):
        while self.is_running:
            # ... 获取帧和检测 ...

            if self.aruco_enabled and self.aruco_detector:
                detection_info = self.aruco_detector.get_detection_info()
                detection_info['frame_seq_num'] = frame_seq_num

                # 保存到成员变量（GUI使用）
                with self.lock:
                    self.aruco_detection_results = detection_info

                # ✅ 立即回调（录制使用）
                if self.aruco_data_callback:
                    timestamp = time.time()
                    self.aruco_data_callback(timestamp, detection_info)
```

### 2. 修改SynchronizedRecorder

**文件**: `src/data/synchronized_recorder.py`

```python
class SynchronizedRecorder:
    def start_recording(self):
        # ... 现有代码 ...

        # ✅ 设置OAK相机的ArUco回调
        if hasattr(self.sensor_manager.oak_camera, 'set_aruco_data_callback'):
            self.sensor_manager.oak_camera.set_aruco_data_callback(
                self._on_aruco_data
            )

    def _on_aruco_data(self, timestamp, aruco_results):
        """ArUco数据回调（在camera loop中调用）"""
        if self.recording:
            relative_timestamp = timestamp - self.start_time
            self.pkl_saver.add_camera_frame(relative_timestamp, aruco_results)

    def stop_recording(self):
        # 移除回调
        if hasattr(self.sensor_manager.oak_camera, 'set_aruco_data_callback'):
            self.sensor_manager.oak_camera.set_aruco_data_callback(None)

        # ... 现有代码 ...
```

### 3. 移除GUI中的ArUco保存逻辑

**文件**: `src/gui/main_window.py:428-431`

```python
def update(self, dt):
    # 获取ArUco结果（仅用于显示）
    aruco_results = self.sensor_manager.oak_camera.get_aruco_detection_results()

    # ❌ 删除这部分 - 现在在camera loop中直接保存
    # if self.sync_recorder and aruco_results:
    #     timestamp = time.time() - self.sync_recorder.start_time
    #     self.sync_recorder.record_frame_data(timestamp, aruco_results)

    # ✅ 只用于显示更新
    self._update_aruco_display(aruco_results)
```

## 预期效果

### 修改前
```
录制14秒：
- 图片：411张 (29 FPS)
- ArUco数据：168条 (12 FPS) ⚠️
- 保存率：40.9%
```

### 修改后
```
录制14秒：
- 图片：411张 (29 FPS)
- ArUco数据：411条 (29 FPS) ✅
- 保存率：100%
```

## 临时解决方案

在实施完整修复前，可以：

### 选项1：降低图片保存频率
```python
# 在synchronized_recorder中设置较低的FPS
target_fps = 12  # 匹配当前PKL保存频率
```

### 选项2：使用现有数据进行插值
```python
# 对缺失的ArUco数据进行线性插值
import numpy as np
from scipy.interpolate import interp1d

# 已知的ArUco时间戳和距离
aruco_timestamps = pkl_data['data']['timestamps']
aruco_distances = pkl_data['data']['aruco']['distance_absolute']

# 所有图片的时间戳
all_timestamps = image_metadata['frames'][i]['timestamp']

# 插值
interpolator = interp1d(aruco_timestamps, aruco_distances,
                       kind='linear', fill_value='extrapolate')
interpolated_distances = interpolator(all_timestamps)
```

## 总结

### 现状
- ✅ **ArUco检测频率**: 30 FPS（每帧都检测）
- ✅ **图片保存频率**: ~29 FPS（接近配置）
- ❌ **PKL ArUco保存频率**: ~12 FPS（严重低于预期）
- ❌ **数据保存率**: 仅40.9%

### 根本原因
- ArUco数据保存依赖GUI update
- GUI实际运行频率远低于30 FPS目标
- 图片录制和ArUco数据保存不同步

### 解决方案
- **推荐**：在camera loop中直接保存ArUco数据
- **效果**：100%数据保存率，与图片完全同步
- **修改文件**：oak_camera.py, synchronized_recorder.py, main_window.py

这样可以确保每张保存的图片都有对应的ArUco距离数据！
