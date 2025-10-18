#!/usr/bin/env python3
"""
Standalone ArUco marker detection script for video files
Processes video files and outputs annotated versions with detected ArUco markers
"""

import cv2
import numpy as np
import argparse
import os
from pathlib import Path
import time


class VideoArUcoProcessor:
    """Process video files to detect and annotate ArUco markers"""

    def __init__(self, dictionary_type='DICT_6X6_250', marker_size=0.015, target_ids=[0, 1]):
        # Initialize ArUco detector
        self.dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dictionary_type))
        self.detector_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.detector_params)

        # Marker settings
        self.marker_size = marker_size
        self.target_ids = set(target_ids)  # Only detect these IDs

        # Setup ultra-sensitive parameters for small markers (15mm)
        self._setup_sensitive_parameters()

        # Statistics
        self.stats = {
            'total_frames': 0,
            'frames_with_markers': 0,
            'total_markers_detected': 0,
            'unique_marker_ids': set()
        }

    def _setup_sensitive_parameters(self):
        """Setup detector parameters optimized for small 15mm markers"""
        # EXTREMELY sensitive parameters for tiny 15mm markers
        self.detector_params.minMarkerPerimeterRate = 0.005  # Even more sensitive to very small markers
        self.detector_params.maxMarkerPerimeterRate = 6.0    # Allow larger range

        # Adaptive threshold parameters - ultra aggressive for 15mm
        self.detector_params.adaptiveThreshWinSizeMin = 3
        self.detector_params.adaptiveThreshWinSizeMax = 31   # Increased range
        self.detector_params.adaptiveThreshWinSizeStep = 8
        self.detector_params.adaptiveThreshConstant = 5      # Lower threshold

        # Polygonal approximation - very lenient for small markers
        self.detector_params.polygonalApproxAccuracyRate = 0.15  # Even more lenient for 15mm

        # Minimum distance - allow very close 15mm markers
        self.detector_params.minMarkerDistanceRate = 0.005

        # Candidate detection - ultra sensitive for 15mm
        self.detector_params.minCornerDistanceRate = 0.005   # Allow very close corners
        self.detector_params.minDistanceToBorder = 0         # Allow markers at border

        # Marker border detection
        self.detector_params.markerBorderBits = 1

        # Otsu threshold - extremely sensitive for 15mm
        self.detector_params.minOtsuStdDev = 1.5             # Much lower for tiny markers

        # Perspective removal - optimized for 15mm
        self.detector_params.perspectiveRemovePixelPerCell = 6        # Smaller cells for tiny markers
        self.detector_params.perspectiveRemoveIgnoredMarginPerCell = 0.05  # Smaller margin

        # Error correction - maximum tolerance for 15mm markers
        self.detector_params.maxErroneousBitsInBorderRate = 0.6      # Higher tolerance
        self.detector_params.errorCorrectionRate = 1.0              # Maximum correction

        # Corner refinement - optimized for 15mm precision
        self.detector_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        self.detector_params.cornerRefinementWinSize = 3             # Smaller window for tiny markers
        self.detector_params.cornerRefinementMaxIterations = 50     # More iterations
        self.detector_params.cornerRefinementMinAccuracy = 0.005    # Higher precision

        # Additional parameters for very small markers
        if hasattr(self.detector_params, 'aprilTagQuadDecimate'):
            self.detector_params.aprilTagQuadDecimate = 1.0          # No decimation
        if hasattr(self.detector_params, 'aprilTagQuadSigma'):
            self.detector_params.aprilTagQuadSigma = 0.0             # No blur

        print("ArUco detector configured for ULTRA-SENSITIVE 15mm marker detection")

    def _enhance_frame_for_detection(self, frame):
        """Apply enhanced image processing specifically for 15mm ArUco detection"""
        # Convert to grayscale
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame.copy()

        # 1. Noise reduction for better small marker detection
        denoised = cv2.bilateralFilter(gray, 5, 50, 50)

        # 2. CLAHE with smaller tile size for 15mm markers
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4,4))  # Smaller tiles for tiny markers
        enhanced = clahe.apply(denoised)

        # 3. Enhanced sharpening specifically for small features
        # Unsharp masking for better edge definition
        gaussian = cv2.GaussianBlur(enhanced, (3, 3), 1.0)
        unsharp_mask = cv2.addWeighted(enhanced, 1.5, gaussian, -0.5, 0)
        unsharp_mask = np.clip(unsharp_mask, 0, 255).astype(np.uint8)

        # 4. Additional sharpening kernel for tiny markers
        kernel = np.array([[-1,-1,-1], [-1,12,-1], [-1,-1,-1]], dtype=np.float32) / 4
        sharpened = cv2.filter2D(unsharp_mask, -1, kernel)
        sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)

        # 5. Morphological operations to clean up small features
        kernel_morph = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        cleaned = cv2.morphologyEx(sharpened, cv2.MORPH_CLOSE, kernel_morph)

        return cleaned

    def detect_markers_in_frame(self, frame):
        """Detect ArUco markers in a single frame"""
        # Enhance frame for detection
        enhanced_frame = self._enhance_frame_for_detection(frame)

        # Detect markers
        corners, ids, rejected = self.detector.detectMarkers(enhanced_frame)

        # Filter for target IDs only
        filtered_corners = []
        filtered_ids = []

        if corners is not None and ids is not None and len(corners) > 0:
            ids_flat = ids.flatten()
            for i, marker_id in enumerate(ids_flat):
                if marker_id in self.target_ids:
                    filtered_corners.append(corners[i])
                    filtered_ids.append(marker_id)

        # Convert back to numpy arrays if we have results
        if filtered_corners:
            filtered_corners = np.array(filtered_corners)
            filtered_ids = np.array(filtered_ids).reshape(-1, 1)
        else:
            filtered_corners = None
            filtered_ids = None

        # Update statistics with filtered results only
        self.stats['total_frames'] += 1
        if filtered_ids is not None and len(filtered_ids) > 0:
            self.stats['frames_with_markers'] += 1
            self.stats['total_markers_detected'] += len(filtered_ids)
            for marker_id in filtered_ids.flatten():
                self.stats['unique_marker_ids'].add(int(marker_id))

        return filtered_corners, filtered_ids, rejected

    def annotate_frame(self, frame, corners, ids, rejected=None, show_rejected=False):
        """Annotate frame with detected target markers only"""
        annotated = frame.copy()

        # Draw detected target markers only
        if corners is not None and len(corners) > 0:
            # Draw marker outlines and IDs
            cv2.aruco.drawDetectedMarkers(annotated, corners, ids)

            # Add marker information text with labels
            for i, (corner, marker_id) in enumerate(zip(corners, ids.flatten())):
                # Get marker center
                center = np.mean(corner[0], axis=0).astype(int)

                # Determine label and color
                if marker_id == 0:
                    label = "LEFT (ID:0)"
                    color = (0, 255, 0)  # Green
                elif marker_id == 1:
                    label = "RIGHT (ID:1)"
                    color = (0, 0, 255)  # Red
                else:
                    label = f"ID:{marker_id}"
                    color = (255, 255, 0)  # Yellow

                # Draw label
                text_pos = (int(center[0] - 50), int(center[1] - 20))
                cv2.putText(annotated, label, text_pos, cv2.FONT_HERSHEY_SIMPLEX,
                           0.7, color, 2)

                # Draw marker center
                cv2.circle(annotated, tuple(center), 5, color, -1)

        # Only draw rejected candidates if explicitly requested for debugging
        if show_rejected and rejected is not None and len(rejected) > 0:
            for rejected_corners in rejected:
                if rejected_corners is not None and len(rejected_corners) > 0:
                    # Draw rejected candidates with red outline
                    pts = np.array(rejected_corners, dtype=np.int32)
                    cv2.polylines(annotated, [pts], True, (0, 0, 255), 1)

        # Add frame statistics - only show target markers
        target_count = len(ids) if ids is not None else 0
        stats_text = f"Target Markers: {target_count} (ID: 0=LEFT, 1=RIGHT)"

        cv2.putText(annotated, stats_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                   0.7, (255, 255, 255), 2)
        cv2.putText(annotated, stats_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                   0.7, (0, 0, 0), 1)

        return annotated

    def process_video(self, input_path, output_path=None, show_rejected=False):
        """Process entire video file"""
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input video not found: {input_path}")

        # Generate output path if not provided
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_aruco_detected{input_path.suffix}"
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

                # Detect markers
                corners, ids, rejected = self.detect_markers_in_frame(frame)

                # Annotate frame - rejected candidates only shown if explicitly requested
                annotated_frame = self.annotate_frame(frame, corners, ids, rejected, show_rejected)

                # Write frame
                out.write(annotated_frame)

                frame_count += 1

                # Progress update
                if frame_count % 30 == 0 or frame_count == total_frames:
                    progress = (frame_count / total_frames) * 100
                    elapsed_time = time.time() - start_time
                    fps_actual = frame_count / elapsed_time if elapsed_time > 0 else 0
                    print(f"Progress: {progress:.1f}% ({frame_count}/{total_frames}) "
                          f"- Processing FPS: {fps_actual:.1f}")

        finally:
            cap.release()
            out.release()

        # Print final statistics
        self._print_statistics()

        print(f"\nProcessing complete!")
        print(f"Output saved to: {output_path}")

        return output_path

    def _print_statistics(self):
        """Print detection statistics"""
        print("\n" + "="*50)
        print("ARUCO DETECTION STATISTICS")
        print("="*50)
        print(f"Total frames processed: {self.stats['total_frames']}")
        print(f"Frames with markers: {self.stats['frames_with_markers']}")
        print(f"Detection rate: {(self.stats['frames_with_markers']/self.stats['total_frames']*100):.1f}%")
        print(f"Total markers detected: {self.stats['total_markers_detected']}")
        print(f"Unique marker IDs found: {sorted(list(self.stats['unique_marker_ids']))}")
        print(f"Average markers per frame: {(self.stats['total_markers_detected']/self.stats['total_frames']):.2f}")
        print("="*50)


def main():
    parser = argparse.ArgumentParser(description='Detect and annotate ArUco markers in video files')
    parser.add_argument('input_video', help='Input video file path')
    parser.add_argument('-o', '--output', help='Output video file path (optional)')
    parser.add_argument('-d', '--dictionary', default='DICT_6X6_250',
                       help='ArUco dictionary type (default: DICT_6X6_250)')
    parser.add_argument('-s', '--marker-size', type=float, default=0.015,
                       help='Marker size in meters (default: 0.015 for 15mm)')
    parser.add_argument('--show-rejected', action='store_true',
                       help='Show rejected marker candidates in red')
    parser.add_argument('--target-ids', nargs='+', type=int, default=[0, 1],
                       help='Target marker IDs to detect (default: 0 1)')

    args = parser.parse_args()

    try:
        # Create processor
        processor = VideoArUcoProcessor(
            dictionary_type=args.dictionary,
            marker_size=args.marker_size,
            target_ids=args.target_ids
        )

        # Process video
        output_path = processor.process_video(
            input_path=args.input_video,
            output_path=args.output,
            show_rejected=args.show_rejected
        )

        print(f"\nSuccess! Processed video saved to: {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())