# PoTac 语音播报配置说明

## 如何关闭语音播报

### 方法：编辑配置文件

打开配置文件：`config/settings.json`

找到 `recording` 部分，修改以下配置：

```json
{
  "recording": {
    "voice_prompts_enabled": false,  // ← 全局语音开关（推荐修改这个）
    "distance_based_auto_recording": {
      "enabled": true,
      "voice_prompts_enabled": false  // ← 自动录制时的语音开关
    }
  }
}
```

## 配置说明

### 1. 全局语音开关（推荐）
```json
"recording": {
  "voice_prompts_enabled": false  // 关闭所有语音提示
}
```

**作用范围**：
- 手动录制时的语音提示
- 保存数据时的语音提示

**默认值**：`false`（已关闭）

---

### 2. 自动录制语音开关
```json
"distance_based_auto_recording": {
  "voice_prompts_enabled": false  // 关闭自动录制的语音提示
}
```

**作用范围**：
- 自动开始录制时的 "Start Recording" 提示

**默认值**：`false`（已关闭）

---

## 语音提示列表

当语音启用时，会播放以下提示：

| 提示 | 文件名 | 触发时机 |
|------|--------|---------|
| 开始录制 | `StartRecording.wav` | 开始录制时 |
| 停止录制 | `StopRecording.wav` | 停止录制时 |
| 保存数据 | `Saving and processing recorded data. Please wait..wav` | 停止录制后保存数据时 |
| 保存成功 | `Save success! Ready for next record..wav` | 数据保存完成时 |

**语音文件路径**：`Assets/Potac-Voice/`

---

## 快速开关对照表

| 需求 | 配置 |
|------|------|
| **关闭所有语音** | `recording.voice_prompts_enabled: false` + `distance_based_auto_recording.voice_prompts_enabled: false` |
| **只关闭手动录制语音** | `recording.voice_prompts_enabled: false` |
| **只关闭自动录制语音** | `distance_based_auto_recording.voice_prompts_enabled: false` |
| **启用所有语音** | 两个都设置为 `true` |

---

## 当前配置状态

根据您当前的配置文件，语音播报已经**关闭**：

```json
"recording": {
  "voice_prompts_enabled": false,  // ✓ 已关闭
  "distance_based_auto_recording": {
    "voice_prompts_enabled": false  // ✓ 已关闭
  }
}
```

重启 PoTac 程序后生效。

---

## 验证配置是否生效

启动程序后，查看日志输出：

```
[INFO   ] [MainWindow  ] Voice prompts disabled by configuration
[INFO   ] [AutoRecorder] Voice prompts disabled
```

如果看到以上日志，说明配置成功！

---

## 重新启用语音

如果需要重新启用语音，将配置改为：

```json
"recording": {
  "voice_prompts_enabled": true,  // 启用语音
  "distance_based_auto_recording": {
    "voice_prompts_enabled": true  // 启用自动录制语音
  }
}
```

然后重启程序即可。
