#!/usr/bin/env python3
"""
Optimized ArUco marker detection script based on official DepthAI AprilTag examples
High-performance detection for 15mm markers using DICT_4X4_250
"""

import cv2
import numpy as np
import argparse
import os
from pathlib import Path
import time


class OptimizedVideoArUcoProcessor:
    """High-performance ArUco processor based on official DepthAI optimization patterns"""

    def __init__(self, dictionary_type='DICT_4X4_250', marker_size=0.015, target_ids=[0, 1]):
        # Initialize ArUco detector with optimized settings
        self.dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dictionary_type))
        self.detector_params = cv2.aruco.DetectorParameters()

        # Target settings
        self.marker_size = marker_size
        self.target_ids = set(target_ids)

        # Setup optimized detection parameters (based on DepthAI AprilTag approach)
        self._setup_optimized_parameters()

        # Create detector
        self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.detector_params)

        # Performance tracking
        self.stats = {
            'total_frames': 0,
            'frames_with_markers': 0,
            'total_markers_detected': 0,
            'unique_marker_ids': set()
        }

    def _setup_optimized_parameters(self):
        """Setup detection parameters optimized like DepthAI AprilTag examples"""
        print("Setting up optimized ArUco detection parameters...")

        # Based on AprilTag quadDecimate=4 and performance optimizations
        # Less aggressive preprocessing, more focused on actual detection
        self.detector_params.minMarkerPerimeterRate = 0.03  # More conservative
        self.detector_params.maxMarkerPerimeterRate = 4.0   # Reasonable range

        # Adaptive threshold - simplified like AprilTag
        self.detector_params.adaptiveThreshWinSizeMin = 5
        self.detector_params.adaptiveThreshWinSizeMax = 23
        self.detector_params.adaptiveThreshWinSizeStep = 10
        self.detector_params.adaptiveThreshConstant = 7

        # Polygonal approximation - more strict for accuracy
        self.detector_params.polygonalApproxAccuracyRate = 0.05

        # Distance and border parameters
        self.detector_params.minCornerDistanceRate = 0.05
        self.detector_params.minDistanceToBorder = 3
        self.detector_params.minMarkerDistanceRate = 0.05

        # Error correction - balanced approach
        self.detector_params.maxErroneousBitsInBorderRate = 0.35
        self.detector_params.errorCorrectionRate = 0.6

        # Border detection
        self.detector_params.markerBorderBits = 1

        # Otsu threshold - less sensitive to reduce false positives
        self.detector_params.minOtsuStdDev = 5.0

        # Perspective removal - optimized like AprilTag
        self.detector_params.perspectiveRemovePixelPerCell = 8
        self.detector_params.perspectiveRemoveIgnoredMarginPerCell = 0.13

        # Corner refinement - high precision
        self.detector_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        self.detector_params.cornerRefinementWinSize = 5
        self.detector_params.cornerRefinementMaxIterations = 30
        self.detector_params.cornerRefinementMinAccuracy = 0.1

        print("Optimized parameters configured for high-performance detection")

    def _preprocess_frame(self, frame):
        """Minimal preprocessing optimized for performance"""
        # Convert to grayscale efficiently
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame.copy()

        # Simple enhancement - similar to AprilTag approach
        # Apply mild CLAHE for contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        return enhanced

    def detect_markers_in_frame(self, frame):
        """High-performance marker detection"""
        # Minimal preprocessing for speed
        processed_frame = self._preprocess_frame(frame)

        # Detect all markers first
        corners, ids, rejected = self.detector.detectMarkers(processed_frame)

        # Filter for target IDs only
        filtered_corners = []
        filtered_ids = []

        if corners is not None and ids is not None and len(corners) > 0:
            ids_flat = ids.flatten()
            for i, marker_id in enumerate(ids_flat):
                if marker_id in self.target_ids:
                    filtered_corners.append(corners[i])
                    filtered_ids.append(marker_id)

        # Convert back to numpy arrays
        if filtered_corners:
            filtered_corners = np.array(filtered_corners)
            filtered_ids = np.array(filtered_ids).reshape(-1, 1)
        else:
            filtered_corners = None
            filtered_ids = None

        # Update statistics
        self.stats['total_frames'] += 1
        if filtered_ids is not None and len(filtered_ids) > 0:
            self.stats['frames_with_markers'] += 1
            self.stats['total_markers_detected'] += len(filtered_ids)
            for marker_id in filtered_ids.flatten():
                self.stats['unique_marker_ids'].add(int(marker_id))

        return filtered_corners, filtered_ids

    def draw_markers(self, frame, corners, ids):
        """Clean marker visualization like AprilTag examples"""
        annotated = frame.copy()

        if corners is not None and ids is not None and len(corners) > 0:
            # Draw marker outlines - clean style like AprilTag
            for i, (corner, marker_id) in enumerate(zip(corners, ids.flatten())):
                # Get corner points
                pts = corner[0].astype(int)

                # Draw marker outline with clean lines
                color = (0, 255, 0) if marker_id == 1 else (0, 0, 255)  # Green for 1, Red for 0
                cv2.polylines(annotated, [pts], True, color, 2, cv2.LINE_AA)

                # Calculate center
                center = tuple(np.mean(pts, axis=0).astype(int))

                # Draw clean ID label
                label = f"LEFT (ID:{marker_id})" if marker_id == 1 else f"RIGHT (ID:{marker_id})"
                text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                text_pos = (center[0] - text_size[0] // 2, center[1] - 10)

                # Background for text
                cv2.rectangle(annotated, (text_pos[0] - 5, text_pos[1] - text_size[1] - 5),
                             (text_pos[0] + text_size[0] + 5, text_pos[1] + 5), (255, 255, 255), -1)
                cv2.putText(annotated, label, text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

                # Draw center point
                cv2.circle(annotated, center, 5, color, -1)

        return annotated

    def process_video(self, input_path, output_path=None):
        """Process video with optimized detection"""
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input video not found: {input_path}")

        # Generate output path
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_optimized_aruco{input_path.suffix}"
        else:
            output_path = Path(output_path)

        print(f"Processing video: {input_path}")
        print(f"Output will be saved to: {output_path}")

        # Open input video
        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {input_path}")

        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        print(f"Video info: {width}x{height} @ {fps}fps, {total_frames} frames")

        # Setup output video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        if not out.isOpened():
            raise ValueError(f"Cannot create output video: {output_path}")

        # Reset statistics
        self.stats = {
            'total_frames': 0,
            'frames_with_markers': 0,
            'total_markers_detected': 0,
            'unique_marker_ids': set()
        }

        # Process frames
        frame_count = 0
        start_time = time.time()

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # High-performance detection
                corners, ids = self.detect_markers_in_frame(frame)

                # Clean visualization
                annotated_frame = self.draw_markers(frame, corners, ids)

                # Add performance info
                current_time = time.time()
                elapsed_time = current_time - start_time
                processing_fps = frame_count / elapsed_time if elapsed_time > 0 else 0

                fps_text = f"Processing FPS: {processing_fps:.1f}"
                cv2.putText(annotated_frame, fps_text, (10, annotated_frame.shape[0] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # Write frame
                out.write(annotated_frame)

                frame_count += 1

                # Progress update
                if frame_count % 30 == 0 or frame_count == total_frames:
                    progress = (frame_count / total_frames) * 100
                    print(f"Progress: {progress:.1f}% ({frame_count}/{total_frames}) "
                          f"- Processing FPS: {processing_fps:.1f}")

        finally:
            cap.release()
            out.release()

        # Print final statistics
        self._print_statistics()

        print(f"\nOptimized processing complete!")
        print(f"Output saved to: {output_path}")

        return output_path

    def _print_statistics(self):
        """Print detection statistics"""
        print("\n" + "="*50)
        print("OPTIMIZED ARUCO DETECTION STATISTICS")
        print("="*50)
        print(f"Total frames processed: {self.stats['total_frames']}")
        print(f"Frames with markers: {self.stats['frames_with_markers']}")
        if self.stats['total_frames'] > 0:
            print(f"Detection rate: {(self.stats['frames_with_markers']/self.stats['total_frames']*100):.1f}%")
        print(f"Total markers detected: {self.stats['total_markers_detected']}")
        print(f"Unique marker IDs found: {sorted(list(self.stats['unique_marker_ids']))}")
        if self.stats['total_frames'] > 0:
            print(f"Average markers per frame: {(self.stats['total_markers_detected']/self.stats['total_frames']):.2f}")
        print("="*50)


def main():
    parser = argparse.ArgumentParser(description='Optimized ArUco marker detection for video files')
    parser.add_argument('input_video', help='Input video file path')
    parser.add_argument('-o', '--output', help='Output video file path (optional)')
    parser.add_argument('-d', '--dictionary', default='DICT_4X4_250',
                       help='ArUco dictionary type (default: DICT_4X4_250)')
    parser.add_argument('-s', '--marker-size', type=float, default=0.015,
                       help='Marker size in meters (default: 0.015 for 15mm)')
    parser.add_argument('--target-ids', nargs='+', type=int, default=[0, 1],
                       help='Target marker IDs to detect (default: 0 1)')

    args = parser.parse_args()

    try:
        # Create optimized processor
        processor = OptimizedVideoArUcoProcessor(
            dictionary_type=args.dictionary,
            marker_size=args.marker_size,
            target_ids=args.target_ids
        )

        # Process video
        output_path = processor.process_video(
            input_path=args.input_video,
            output_path=args.output
        )

        print(f"\nSuccess! Optimized video saved to: {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())