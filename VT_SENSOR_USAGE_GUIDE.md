# Visuotactile Sensor Usage Guide

## 新功能概述

系统现在支持**自动扫描和动态配置**视触觉传感器，无需手动编辑配置文件！

## 工作流程

### 1. 启动程序

```bash
python main.py
```

程序启动时会自动：
- 扫描所有可用的视频设备
- 检测工作正常的相机
- 准备传感器选择界面

### 2. 配置视触觉传感器

在GUI界面中：

1. **点击 "VT Sensors" 按钮**
   - 位于底部控制栏
   - 蓝色按钮

2. **传感器选择对话框出现**
   - 显示所有可用的视频设备
   - 每个设备显示：相机ID、分辨率、帧率、后端

3. **添加传感器**
   - 点击 "+ Add Sensor" 按钮添加传感器配置
   - 为每个传感器设置：
     - **名称**: 自定义传感器名称（如 "Left_GelSight"、"Right_DIGIT"）
     - **设备**: 从下拉菜单选择视频设备
   - 可以添加多个传感器

4. **移除传感器**
   - 点击行末尾的 "✗" 按钮移除传感器配置

5. **确认连接**
   - 点击 "Confirm" 按钮
   - 系统会自动连接所有配置的传感器
   - 成功后显示绿色状态信息

### 3. 查看传感器状态

连接成功后：

- **右侧面板**: 实时显示所有视触觉传感器的视频流
- **控制面板**: "VT Sensors: X connected" 显示连接数量
- **每个传感器显示**:
  - 传感器名称
  - 实时/录制状态
  - 当前FPS

### 4. 录制数据

点击 "Start Recording" 按钮：
- OAK相机（如果连接）开始录制
- 所有视触觉传感器同时开始录制
- 每个传感器生成独立的MP4文件

文件命名格式：
```
data/
├── oak_camera_20231215_143022.mp4
├── Left_GelSight_20231215_143022.mp4
└── Right_DIGIT_20231215_143022.mp4
```

### 5. 停止录制

点击 "Stop Recording" 按钮：
- 所有传感器停止录制
- 视频文件自动保存

## 示例场景

### 场景1: 单个GelSight传感器

1. 运行 `python main.py`
2. 点击 "VT Sensors"
3. 保持默认的 "VT_Sensor_1"
4. 选择你的GelSight相机设备
5. 点击 "Confirm"
6. 等待连接成功（绿色提示）
7. 右侧面板显示GelSight实时图像

### 场景2: 双DIGIT传感器（左右手）

1. 运行 `python main.py`
2. 点击 "VT Sensors"
3. 第一个传感器:
   - 名称: "Left_DIGIT"
   - 设备: Camera 0
4. 点击 "+ Add Sensor"
5. 第二个传感器:
   - 名称: "Right_DIGIT"
   - 设备: Camera 2
6. 点击 "Confirm"
7. 两个传感器同时显示在右侧面板

### 场景3: 多传感器阵列

可以添加任意数量的传感器：
- 左手指传感器 x3
- 右手指传感器 x3
- 掌心传感器 x2
- 等等...

每个传感器独立显示和录制。

## 设备查找

如果不确定相机ID，使用测试脚本：

```bash
python test_camera_access.py
```

输出示例：
```
Testing camera: 0
✓ Successfully opened camera 0
  - Backend: V4L2
  - Resolution: 640x480
  - FPS: 30
```

或者直接检查系统：
```bash
ls /dev/video*
```

## 故障排除

### 问题1: 对话框显示 "No video devices found"

**原因**: 没有检测到可用的视频设备

**解决**:
1. 检查相机连接: `ls /dev/video*`
2. 检查相机权限: `ls -la /dev/video*`
3. 运行测试: `python test_camera_access.py`
4. 确保相机未被其他程序占用

### 问题2: 传感器连接失败

**症状**: 点击Confirm后显示红色错误

**解决**:
1. 确认选择的相机ID正确
2. 确认相机未被其他进程占用
3. 重新扫描设备（关闭对话框，再次点击"VT Sensors"）
4. 查看日志了解详细错误

### 问题3: 看不到传感器视频

**原因**: 传感器可能未正确启动

**解决**:
1. 检查状态栏显示 "VT Sensors: X connected"
2. 确认传感器显示在右侧面板
3. 等待1-2秒让传感器初始化
4. 如果仍无显示，断开并重新连接传感器

### 问题4: FPS很低

**解决**:
1. 减少同时连接的传感器数量
2. 降低单个传感器的分辨率
3. 关闭图像预处理（默认已关闭）
4. 检查系统资源使用情况

## 技术细节

### 自动扫描

程序启动时自动扫描0-9号相机设备：
- 测试每个设备是否可打开
- 读取一帧确认设备可用
- 获取分辨率、帧率、后端信息
- 只显示工作正常的设备

### 动态连接

传感器连接过程：
1. 创建VisuotactileSensor对象
2. 初始化相机连接
3. 启动采集线程
4. 开始实时数据流
5. 更新GUI显示

### 数据同步

所有传感器采用独立线程：
- 每个传感器30 FPS独立采集
- 线程安全的帧缓冲
- GUI以30 FPS刷新显示
- 录制时间戳同步

## 高级用法

### 编程方式连接传感器

如果需要在代码中动态连接传感器：

```python
from sensors.sensor_manager import SensorManager

# 创建管理器
sensor_manager = SensorManager()

# 连接传感器
sensor_manager.connect_visuotactile_sensor(
    sensor_id="my_sensor",
    camera_id=0,
    name="My GelSight Sensor"
)

# 获取数据
sensor_data = sensor_manager.get_sensor_data()
if 'visuotactile' in sensor_data:
    frame = sensor_data['visuotactile']['my_sensor']

# 断开传感器
sensor_manager.disconnect_visuotactile_sensor("my_sensor")
```

### 自定义传感器配置

可以为每个传感器设置自定义配置：

```python
config = {
    'resolution': (320, 240),  # 更低分辨率
    'fps': 60,                 # 更高帧率
    'enable_preprocessing': True,  # 启用预处理
    'preprocessing': {
        'denoise': True,
        'enhance_contrast': True
    }
}

sensor_manager.add_visuotactile_sensor(
    sensor_id="custom_sensor",
    camera_id=0,
    name="Custom Sensor",
    config=config
)
```

## 性能优化

### 推荐配置

- **单个传感器**: 640x480 @ 30fps (默认)
- **2个传感器**: 640x480 @ 30fps 每个
- **3-4个传感器**: 考虑降低到320x240
- **5个以上**: 320x240 @ 30fps 或更低

### 系统要求

- **CPU**: 建议4核以上
- **内存**: 每个传感器约100-200MB
- **USB**: USB 3.0推荐（高分辨率时）
- **存储**: SSD推荐用于高帧率录制

## 总结

新的动态配置系统提供：
- ✓ 自动设备扫描
- ✓ GUI可视化选择
- ✓ 实时连接/断开
- ✓ 多传感器支持
- ✓ 同步录制
- ✓ 无需配置文件

开始使用只需3步：
1. 运行程序
2. 点击"VT Sensors"
3. 选择并确认

简单、直观、强大！
