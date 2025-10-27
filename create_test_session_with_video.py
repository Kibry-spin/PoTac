#!/usr/bin/env python3
"""
Create a test session with video files for visualization testing
"""
import numpy as np
import cv2
import time
from pathlib import Path
from src.data.pkl_saver import TimestampAlignedDataSaver

def create_test_video(output_path, num_frames=100, fps=30):
    """Create a simple test video with frame numbers"""
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    for i in range(num_frames):
        # Create frame with frame number
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Add gradient background
        for y in range(height):
            frame[y, :, 0] = int((y / height) * 255)  # Blue gradient

        # Add frame number
        text = f"Frame {i+1}/{num_frames}"
        cv2.putText(frame, text, (width//2 - 100, height//2),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        # Add timestamp
        timestamp = i / fps
        time_text = f"Time: {timestamp:.2f}s"
        cv2.putText(frame, time_text, (width//2 - 80, height//2 + 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1)

        writer.write(frame)

    writer.release()
    print(f"✓ Created test video: {output_path}")


def main():
    print("Creating test session with video files...")
    print("=" * 70)

    # Create session
    session_name = "test_session_viz"
    output_dir = "./test_data"

    saver = TimestampAlignedDataSaver(output_dir, session_name)
    session_dir = Path(output_dir) / session_name

    # Add sensor metadata
    print("\n[1] Adding sensor metadata")
    saver.add_sensor_metadata('oak_camera', {
        'sensor_id': 'oak_camera',
        'sensor_name': 'OAK_Camera',
        'fps': 30,
        'resolution': (640, 480),
        'video_file': 'OAK_Camera_test_session_viz.mp4'
    })

    # Add ArUco metadata
    print("[2] Adding ArUco metadata")
    saver.add_aruco_metadata({
        'enabled': True,
        'target_ids': [0, 1],
        'marker_size': 0.015,
        'calibrated': True,
        'dictionary': 'DICT_4X4_250'
    })

    # Start recording
    print("[3] Simulating recording session")
    saver.start_recording()

    # Simulate 100 frames at 30 FPS
    num_frames = 100
    fps = 30

    for i in range(num_frames):
        timestamp = i / fps

        # Simulate ArUco detection with varying distance
        # Pattern: start far, come close, then move away
        if i < 30:
            # Moving closer
            distance = 150.0 - (i * 2.0)  # 150mm -> 90mm
        elif i < 70:
            # Staying close with variation
            distance = 90.0 + np.sin(i * 0.3) * 10.0  # 80-100mm
        else:
            # Moving away
            distance = 90.0 + ((i - 70) * 2.0)  # 90mm -> 150mm

        # Markers detected 80% of the time
        if i % 5 != 0:
            # Calculate correct distances from tvec positions
            left_tvec = np.array([0.0, 0.0, 0.5])
            right_tvec = np.array([distance/1000.0, 0.0, 0.5])

            # 3D absolute distance
            dist_3d = np.linalg.norm(right_tvec - left_tvec) * 1000.0

            # Horizontal distance (XY plane only, ignore Z)
            dist_hor = np.sqrt((right_tvec[0] - left_tvec[0])**2 +
                              (right_tvec[1] - left_tvec[1])**2) * 1000.0

            aruco_results = {
                'detection_count': 2,
                'left_marker': {
                    'id': 0,
                    'tvec': left_tvec.tolist(),
                    'detected': True
                },
                'right_marker': {
                    'id': 1,
                    'tvec': right_tvec.tolist(),
                    'detected': True
                },
                'real_distance_3d': float(dist_3d),
                'horizontal_distance': float(dist_hor),
                'marker_distance': distance * 2.0,  # Pixel distance (arbitrary)
                'calibrated': True,
                'enabled': True,
                'frame_seq_num': i  # Simulated frame sequence number
            }
        else:
            # Not detected
            aruco_results = {
                'detection_count': 0,
                'left_marker': None,
                'right_marker': None,
                'real_distance_3d': None,
                'horizontal_distance': None,
                'marker_distance': None,
                'calibrated': True,
                'enabled': True,
                'frame_seq_num': i  # Simulated frame sequence number
            }

        saver.add_camera_frame(timestamp, aruco_results)

    print(f"  ✓ Recorded {num_frames} frames")

    # Stop recording
    time.sleep(0.1)
    saver.stop_recording()

    # Save PKL
    print("[4] Saving PKL file")
    pkl_path = saver.finalize_and_save()
    print(f"  ✓ PKL saved: {pkl_path}")

    # Create test video
    print("[5] Creating test video")
    video_path = session_dir / "OAK_Camera_test_session_viz.mp4"
    create_test_video(video_path, num_frames, fps)

    print("\n" + "=" * 70)
    print("✓ Test session created successfully!")
    print(f"\nSession directory: {session_dir}")
    print(f"PKL file: {pkl_path}")
    print(f"Video file: {video_path}")
    print(f"\nTo visualize:")
    print(f"  python visualize_session.py {session_dir}")

    return session_dir


if __name__ == "__main__":
    try:
        session_dir = main()
        exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
