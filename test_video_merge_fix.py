#!/usr/bin/env python3
"""
Test script to verify video merger correctly includes all sensors
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import cv2
import numpy as np
from pathlib import Path
from data.video_merger import merge_session_videos


def test_merge_includes_all_sensors():
    """Test that merged video includes all sensor videos"""
    print("=" * 60)
    print("Testing Video Merger - All Sensors Included")
    print("=" * 60)

    # Find a test session
    session_dir = Path('./data/session_20251018_161359')

    if not session_dir.exists():
        print(f"✗ Session directory not found: {session_dir}")
        return False

    # List individual videos
    video_files = sorted([f for f in session_dir.glob("*.mp4") if 'merged' not in f.name])

    print(f"\n[1] Found {len(video_files)} individual sensor videos:")
    for video_file in video_files:
        cap = cv2.VideoCapture(str(video_file))
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            print(f"    - {video_file.name}: {width}x{height}, {frame_count} frames")
            cap.release()

    # Delete old merged video if exists
    merged_path = session_dir / f"{session_dir.name}_merged.mp4"
    if merged_path.exists():
        merged_path.unlink()
        print(f"\n[2] Deleted old merged video")

    # Merge videos
    print("\n[3] Merging videos with grid layout...")
    merged_video = merge_session_videos(session_dir, layout='grid')

    if not merged_video:
        print("✗ Merge failed")
        return False

    print(f"    ✓ Merged video created: {merged_video.name}")

    # Verify merged video
    print("\n[4] Verifying merged video contains all sensors...")
    cap = cv2.VideoCapture(str(merged_video))

    if not cap.isOpened():
        print("✗ Cannot open merged video")
        return False

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    print(f"    Merged video: {width}x{height} @ {fps}fps, {frame_count} frames")

    # Calculate expected grid layout
    num_videos = len(video_files)
    cols = int(np.ceil(np.sqrt(num_videos)))
    rows = int(np.ceil(num_videos / cols))
    cell_width = width // cols
    cell_height = height // rows

    print(f"    Grid layout: {cols} cols x {rows} rows")
    print(f"    Cell size: {cell_width}x{cell_height}")

    # Read first frame and check each grid cell
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("✗ Cannot read frame from merged video")
        return False

    print("\n[5] Checking grid cells for content...")
    all_cells_have_content = True

    for idx in range(num_videos):
        row = idx // cols
        col = idx % cols

        # Extract cell
        y_start = row * cell_height
        y_end = y_start + cell_height
        x_start = col * cell_width
        x_end = x_start + cell_width

        cell = frame[y_start:y_end, x_start:x_end]

        # Check if cell has content
        nonzero = np.count_nonzero(cell)
        total = cell.size

        if nonzero > 0:
            print(f"    Cell [{row},{col}] (video {idx+1}): ✓ Has content ({nonzero:,}/{total:,} pixels)")
        else:
            print(f"    Cell [{row},{col}] (video {idx+1}): ✗ Empty")
            all_cells_have_content = False

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    print("=" * 60)
    print(f"✓ Found {len(video_files)} individual videos")
    print(f"✓ Merged video created successfully")
    print(f"✓ Grid layout: {cols}x{rows}")

    if all_cells_have_content:
        print(f"✓ ALL {num_videos} sensors are visible in merged video!")
        print("=" * 60)
        return True
    else:
        print(f"✗ Some sensors are missing from merged video")
        print("=" * 60)
        return False


if __name__ == '__main__':
    success = test_merge_includes_all_sensors()

    if success:
        print("\n🎉 Video merger is working correctly!")
        print("All sensors are included in the merged video.")
        sys.exit(0)
    else:
        print("\n❌ Video merger test failed")
        sys.exit(1)
