#!/usr/bin/env python3
"""
Convert Tac3D NPZ data to image sequence
Generates 2D heatmap images from displacement data for visualization
"""

import numpy as np
import cv2
from pathlib import Path
import argparse
import json


def npz_to_images(npz_path, output_dir=None, colormap=cv2.COLORMAP_JET,
                  width=400, height=400, use_global_norm=True):
    """
    Convert Tac3D NPZ data to image sequence

    Output structure matches visuotactile sensor format:
    - Images placed directly in sensor folder
    - frames_metadata.json with vt-compatible format

    Args:
        npz_path: Path to NPZ file
        output_dir: Output directory for images (None = parent folder of npz)
        colormap: OpenCV colormap
        width: Image width
        height: Image height
        use_global_norm: Use global normalization across all frames

    Returns:
        output_dir: Path to output directory
    """
    npz_path = Path(npz_path)

    # Determine output directory - use parent folder to match vt sensor structure
    if output_dir is None:
        output_dir = npz_path.parent  # Changed: direct to sensor folder
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading data from {npz_path}...")

    # Load NPZ data
    data = np.load(npz_path)
    displacements = data['displacements']  # (N_frames, 400, 3)
    capture_timestamps = data['capture_timestamps']
    sensor_sn = str(data['sensor_sn'][0])

    n_frames = len(displacements)
    print(f"  Sensor SN: {sensor_sn}")
    print(f"  Total frames: {n_frames}")
    print(f"  Displacement shape: {displacements.shape}")

    # Calculate displacement magnitudes
    print("Calculating displacement magnitudes...")
    magnitudes = np.linalg.norm(displacements, axis=2)  # (N_frames, 400)

    # Determine normalization range
    if use_global_norm:
        global_max = magnitudes.max()
        global_min = magnitudes.min()
        print(f"  Global range: {global_min:.6f} to {global_max:.6f} mm")
        norm_info = f"global_max_{global_max:.6f}"
    else:
        norm_info = "per_frame"

    # Generate images
    print(f"\nGenerating {n_frames} images...")
    print(f"  Output directory: {output_dir}")
    print(f"  Image size: {width}x{height}")
    print(f"  Normalization: {'global' if use_global_norm else 'per-frame'}")

    # Save metadata in vt-compatible format
    metadata = {
        'sensor_id': npz_path.stem.replace('_data', ''),  # e.g., 'tac3d_1'
        'total_frames': n_frames,
        'dropped_frames': 0,
        'fps': None,  # Tac3D doesn't have fixed fps
        'image_format': 'jpg',
        'frames': []
    }

    for i in range(n_frames):
        # Get displacement magnitude for this frame
        disp_mag = magnitudes[i]  # (400,)

        # Reshape to 20x20 grid
        disp_grid = disp_mag.reshape(20, 20)

        # Normalize
        if use_global_norm:
            if global_max > 0:
                disp_norm = (disp_grid / global_max * 255).astype(np.uint8)
            else:
                disp_norm = np.zeros_like(disp_grid, dtype=np.uint8)
        else:
            # Per-frame normalization
            frame_max = disp_grid.max()
            if frame_max > 0:
                disp_norm = (disp_grid / frame_max * 255).astype(np.uint8)
            else:
                disp_norm = np.zeros_like(disp_grid, dtype=np.uint8)

        # Resize to target resolution
        disp_resized = cv2.resize(disp_norm, (width, height),
                                  interpolation=cv2.INTER_LINEAR)

        # Apply colormap
        colored_image = cv2.applyColorMap(disp_resized, colormap)

        # Save image
        filename = f"frame_{i:06d}.jpg"
        output_path = output_dir / filename
        cv2.imwrite(str(output_path), colored_image)

        # Add to metadata - vt-compatible format
        metadata['frames'].append({
            'frame_num': i,
            'filename': filename,
            'timestamp': float(capture_timestamps[i]),
            'frame_seq_num': -1  # Not applicable for Tac3D
        })

        # Progress
        if (i + 1) % 50 == 0 or i == n_frames - 1:
            progress = (i + 1) / n_frames * 100
            print(f"\r  Progress: {i+1}/{n_frames} ({progress:.1f}%)",
                  end='', flush=True)

    print()  # New line after progress

    # Save metadata
    metadata_path = output_dir / "frames_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✓ Images saved to: {output_dir}")
    print(f"✓ Metadata saved to: {metadata_path}")

    return output_dir


def main():
    parser = argparse.ArgumentParser(
        description='Convert Tac3D NPZ data to image sequence',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert NPZ to images (global normalization)
  python convert_tac3d_to_images.py data/session_xxx/tac3d_1/tac3d_1_data.npz

  # Specify output directory
  python convert_tac3d_to_images.py data.npz --output ./images

  # Use per-frame normalization
  python convert_tac3d_to_images.py data.npz --per-frame

  # Custom resolution
  python convert_tac3d_to_images.py data.npz --width 800 --height 800
        """
    )

    parser.add_argument('npz_file', type=str,
                       help='Path to Tac3D NPZ file')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='Output directory (default: same as NPZ file)')
    parser.add_argument('--width', type=int, default=400,
                       help='Image width (default: 400)')
    parser.add_argument('--height', type=int, default=400,
                       help='Image height (default: 400)')
    parser.add_argument('--per-frame', action='store_true',
                       help='Use per-frame normalization instead of global')

    args = parser.parse_args()

    try:
        output_dir = npz_to_images(
            npz_path=args.npz_file,
            output_dir=args.output,
            width=args.width,
            height=args.height,
            use_global_norm=not args.per_frame
        )

        print("\n✓ Conversion complete!")
        print(f"\nImages location: {output_dir}")
        print("\nNext steps:")
        print("  1. View images: ls", str(output_dir))
        print("  2. Visualize with rerun: python visualize_session_with_tac3d.py <session_dir>")

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
