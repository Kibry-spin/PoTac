#!/usr/bin/env python3
"""
Diagnose video-data synchronization issues
"""
import sys
import cv2
import pickle
import numpy as np
from pathlib import Path


def diagnose_sync(session_dir):
    """Diagnose synchronization between video and PKL data"""
    print(f"Diagnosing synchronization in: {session_dir}")
    print("=" * 80)
    
    session_path = Path(session_dir)
    
    # Load PKL data
    pkl_files = list(session_path.glob("*_data.pkl"))
    if not pkl_files:
        print("Error: No PKL file found")
        return
    
    with open(pkl_files[0], 'rb') as f:
        data = pickle.load(f)
    
    metadata = data['metadata']
    data_section = data['data']
    
    print(f"\n[SESSION INFO]")
    print(f"  Session: {metadata['session_name']}")
    print(f"  Duration: {metadata['duration']:.2f}s")
    
    # Check video files
    print(f"\n[VIDEO FILES]")
    for sensor_id, sensor_meta in metadata['sensors'].items():
        video_file = sensor_meta.get('video_file')
        if video_file:
            video_path = session_path / video_file
            if video_path.exists():
                cap = cv2.VideoCapture(str(video_path))
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                duration = frame_count / fps if fps > 0 else 0
                cap.release()
                
                print(f"  {sensor_id}:")
                print(f"    File: {video_file}")
                print(f"    Frames: {frame_count}")
                print(f"    FPS: {fps}")
                print(f"    Duration: {duration:.2f}s")
    
    # Check PKL timestamps
    print(f"\n[PKL DATA]")
    timestamps = data_section.get('timestamps', [])
    print(f"  Timestamp entries: {len(timestamps)}")
    if len(timestamps) > 0:
        print(f"  First timestamp: {timestamps[0]:.3f}s")
        print(f"  Last timestamp: {timestamps[-1]:.3f}s")
        print(f"  Duration: {timestamps[-1] - timestamps[0]:.3f}s")
        
        # Calculate actual frame rate from timestamps
        if len(timestamps) > 1:
            intervals = np.diff(timestamps)
            avg_interval = np.mean(intervals)
            actual_fps = 1.0 / avg_interval if avg_interval > 0 else 0
            print(f"  Average interval: {avg_interval*1000:.2f}ms")
            print(f"  Calculated FPS: {actual_fps:.2f}")
            print(f"  Interval std: {np.std(intervals)*1000:.2f}ms")
    
    # Check ArUco data
    if 'aruco' in data_section:
        aruco_data = data_section['aruco']
        print(f"\n[ARUCO DATA]")
        print(f"  Data points: {len(aruco_data['left_detected'])}")
        
        both_detected = aruco_data['left_detected'] & aruco_data['right_detected']
        print(f"  Both markers detected: {np.sum(both_detected)}/{len(both_detected)}")
    
    # CRITICAL: Compare video frames vs PKL data points
    print(f"\n[SYNCHRONIZATION ANALYSIS]")
    
    # Get video frame count for oak_camera
    oak_video = None
    for sensor_id, sensor_meta in metadata['sensors'].items():
        if 'oak' in sensor_id.lower() or 'camera' in sensor_id.lower():
            video_file = sensor_meta.get('video_file')
            if video_file:
                video_path = session_path / video_file
                if video_path.exists():
                    cap = cv2.VideoCapture(str(video_path))
                    oak_video = {
                        'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                        'fps': cap.get(cv2.CAP_PROP_FPS)
                    }
                    cap.release()
                    break
    
    if oak_video:
        video_frames = oak_video['frame_count']
        pkl_frames = len(timestamps)
        
        print(f"  Video frames:     {video_frames}")
        print(f"  PKL data points:  {pkl_frames}")
        print(f"  Difference:       {abs(video_frames - pkl_frames)} frames")
        
        if video_frames != pkl_frames:
            print(f"\n  ⚠️  WARNING: Frame count mismatch!")
            print(f"  This will cause synchronization issues in visualization.")
            print(f"\n  Possible causes:")
            print(f"    1. GUI update rate != video capture rate")
            print(f"    2. Dropped frames during recording")
            print(f"    3. Timing differences between video and data threads")
            
            # Calculate expected alignment
            if pkl_frames > 0 and video_frames > 0:
                ratio = video_frames / pkl_frames
                print(f"\n  Video/PKL ratio: {ratio:.4f}")
                if abs(ratio - 1.0) > 0.01:
                    print(f"  Video has {(ratio-1)*100:.1f}% {'more' if ratio > 1 else 'fewer'} frames than PKL data")
        else:
            print(f"  ✓ Frame counts match perfectly")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python diagnose_sync.py <session_directory>")
        sys.exit(1)
    
    diagnose_sync(sys.argv[1])
