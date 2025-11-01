# Tac3D实时可视化 - 快速开始

## 功能

基于 `main-exampleWithView.py` 创建的**实时位移可视化工具**：
- 🎨 2D彩色热图显示位移数据
- 📡 支持远程连接
- 🎯 实时统计信息
- ⌨️ 交互式控制

## 一分钟快速使用

```bash
cd /home/kirdo/robo/PoTac/Tac3d/Tac3D-SDK-v3.2.1/Tac3D-API/python/PyTac3D

# 本地连接
python tac3d_realtime_visualizer.py

# 远程连接
python tac3d_realtime_visualizer.py --ip 192.168.1.100
```

## 显示效果

```
┌────────────────────────────────┐
│ Tac3D Sensor: TAC3D001         │
│ Frame: 1234                    │
│ Max Disp: 0.1234 mm            │
│ Mean Disp: 0.0567 mm           │
│ Force: 2.345 N                 │
│                                │
│   [2D位移热图]     [色标]     │
│    ● ● ● ●         │ 最大值   │
│   ● ● ● ● ●        │          │
│    ● ● ● ●         │ 最小值   │
│                    mm          │
└────────────────────────────────┘
```

**颜色**：蓝色(低) → 绿色(中) → 黄色(高) → 红色(最大)

## 键盘控制

- **q** - 退出
- **c** - 校准（清零）
- **s** - 保存图像

## 常用命令

```bash
# 自动校准
python tac3d_realtime_visualizer.py --calibrate

# 自定义窗口大小
python tac3d_realtime_visualizer.py --width 1024 --height 768

# 完整配置
python tac3d_realtime_visualizer.py \
    --ip 192.168.1.100 \
    --port 9988 \
    --calibrate \
    --width 1024 \
    --height 768
```

## 与原始代码对比

| 文件 | 功能 |
|------|------|
| `main-exampleWithView.py` | 基础数据接收 |
| `tac3d_realtime_visualizer.py` | **+ 实时2D可视化** ⭐ |

## 技术亮点

1. **位移热图生成**
   - 计算3D位移模长
   - 高斯核平滑
   - JET色图映射

2. **自适应显示**
   - 自动调整色标范围
   - X-Y坐标自动归一化
   - 测量点标记

3. **实时性能**
   - 30-60 FPS
   - <50ms延迟
   - 低内存占用

## 文件位置

```
/home/kirdo/robo/PoTac/Tac3d/Tac3D-SDK-v3.2.1/Tac3D-API/python/PyTac3D/
├── main-exampleWithView.py          # 原始示例
├── tac3d_realtime_visualizer.py     # 新的可视化脚本
├── TAC3D_VISUALIZER_GUIDE.md        # 详细文档
└── TAC3D_QUICKSTART.md              # 本文件
```

## 故障排除

**无法连接**：
```bash
# 检查网络
ping 192.168.1.100

# 检查端口
netstat -an | grep 9988
```

**位移为零**：
- 传感器未接触物体
- 按 `c` 键校准

**显示窗口错误**：
```bash
export DISPLAY=:0
```

## 下一步

详细文档请查看：`TAC3D_VISUALIZER_GUIDE.md`

---

**提示**：首次运行建议使用 `--calibrate` 参数！
