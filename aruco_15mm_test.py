#!/usr/bin/env python3
"""
Specialized test for 15mm ArUco markers with multiple detection strategies
"""

import cv2
import numpy as np
from pathlib import Path


def test_multiple_strategies(video_path):
    """Test multiple detection strategies for 15mm markers"""

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Cannot open video: {video_path}")
        return

    # Test on middle frame
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print("Could not read test frame")
        return

    print(f"Testing frame from middle of video ({total_frames//2}/{total_frames})")

    # Test different ArUco dictionaries
    dictionaries = [
        ('DICT_4X4_50', cv2.aruco.DICT_4X4_50),
        ('DICT_4X4_100', cv2.aruco.DICT_4X4_100),
        ('DICT_4X4_250', cv2.aruco.DICT_4X4_250),
        ('DICT_5X5_50', cv2.aruco.DICT_5X5_50),
        ('DICT_6X6_50', cv2.aruco.DICT_6X6_50),
        ('DICT_6X6_250', cv2.aruco.DICT_6X6_250),
    ]

    for dict_name, dict_type in dictionaries:
        print(f"\n--- Testing {dict_name} ---")

        # Setup detector
        dictionary = cv2.aruco.getPredefinedDictionary(dict_type)
        detector_params = cv2.aruco.DetectorParameters()

        # Ultra-aggressive settings for 15mm
        detector_params.minMarkerPerimeterRate = 0.001    # Extremely sensitive
        detector_params.maxMarkerPerimeterRate = 8.0
        detector_params.polygonalApproxAccuracyRate = 0.2  # Very lenient
        detector_params.minOtsuStdDev = 1.0               # Very low threshold
        detector_params.adaptiveThreshWinSizeMin = 3
        detector_params.adaptiveThreshWinSizeMax = 35
        detector_params.adaptiveThreshConstant = 3        # Very low
        detector_params.minCornerDistanceRate = 0.001
        detector_params.minDistanceToBorder = 0
        detector_params.maxErroneousBitsInBorderRate = 0.8  # Very tolerant
        detector_params.errorCorrectionRate = 1.0

        detector = cv2.aruco.ArucoDetector(dictionary, detector_params)

        # Test different preprocessing approaches
        preprocessing_methods = [
            ("Original", lambda x: cv2.cvtColor(x, cv2.COLOR_BGR2GRAY)),
            ("CLAHE", lambda x: apply_clahe(x)),
            ("Enhanced", lambda x: apply_15mm_enhancement(x)),
            ("Gaussian", lambda x: apply_gaussian_enhancement(x)),
            ("Adaptive", lambda x: apply_adaptive_threshold(x)),
        ]

        for prep_name, prep_func in preprocessing_methods:
            try:
                processed_frame = prep_func(frame)
                corners, ids, rejected = detector.detectMarkers(processed_frame)

                detected = len(corners) if corners is not None else 0
                rejected_count = len(rejected) if rejected is not None else 0

                print(f"  {prep_name:12}: {detected:3d} detected, {rejected_count:4d} rejected")

                if detected > 0:
                    print(f"    *** FOUND MARKERS: {ids.flatten().tolist()} ***")

                    # Save successful detection
                    annotated = frame.copy()
                    cv2.aruco.drawDetectedMarkers(annotated, corners, ids)
                    cv2.imwrite(f"success_{dict_name}_{prep_name}.jpg", annotated)

            except Exception as e:
                print(f"  {prep_name:12}: Error - {e}")


def apply_clahe(frame):
    """Apply CLAHE enhancement"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4,4))
    return clahe.apply(gray)


def apply_15mm_enhancement(frame):
    """Apply specialized 15mm enhancement"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Bilateral filter
    denoised = cv2.bilateralFilter(gray, 5, 50, 50)

    # CLAHE
    clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(3,3))
    enhanced = clahe.apply(denoised)

    # Unsharp masking
    gaussian = cv2.GaussianBlur(enhanced, (3, 3), 1.0)
    unsharp = cv2.addWeighted(enhanced, 2.0, gaussian, -1.0, 0)

    return np.clip(unsharp, 0, 255).astype(np.uint8)


def apply_gaussian_enhancement(frame):
    """Apply Gaussian-based enhancement"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Gaussian blur and subtract for edge enhancement
    blurred = cv2.GaussianBlur(gray, (5, 5), 2.0)
    enhanced = cv2.addWeighted(gray, 2.0, blurred, -1.0, 0)

    return np.clip(enhanced, 0, 255).astype(np.uint8)


def apply_adaptive_threshold(frame):
    """Apply adaptive thresholding"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Multiple adaptive thresholds and combine
    thresh1 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 11, 2)
    thresh2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)

    # Combine thresholds
    combined = cv2.bitwise_and(thresh1, thresh2)

    return combined


if __name__ == "__main__":
    video_path = "/home/kirdo/robo/PoTac/data/potac_video_20250926_192052_mp4v.mp4"
    test_multiple_strategies(video_path)