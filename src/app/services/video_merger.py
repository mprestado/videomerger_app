"""
Video Merger Service - Handles video merging using FFmpeg
"""

import os
import subprocess
import tempfile
from typing import Callable, Optional, List
import re


class VideoMerger:
    """Handles merging multiple video files using FFmpeg"""
    
    def __init__(self):
        self.ffmpeg_path = "ffmpeg"  # Assumes ffmpeg is in PATH
        self.on_progress = None  # Callback for progress updates
        self.on_error = None  # Callback for error handling
        self.on_complete = None  # Callback for completion
        
    def set_progress_callback(self, callback: Callable[[str, float], None]):
        """
        Set callback for progress updates
        Args:
            callback: Function that receives (status_message, progress_percentage)
        """
        self.on_progress = callback
        
    def set_error_callback(self, callback: Callable[[str], None]):
        """
        Set callback for error handling
        Args:
            callback: Function that receives error message
        """
        self.on_error = callback
        
    def set_complete_callback(self, callback: Callable[[str], None]):
        """
        Set callback for completion
        Args:
            callback: Function that receives output file path
        """
        self.on_complete = callback
    
    def _report_progress(self, message: str, percentage: float = 0):
        """Internal method to report progress"""
        if self.on_progress:
            self.on_progress(message, percentage)
    
    def _report_error(self, message: str):
        """Internal method to report errors"""
        if self.on_error:
            self.on_error(message)
    
    def _report_complete(self, output_path: str):
        """Internal method to report completion"""
        if self.on_complete:
            self.on_complete(output_path)
    
    def merge_videos(
        self,
        video_paths: List[str],
        output_path: str,
        codec: str = "H.264",
        bitrate: str = "5000k",
    ) -> bool:
        """
        Merge multiple videos into a single output file
        
        Args:
            video_paths: List of input video file paths
            output_path: Output file path
            codec: Video codec to use (default: H.264)
            bitrate: Output bitrate (default: 5000k)
            
        Returns:
            True if successful, False otherwise
        """
        
        if not video_paths:
            self._report_error("No video files provided")
            return False
        
        if len(video_paths) == 1:
            self._report_error("At least 2 videos are required for merging")
            return False
        
        try:
            # Create a temporary concat demuxer file
            self._report_progress("Preparing videos for merge...", 5)

            concat_file = self._create_concat_file(video_paths)
            if not concat_file:
                self._report_error("Failed to create concat file")
                return False

            # determine total duration (seconds) to compute progress
            total_duration = self._get_total_duration(video_paths)
            if total_duration <= 0:
                # fallback to coarse progress
                total_duration = None

            try:
                self._report_progress("Starting merge process...", 10)

                # Build FFmpeg command
                cmd = self._build_ffmpeg_command(
                    concat_file,
                    output_path,
                    codec,
                    bitrate
                )

                # Run ffmpeg and parse stderr for progress (time=...)
                self._report_progress("Merging videos (running FFmpeg)...", 20)

                # Use Popen so we can stream stderr and compute progress
                # Convert cmd to proper list if it's a string
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                )

                time_re = re.compile(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})")

                last_report = 20.0
                # Read stderr line-by-line
                assert proc.stderr is not None
                for line in proc.stderr:
                    # Try to find time= in the ffmpeg progress output
                    m = time_re.search(line)
                    if m and total_duration:
                        t_str = m.group(1)
                        h, mm, ss = t_str.split(":")
                        seconds = int(h) * 3600 + int(mm) * 60 + float(ss)
                        percent = min(100.0, (seconds / total_duration) * 100.0)
                        # Only report when percent increased by >=1 or every few seconds
                        if percent - last_report >= 1.0 or percent >= 99.0:
                            last_report = percent
                            self._report_progress("Merging...", percent)
                    else:
                        # if no duration available, emit simple heartbeat
                        self._report_progress("Merging (in progress)...", last_report + 0.1)

                ret = proc.wait()
                if ret != 0:
                    # capture final stderr
                    stderr = proc.stderr.read() if proc.stderr is not None else ""
                    self._report_error(f"FFmpeg exited with code {ret}: {stderr}")
                    return False

                self._report_progress("Finalizing...", 99)
                self._report_progress("Merge complete!", 100)
                self._report_complete(output_path)
                return True

            finally:
                # Clean up concat file
                if os.path.exists(concat_file):
                    os.remove(concat_file)

        except Exception as e:
            self._report_error(f"Exception during merge: {str(e)}")
            return False

    def _get_total_duration(self, video_paths: List[str]) -> float:
        """Return sum of durations (in seconds) for input files using ffprobe"""
        total = 0.0
        for p in video_paths:
            try:
                # ffprobe command to get duration
                cmd = [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    p,
                ]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0:
                    s = res.stdout.strip()
                    try:
                        d = float(s)
                        if d > 0:
                            total += d
                    except Exception:
                        continue
            except Exception:
                continue
        return total
    
    def _create_concat_file(self, video_paths: List[str]) -> Optional[str]:
        """
        Create a temporary FFmpeg concat demuxer file
        
        Args:
            video_paths: List of video file paths
            
        Returns:
            Path to concat file, or None if failed
        """
        try:
            # Create temp file
            temp_fd, temp_path = tempfile.mkstemp(suffix=".txt", prefix="ffmpeg_concat_")
            
            with os.fdopen(temp_fd, 'w') as f:
                for video_path in video_paths:
                    # Normalize path separators for FFmpeg
                    normalized_path = os.path.abspath(video_path).replace('\\', '/')
                    f.write(f"file '{normalized_path}'\n")
            
            return temp_path
        except Exception as e:
            self._report_error(f"Failed to create concat file: {str(e)}")
            return None
    
    def _build_ffmpeg_command(
        self,
        concat_file: str,
        output_path: str,
        codec: str,
        bitrate: str
    ) -> List[str]:
        """
        Build FFmpeg command for merging
        
        Args:
            concat_file: Path to concat demuxer file
            output_path: Output file path
            codec: Video codec
            bitrate: Output bitrate
            
        Returns:
            List of command arguments
        """
        
        # Map codec names to FFmpeg codec strings
        codec_map = {
            "H.264": "libx264",
            "H.265": "libx265",
            "VP8": "libvpx",
            "VP9": "libvpx-vp9",
            "MPEG-4": "mpeg4",
            "MPEG-2": "mpeg2video",
            "ProRes": "prores",
            "Theora": "libtheora",
            "AV1": "libaom-av1",
            "WMV": "wmv2",
        }
        
        ffmpeg_codec = codec_map.get(codec, "libx264")
        
        cmd = [
            self.ffmpeg_path,
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c:v", ffmpeg_codec,
            "-b:v", bitrate,
            "-c:a", "aac",
            "-b:a", "192k",
            "-y",  # Overwrite output file
            output_path,
        ]
        
        return cmd
