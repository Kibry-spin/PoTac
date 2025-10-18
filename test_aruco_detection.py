#!/usr/bin/env python3
"""
Test script to verify ArUco detection on video frames
Saves sample frames for inspection
"""

import cv2
import numpy as np
from pathlib import Path


def test_detection_on_frames(video_path, output_dir="./test_frames"):
    """Extract and test detection on sample frames"""

    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Cannot open video: {video_path}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Video has {total_frames} frames")

    # Setup ArUco detector with ultra-sensitive parameters
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    detector_params = cv2.aruco.DetectorParameters()

    # Ultra-sensitive settings for 15mm markers
    detector_params.minMarkerPerimeterRate = 0.01
    detector_params.maxMarkerPerimeterRate = 4.0
    detector_params.polygonalApproxAccuracyRate = 0.1
    detector_params.minOtsuStdDev = 2.0
    detector_params.adaptiveThreshWinSizeMin = 3
    detector_params.adaptiveThreshWinSizeMax = 23
    detector_params.adaptiveThreshConstant = 7

    detector = cv2.aruco.ArucoDetector(dictionary, detector_params)

    # Test on several frames
    test_frame_indices = [0, total_frames//4, total_frames//2, 3*total_frames//4, total_frames-1]

    for i, frame_idx in enumerate(test_frame_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()

        if not ret:
            continue

        print(f"\nTesting frame {frame_idx}")

        # Convert to grayscale and enhance
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply CLAHE enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)

        # Apply sharpening
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]], dtype=np.float32)
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)

        # Detect markers
        corners, ids, rejected = detector.detectMarkers(sharpened)

        print(f"  Detected: {len(corners) if corners is not None else 0} markers")
        print(f"  Rejected: {len(rejected) if rejected is not None else 0} candidates")

        # Save original frame
        cv2.imwrite(str(output_dir / f"frame_{frame_idx:03d}_original.jpg"), frame)

        # Save enhanced grayscale
        cv2.imwrite(str(output_dir / f"frame_{frame_idx:03d}_enhanced.jpg"), sharpened)

        # Create annotated version
        annotated = frame.copy()

        # Draw detected markers
        if corners is not None and len(corners) > 0:
            cv2.aruco.drawDetectedMarkers(annotated, corners, ids)
            print(f"  Marker IDs: {ids.flatten().tolist()}")

        # Draw rejected candidates
        if rejected is not None and len(rejected) > 0:
            for rejected_corners in rejected:
                if rejected_corners is not None and len(rejected_corners) > 0:
                    pts = np.array(rejected_corners, dtype=np.int32)
                    cv2.polylines(annotated, [pts], True, (0, 0, 255), 2)

        # Add info text
        info_text = f"Frame {frame_idx}: Detected={len(corners) if corners is not None else 0}, Rejected={len(rejected) if rejected is not None else 0}"
        cv2.putText(annotated, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(annotated, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 1)

        # Save annotated frame
        cv2.imwrite(str(output_dir / f"frame_{frame_idx:03d}_annotated.jpg"), annotated)

    cap.release()
    print(f"\nTest frames saved to: {output_dir}")


if __name__ == "__main__":
    video_path = "/home/kirdo/robo/PoTac/data/potac_video_20250926_192052_mp4v.mp4"
    test_detection_on_frames(video_path)