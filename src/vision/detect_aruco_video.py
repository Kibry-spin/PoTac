"""Command-line tool to detect and annotate ArUco markers in a video."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from .aruco_detector import ArUcoDetector


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Detect ArUco markers in a video, annotate the frames, and save "
            "the result as a new video."
        )
    )
    parser.add_argument(
        "--video",
        required=True,
        type=Path,
        help="Path to the input video file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional path for the annotated output video",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Optional JSON configuration file for ArUco detector settings",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display annotated frames while processing (press 'q' to quit)",
    )
    parser.add_argument(
        "--log-every",
        type=int,
        default=30,
        help="Print detection info every N frames (default: 30)",
    )
    return parser.parse_args()


def infer_output_path(video_path: Path) -> Path:
    stem = video_path.stem
    suffix = video_path.suffix or ".mp4"
    return video_path.with_name(f"{stem}_annotated{suffix}")


def create_video_writer(
    output_path: Path,
    fps: float,
    frame_size: tuple[int, int],
) -> cv2.VideoWriter:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, frame_size)
    if not writer.isOpened():
        raise RuntimeError(f"Failed to open video writer for {output_path}")
    return writer


def main() -> None:
    args = parse_args()

    video_path: Path = args.video
    if not video_path.exists():
        raise FileNotFoundError(f"Input video not found: {video_path}")

    output_path: Path = args.output or infer_output_path(video_path)

    detector = ArUcoDetector(config_file=str(args.config) if args.config else None)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video source: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_size = (width, height)

    writer = create_video_writer(output_path, fps, frame_size)

    frame_index = 0
    print(f"Processing video: {video_path}")
    print(f"Annotated output will be saved to: {output_path}")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            annotated_frame, detection = detector.detect_markers(frame)
            writer.write(annotated_frame)

            if args.show:
                cv2.imshow("ArUco Detection", annotated_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    print("Processing interrupted by user request (q pressed).")
                    break

            if args.log_every > 0 and frame_index % args.log_every == 0:
                ids = detection.get("ids", []) if isinstance(detection, dict) else []
                print(
                    f"Frame {frame_index}: detected {len(ids)} marker(s)"
                    + (f" -> IDs: {ids}" if ids else "")
                )

            frame_index += 1

    except KeyboardInterrupt:
        print("Processing interrupted by user (Ctrl+C).")
    finally:
        cap.release()
        writer.release()
        if args.show:
            cv2.destroyAllWindows()

    print("Processing complete.")


if __name__ == "__main__":
    main()
