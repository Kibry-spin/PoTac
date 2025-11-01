#!/usr/bin/env python3
"""
Inspect PKL session data to diagnose distance calculation issues
"""
import sys
import pickle
import numpy as np
from pathlib import Path


def inspect_pkl_data(pkl_path):
    """Inspect PKL data and show detailed information"""
    print(f"Inspecting PKL file: {pkl_path}")
    print("=" * 80)

    try:
        with open(pkl_path, 'rb') as f:
            data = pickle.load(f)

        # Show metadata
        metadata = data['metadata']
        print("\n[METADATA]")
        print(f"  Session: {metadata['session_name']}")
        print(f"  Duration: {metadata['duration']:.2f}s")
        print(f"  ArUco enabled: {metadata['aruco']['enabled']}")
        print(f"  Marker IDs: {metadata['aruco']['marker_ids']}")
        print(f"  Marker size: {metadata['aruco']['marker_size']}m")
        print(f"  Calibrated: {metadata['aruco']['calibrated']}")

        # Show data structure
        data_section = data['data']
        print(f"\n[DATA STRUCTURE]")
        print(f"  Keys: {list(data_section.keys())}")

        timestamps = data_section.get('timestamps', [])
        print(f"  Total frames: {len(timestamps)}")

        # Inspect ArUco data in detail
        if 'aruco' in data_section:
            aruco_data = data_section['aruco']
            print(f"\n[ARUCO DATA]")
            print(f"  Fields: {list(aruco_data.keys())}")

            left_det = aruco_data['left_detected']
            right_det = aruco_data['right_detected']
            dist_abs = aruco_data['distance_absolute']
            dist_hor = aruco_data['distance_horizontal']
            dist_pix = aruco_data['distance_pixel']
            left_pos = aruco_data['left_positions']
            right_pos = aruco_data['right_positions']

            print(f"\n  Detection rates:")
            print(f"    Left:  {np.sum(left_det)}/{len(left_det)} ({np.mean(left_det)*100:.1f}%)")
            print(f"    Right: {np.sum(right_det)}/{len(right_det)} ({np.mean(right_det)*100:.1f}%)")

            both_detected = left_det & right_det
            print(f"    Both:  {np.sum(both_detected)}/{len(both_detected)} ({np.mean(both_detected)*100:.1f}%)")

            # Check distance data
            valid_dist = ~np.isnan(dist_abs)
            print(f"\n  Distance measurements:")
            print(f"    Valid: {np.sum(valid_dist)}/{len(dist_abs)}")

            if np.any(valid_dist):
                print(f"    Absolute 3D:   {np.nanmin(dist_abs):.2f} - {np.nanmax(dist_abs):.2f} mm (mean: {np.nanmean(dist_abs):.2f})")
                print(f"    Horizontal:    {np.nanmin(dist_hor):.2f} - {np.nanmax(dist_hor):.2f} mm (mean: {np.nanmean(dist_hor):.2f})")
                print(f"    Pixel:         {np.nanmin(dist_pix):.2f} - {np.nanmax(dist_pix):.2f} px (mean: {np.nanmean(dist_pix):.2f})")

            # Detailed frame-by-frame inspection for first few frames with detection
            print(f"\n  [DETAILED FRAME INSPECTION]")
            print(f"  Showing first 10 frames where both markers detected:\n")

            count = 0
            for i in range(len(timestamps)):
                if both_detected[i] and count < 10:
                    left_p = left_pos[i]
                    right_p = right_pos[i]

                    # Manually calculate distance from positions
                    manual_dist_3d = np.linalg.norm(np.array(right_p) - np.array(left_p)) * 1000.0
                    manual_dist_hor = np.sqrt((right_p[0] - left_p[0])**2 + (right_p[1] - left_p[1])**2) * 1000.0

                    print(f"  Frame {i} (t={timestamps[i]:.3f}s):")
                    print(f"    Left pos:  [{left_p[0]:7.4f}, {left_p[1]:7.4f}, {left_p[2]:7.4f}] m")
                    print(f"    Right pos: [{right_p[0]:7.4f}, {right_p[1]:7.4f}, {right_p[2]:7.4f}] m")
                    print(f"    Stored abs distance:  {dist_abs[i]:7.2f} mm")
                    print(f"    Manual abs distance:  {manual_dist_3d:7.2f} mm")
                    print(f"    Stored hor distance:  {dist_hor[i]:7.2f} mm")
                    print(f"    Manual hor distance:  {manual_dist_hor:7.2f} mm")

                    # Check for discrepancy
                    if abs(dist_abs[i] - manual_dist_3d) > 0.1:
                        print(f"    ⚠️  MISMATCH in absolute distance: {abs(dist_abs[i] - manual_dist_3d):.2f} mm difference")
                    if abs(dist_hor[i] - manual_dist_hor) > 0.1:
                        print(f"    ⚠️  MISMATCH in horizontal distance: {abs(dist_hor[i] - manual_dist_hor):.2f} mm difference")
                    print()

                    count += 1

        print("=" * 80)
        print("✓ Inspection complete")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_pkl_data.py <pkl_file_or_session_dir>")
        print("\nExample:")
        print("  python inspect_pkl_data.py ./data/session_20241024_143052")
        print("  python inspect_pkl_data.py ./data/session_20241024_143052/session_20241024_143052_data.pkl")
        sys.exit(1)

    path = Path(sys.argv[1])

    # If directory, find PKL file
    if path.is_dir():
        pkl_files = list(path.glob("*_data.pkl"))
        if not pkl_files:
            print(f"Error: No PKL file found in {path}")
            sys.exit(1)
        pkl_path = pkl_files[0]
    else:
        pkl_path = path

    if not pkl_path.exists():
        print(f"Error: File not found: {pkl_path}")
        sys.exit(1)

    inspect_pkl_data(pkl_path)
