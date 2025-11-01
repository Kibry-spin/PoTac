# Tac3D IP配置集成完成

## ✅ 已完成的工作

### 1. 配置文件更新
已在 `config/settings.json` 中添加Tac3D传感器配置：

```json
{
  "tac3d_sensors": {
    "enabled": false,
    "default_config": {
      "max_queue_size": 5,
      "auto_calibrate": false,
      "calibrate_delay": 2.0,
      "save_all_data": false,
      "comment": "Tac3D远程触觉传感器配置"
    },
    "sensors": [
      {
        "id": "tac3d_1",
        "port": 9988,
        "ip": null,
        "name": "Tac3D_Finger",
        "enabled": false,
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

### 2. 核心代码更新

#### `src/sensors/tac3d_sensor.py`
- ✅ `__init__` 方法添加 `ip` 参数
- ✅ `initialize` 方法支持IP配置（使用PyTac3D的 `portIP` 参数）
- ✅ `get_status` 和 `get_device_info` 返回IP信息

#### `src/sensors/sensor_manager.py`
- ✅ `add_tac3d_sensor` 添加IP参数
- ✅ `connect_tac3d_sensor` 支持IP参数

#### `src/gui/tac3d_gui_extensions.py`
- ✅ GUI配置对话框添加"IP Address"输入框
- ✅ 连接时自动传递IP参数

## 🚀 使用方法

### 方法1：通过GUI手动连接

1. 启动应用：
   ```bash
   python main.py
   ```

2. 点击 "Tac3D Config" 按钮

3. 填写传感器信息：
   - **Sensor ID**: `tac3d_1`
   - **UDP Port**: `9988`
   - **IP Address**:
     - 留空 = 本地传感器（localhost）
     - 填写IP = 远程传感器（如 `192.168.1.100`）
   - **Name**: `Tac3D_Sensor`

4. 点击 "Connect"

### 方法2：通过配置文件自动连接

编辑 `config/settings.json`：

```json
{
  "tac3d_sensors": {
    "enabled": true,  // ← 改为true
    "sensors": [
      {
        "id": "tac3d_1",
        "port": 9988,
        "ip": "192.168.1.100",  // ← 填写实际IP地址
        "name": "Tac3D_Remote",
        "enabled": true,  // ← 改为true
        "config": {
          "auto_calibrate": true  // 可选：启动时自动校准
        }
      }
    ]
  }
}
```

启动应用后会自动连接。

## 📖 配置说明

### IP地址字段

| 值 | 说明 |
|-----|------|
| `null` 或 空字符串 | 本地传感器（使用localhost） |
| `"192.168.1.100"` | 远程传感器IP地址 |

### enabled字段

```json
{
  "tac3d_sensors": {
    "enabled": true,  // 总开关：启用Tac3D功能
    "sensors": [
      {
        "id": "tac3d_1",
        "enabled": true,  // 此传感器启用
        ...
      },
      {
        "id": "tac3d_2",
        "enabled": false,  // 此传感器禁用（不会自动连接）
        ...
      }
    ]
  }
}
```

### 多传感器配置示例

```json
{
  "tac3d_sensors": {
    "enabled": true,
    "sensors": [
      {
        "id": "tac3d_local",
        "port": 9988,
        "ip": null,  // 本地传感器
        "name": "Tac3D_Local",
        "enabled": true
      },
      {
        "id": "tac3d_remote1",
        "port": 9988,
        "ip": "192.168.1.100",  // 远程传感器1
        "name": "Tac3D_Robot1",
        "enabled": true
      },
      {
        "id": "tac3d_remote2",
        "port": 9989,  // 不同端口
        "ip": "192.168.1.101",  // 远程传感器2
        "name": "Tac3D_Robot2",
        "enabled": true
      }
    ]
  }
}
```

## 🔧 网络配置

### 本地传感器
- IP: 留空或 `null`
- 端口: `9988`（默认）
- 传感器和采集系统在同一台机器

### 远程传感器

1. **确保网络连通**：
   ```bash
   ping 192.168.1.100
   ```

2. **防火墙设置**：
   ```bash
   # 在采集系统上开放UDP端口
   sudo ufw allow 9988/udp
   ```

3. **Tac3D传感器配置**：
   - 在传感器端配置UDP发送目标为采集系统的IP地址

## 📊 GUI界面更新

配置对话框现在显示：

```
┌────────────────────────────────┐
│ Tac3D Sensor Configuration     │
├────────────────────────────────┤
│ Connected Sensors: tac3d_1     │
├────────────────────────────────┤
│ Sensor ID:  [tac3d_1         ] │
│ UDP Port:   [9988            ] │
│ IP Address: [192.168.1.100   ] │  ← 新增
│ Name:       [Tac3D_Sensor    ] │
├────────────────────────────────┤
│ Status: ✓ tac3d_1 connected   │
├────────────────────────────────┤
│ [Connect] [Calibrate] [Disconnect] │
│           [Close]              │
└────────────────────────────────┘
```

提示："IP Address" 留空表示本地连接

## ✅ 验证安装

1. 查看配置文件：
   ```bash
   cat config/settings.json | grep -A 20 "tac3d_sensors"
   ```

2. 测试连接：
   ```bash
   python test_tac3d_sensor.py
   ```

3. 检查GUI：
   - 启动 `python main.py`
   - 点击 "Tac3D Config"
   - 确认有"IP Address"输入框

## 🆘 故障排除

### 问题1：无法连接到远程传感器

**症状**：Connection timeout

**解决**：
1. 检查网络连通性：`ping <IP>`
2. 检查防火墙：`sudo ufw status`
3. 确认传感器端UDP目标IP正确
4. 确认端口未被占用：`netstat -an | grep 9988`

### 问题2：GUI没有IP输入框

**症状**：配置对话框中看不到IP Address字段

**解决**：
1. 确认已更新GUI扩展文件：
   ```bash
   grep "IP Address" src/gui/tac3d_gui_extensions.py
   ```
2. 重启应用

### 问题3：配置文件不生效

**症状**：启动后传感器未自动连接

**解决**：
1. 检查 `enabled` 字段是否为 `true`
2. 检查JSON格式是否正确
3. 查看日志：检查是否有加载错误

## 📝 配置模板

### 仅本地传感器
```json
{
  "tac3d_sensors": {
    "enabled": true,
    "sensors": [
      {
        "id": "tac3d_1",
        "port": 9988,
        "ip": null,
        "name": "Tac3D_Sensor",
        "enabled": true
      }
    ]
  }
}
```

### 仅远程传感器
```json
{
  "tac3d_sensors": {
    "enabled": true,
    "sensors": [
      {
        "id": "tac3d_remote",
        "port": 9988,
        "ip": "192.168.1.100",
        "name": "Tac3D_Remote",
        "enabled": true,
        "config": {
          "auto_calibrate": true
        }
      }
    ]
  }
}
```

### 本地+远程混合
```json
{
  "tac3d_sensors": {
    "enabled": true,
    "sensors": [
      {
        "id": "tac3d_local",
        "port": 9988,
        "ip": null,
        "name": "Tac3D_Local",
        "enabled": true
      },
      {
        "id": "tac3d_remote",
        "port": 9988,
        "ip": "192.168.1.100",
        "name": "Tac3D_Remote",
        "enabled": true
      }
    ]
  }
}
```

## 🎯 快速测试

### 1. 本地连接测试
```bash
# GUI方式
python main.py
# 点击 Tac3D Config → 填写信息（IP留空）→ Connect

# 命令行方式
python test_tac3d_sensor.py
```

### 2. 远程连接测试
在GUI中：
- IP Address: `192.168.1.100`
- Port: `9988`
- 点击Connect

查看日志：
```
Tac3DSensor: Initialized sensor 'Tac3D_Sensor' on port 9988 from 192.168.1.100
Tac3DSensor: Initializing UDP connection on port 9988 from 192.168.1.100...
Tac3DSensor: Connected to sensor SN: AD2-0047L
```

## 📚 相关文档

- **完整集成指南**: `TAC3D_INTEGRATION_COMPLETE.md`
- **技术文档**: `TAC3D_INTEGRATION_GUIDE.md`
- **GUI集成**: `TAC3D_GUI_INTEGRATION.md`

---

**更新时间**: 2025-10-31
**状态**: ✅ IP配置完全集成
