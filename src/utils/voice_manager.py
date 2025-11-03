"""
语音提示管理器
在录制过程中提供语音反馈
"""

import threading
import queue
from pathlib import Path
from kivy.logger import Logger


class VoiceManager:
    """管理录制过程中的语音提示"""

    def __init__(self, assets_dir=None):
        """
        初始化语音管理器

        Args:
            assets_dir: 语音素材目录，默认为项目Assets/Potac-Voice
        """
        if assets_dir is None:
            # 默认路径：src/utils -> project_root -> Assets/Potac-Voice
            project_root = Path(__file__).parent.parent.parent
            assets_dir = project_root / "Assets" / "Potac-Voice"

        self.assets_dir = Path(assets_dir)

        # 检查目录是否存在
        if not self.assets_dir.exists():
            Logger.warning(f"VoiceManager: 语音素材目录不存在: {self.assets_dir}")
            self.enabled = False
        else:
            self.enabled = True
            Logger.info(f"VoiceManager: 已加载语音素材目录: {self.assets_dir}")

        # 定义语音提示文件映射
        self.voice_files = {
            'start_recording': 'StartRecording.wav',
            'stop_recording': 'StopRecording.wav',
            'saving_data': 'Saving and processing recorded data. Please wait..wav',
            'save_success': 'Save success! Ready for next record..wav',
        }

        # 验证文件是否存在
        if self.enabled:
            self._verify_files()

        # 播放队列 - 确保语音按顺序播放，不会同时播放
        self.play_queue = queue.Queue()
        self.queue_thread = None
        self.queue_running = False

        # 启动队列处理线程
        if self.enabled:
            self._start_queue_thread()

    def _verify_files(self):
        """验证所有语音文件是否存在"""
        missing_files = []
        for key, filename in self.voice_files.items():
            file_path = self.assets_dir / filename
            if not file_path.exists():
                missing_files.append(filename)

        if missing_files:
            Logger.warning(f"VoiceManager: 缺失语音文件: {missing_files}")
            # 不禁用功能，只是某些提示可能无法播放

    def _start_queue_thread(self):
        """启动队列处理线程"""
        self.queue_running = True
        self.queue_thread = threading.Thread(
            target=self._process_queue,
            daemon=True
        )
        self.queue_thread.start()
        Logger.info("VoiceManager: 语音队列线程已启动")

    def _process_queue(self):
        """处理播放队列（在后台线程中运行）"""
        while self.queue_running:
            try:
                # 从队列获取语音文件（阻塞等待）
                audio_file = self.play_queue.get(timeout=1.0)

                if audio_file is None:
                    # None是停止信号
                    break

                # 播放音频（阻塞）
                self._play_audio_sync(audio_file)

                self.play_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                Logger.error(f"VoiceManager: 队列处理错误 - {e}")

        Logger.info("VoiceManager: 语音队列线程已停止")

    def _play_audio_sync(self, audio_file):
        """
        同步播放音频（阻塞）

        Args:
            audio_file: 音频文件路径
        """
        try:
            from playsound import playsound
            playsound(str(audio_file))
        except ImportError:
            Logger.warning("VoiceManager: playsound未安装，无法播放语音")
            self.enabled = False
        except Exception as e:
            Logger.error(f"VoiceManager: 播放失败 - {e}")

    def play(self, voice_key, blocking=False):
        """
        播放指定的语音提示（通过队列，确保顺序播放）

        Args:
            voice_key: 语音键名 ('start_recording', 'stop_recording', etc.)
            blocking: 是否阻塞等待播放完成（默认False，非阻塞）
                     注意：即使blocking=False，语音也会按顺序在队列中播放

        Returns:
            bool: 是否成功加入播放队列
        """
        if not self.enabled:
            return False

        if voice_key not in self.voice_files:
            Logger.warning(f"VoiceManager: 未知的语音键: {voice_key}")
            return False

        filename = self.voice_files[voice_key]
        audio_file = self.assets_dir / filename

        if not audio_file.exists():
            Logger.warning(f"VoiceManager: 语音文件不存在: {filename}")
            return False

        Logger.info(f"VoiceManager: 加入播放队列 - {voice_key}")

        # 将音频文件加入队列
        self.play_queue.put(audio_file)

        # 如果需要阻塞等待
        if blocking:
            self.wait()

        return True

    def start_recording(self, blocking=False):
        """播放"开始录制"提示"""
        return self.play('start_recording', blocking)

    def stop_recording(self, blocking=False):
        """播放"停止录制"提示"""
        return self.play('stop_recording', blocking)

    def saving_data(self, blocking=False):
        """播放"正在保存数据"提示"""
        return self.play('saving_data', blocking)

    def save_success(self, blocking=False):
        """播放"保存成功"提示"""
        return self.play('save_success', blocking)

    def wait(self):
        """等待队列中所有语音播放完成"""
        self.play_queue.join()

    def shutdown(self):
        """关闭语音管理器"""
        self.queue_running = False
        if self.queue_thread and self.queue_thread.is_alive():
            # 发送停止信号
            self.play_queue.put(None)
            self.queue_thread.join(timeout=2.0)
        Logger.info("VoiceManager: 已关闭")
