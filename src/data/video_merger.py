"""
Video Merger - Merge multiple sensor videos into single combined view
"""

import cv2
import numpy as np
from pathlib import Path
from kivy.logger import Logger
import threading


class VideoMerger:
    """Merge multiple videos into a single combined video"""

    def __init__(self, output_path, layout='grid', fps=30):
        """
        Initialize video merger

        Args:
            output_path: Output video file path
            layout: Layout type ('grid', 'horizontal', 'vertical')
            fps: Output video frame rate
        """
        self.output_path = Path(output_path)
        self.layout = layout
        self.fps = fps

        self.video_readers = []
        self.writer = None
        self.total_frames = 0

    def add_video(self, video_path, label=None):
        """
        Add a video to merge

        Args:
            video_path: Path to video file
            label: Optional label to display on video
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                Logger.error(f"VideoMerger: Failed to open video: {video_path}")
                return False

            # Get video info
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            self.video_readers.append({
                'path': video_path,
                'cap': cap,
                'label': label or Path(video_path).stem,
                'width': width,
                'height': height,
                'fps': fps,
                'frame_count': frame_count
            })

            Logger.info(f"VideoMerger: Added video '{label}' - {width}x{height} @ {fps}fps, {frame_count} frames")
            return True

        except Exception as e:
            Logger.error(f"VideoMerger: Error adding video - {e}")
            return False

    def merge(self, progress_callback=None):
        """
        Merge all videos into combined output

        Args:
            progress_callback: Optional callback function(progress_percent)

        Returns:
            True if successful, False otherwise
        """
        if not self.video_readers:
            Logger.error("VideoMerger: No videos to merge")
            return False

        try:
            # Calculate output dimensions based on layout
            output_width, output_height = self._calculate_output_dimensions()

            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(
                str(self.output_path),
                fourcc,
                self.fps,
                (output_width, output_height)
            )

            if not self.writer.isOpened():
                Logger.error("VideoMerger: Failed to create output video writer")
                return False

            Logger.info(f"VideoMerger: Merging {len(self.video_readers)} videos -> {output_width}x{output_height}")

            # Find maximum frame count
            max_frames = max(v['frame_count'] for v in self.video_readers)

            # Process frames
            frame_idx = 0
            while frame_idx < max_frames:
                # Read frames from all videos
                frames = []
                for video_info in self.video_readers:
                    ret, frame = video_info['cap'].read()

                    if not ret:
                        # Use last frame or black frame if video ended
                        if len(frames) > 0 and hasattr(self, 'last_frame'):
                            frame = self.last_frame.copy()
                        else:
                            frame = np.zeros((video_info['height'], video_info['width'], 3), dtype=np.uint8)

                    # Add label
                    frame = self._add_label(frame, video_info['label'])
                    frames.append(frame)

                # Combine frames according to layout
                combined_frame = self._combine_frames(frames, output_width, output_height)

                # Write combined frame
                self.writer.write(combined_frame)
                self.total_frames += 1
                frame_idx += 1

                # Progress callback
                if progress_callback and frame_idx % 30 == 0:
                    progress = (frame_idx / max_frames) * 100
                    progress_callback(progress)

            Logger.info(f"VideoMerger: Merge complete - {self.total_frames} frames written")
            return True

        except Exception as e:
            Logger.error(f"VideoMerger: Merge failed - {e}")
            return False

        finally:
            self._cleanup()

    def _calculate_output_dimensions(self):
        """Calculate output video dimensions based on layout"""
        if not self.video_readers:
            return (640, 480)

        if self.layout == 'horizontal':
            # Stack horizontally
            total_width = sum(v['width'] for v in self.video_readers)
            max_height = max(v['height'] for v in self.video_readers)
            return (total_width, max_height)

        elif self.layout == 'vertical':
            # Stack vertically
            max_width = max(v['width'] for v in self.video_readers)
            total_height = sum(v['height'] for v in self.video_readers)
            return (max_width, total_height)

        else:  # grid layout
            # Calculate grid dimensions
            num_videos = len(self.video_readers)
            cols = int(np.ceil(np.sqrt(num_videos)))
            rows = int(np.ceil(num_videos / cols))

            # Use a reasonable uniform cell size for all videos
            # Find the video with median aspect ratio and use 720p as base height
            target_height = 720

            # Calculate average aspect ratio
            aspect_ratios = [v['width'] / v['height'] for v in self.video_readers]
            avg_aspect = sum(aspect_ratios) / len(aspect_ratios)

            # Use 16:9 as default if average is close to it, otherwise use calculated average
            if 1.5 <= avg_aspect <= 2.0:
                base_width = int(target_height * 16 / 9)  # 1280
            else:
                base_width = int(target_height * avg_aspect)

            base_height = target_height

            return (base_width * cols, base_height * rows)

    def _combine_frames(self, frames, output_width, output_height):
        """Combine multiple frames according to layout"""
        if not frames:
            return np.zeros((output_height, output_width, 3), dtype=np.uint8)

        if self.layout == 'horizontal':
            # Resize all to same height
            target_height = output_height
            resized_frames = []
            for frame in frames:
                h, w = frame.shape[:2]
                aspect_ratio = w / h
                new_width = int(target_height * aspect_ratio)
                resized = cv2.resize(frame, (new_width, target_height))
                resized_frames.append(resized)

            return np.hstack(resized_frames)

        elif self.layout == 'vertical':
            # Resize all to same width
            target_width = output_width
            resized_frames = []
            for frame in frames:
                h, w = frame.shape[:2]
                aspect_ratio = h / w
                new_height = int(target_width * aspect_ratio)
                resized = cv2.resize(frame, (target_width, new_height))
                resized_frames.append(resized)

            return np.vstack(resized_frames)

        else:  # grid layout
            num_videos = len(frames)
            cols = int(np.ceil(np.sqrt(num_videos)))
            rows = int(np.ceil(num_videos / cols))

            cell_width = output_width // cols
            cell_height = output_height // rows

            # Create output frame
            output = np.zeros((output_height, output_width, 3), dtype=np.uint8)

            # Place frames in grid
            for idx, frame in enumerate(frames):
                row = idx // cols
                col = idx % cols

                # Resize frame to fit cell
                resized = cv2.resize(frame, (cell_width, cell_height))

                # Calculate position
                y_start = row * cell_height
                y_end = y_start + cell_height
                x_start = col * cell_width
                x_end = x_start + cell_width

                # Place frame
                output[y_start:y_end, x_start:x_end] = resized

            return output

    def _add_label(self, frame, label):
        """Add label text to frame"""
        if not label:
            return frame

        frame_with_label = frame.copy()

        # Add semi-transparent background for text
        h, w = frame.shape[:2]
        overlay = frame_with_label.copy()
        cv2.rectangle(overlay, (0, 0), (w, 40), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame_with_label, 0.4, 0, frame_with_label)

        # Add text
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        color = (255, 255, 255)

        text_size = cv2.getTextSize(label, font, font_scale, thickness)[0]
        text_x = (w - text_size[0]) // 2
        text_y = 28

        cv2.putText(frame_with_label, label, (text_x, text_y),
                    font, font_scale, color, thickness, cv2.LINE_AA)

        return frame_with_label

    def _cleanup(self):
        """Cleanup resources"""
        # Release video readers
        for video_info in self.video_readers:
            if video_info['cap']:
                video_info['cap'].release()

        # Release writer
        if self.writer:
            self.writer.release()
            self.writer = None

        Logger.info("VideoMerger: Resources cleaned up")


def merge_session_videos(session_dir, output_name=None, layout='grid', progress_callback=None):
    """
    Convenience function to merge all videos in a session directory

    Args:
        session_dir: Session directory containing video files
        output_name: Output filename (auto-generated if None)
        layout: Layout type ('grid', 'horizontal', 'vertical')
        progress_callback: Optional progress callback

    Returns:
        Path to merged video if successful, None otherwise
    """
    session_dir = Path(session_dir)

    if not session_dir.exists():
        Logger.error(f"merge_session_videos: Session directory not found: {session_dir}")
        return None

    # Find all MP4 files (exclude already merged videos)
    video_files = sorted(session_dir.glob("*.mp4"))

    # Generate output name
    if output_name is None:
        output_name = f"{session_dir.name}_merged.mp4"

    output_path = session_dir / output_name

    # Filter out the merged video itself and any other merged videos
    video_files = [f for f in video_files if 'merged' not in f.name.lower()]

    if not video_files:
        Logger.error(f"merge_session_videos: No video files found in {session_dir}")
        return None

    # Create merger
    merger = VideoMerger(output_path, layout=layout)

    # Add all videos
    for video_file in video_files:
        # Extract sensor name from filename (everything before the session name)
        # Example: "Left_GelSight_session_20231215_143022.mp4" -> "Left_GelSight"
        filename = video_file.stem
        session_name = session_dir.name
        if session_name in filename:
            sensor_name = filename.replace(f"_{session_name}", "").replace(session_name, "")
        else:
            # Fallback: use first part before underscore
            sensor_name = filename.split('_')[0]

        # Clean up sensor name
        sensor_name = sensor_name.strip('_')

        Logger.info(f"merge_session_videos: Adding '{sensor_name}' from {video_file.name}")
        merger.add_video(video_file, label=sensor_name)

    # Merge
    Logger.info(f"merge_session_videos: Merging {len(video_files)} videos...")
    if merger.merge(progress_callback):
        Logger.info(f"merge_session_videos: Merged video saved to {output_path}")
        return output_path
    else:
        Logger.error("merge_session_videos: Merge failed")
        return None
