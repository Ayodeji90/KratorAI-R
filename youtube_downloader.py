#!/usr/bin/env python3
"""
YouTube Video/Playlist Downloader
Downloads YouTube videos or entire playlists to the current working directory.

Requirements:
    pip install yt-dlp

Usage:
    python youtube_downloader.py <youtube_url>
    
Examples:
    python youtube_downloader.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    python youtube_downloader.py "https://www.youtube.com/playlist?list=PLxxxxxx"
"""

import sys
import os
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    print("Error: yt-dlp is not installed.")
    print("Please install it using: pip install yt-dlp")
    sys.exit(1)


def get_download_options(output_dir: str) -> dict:
    """Configure download options for yt-dlp."""
    return {
        # Output template - saves to current working directory
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        
        # Download best quality video + audio and merge
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        
        # Merge output format
        'merge_output_format': 'mp4',
        
        # Progress hooks for feedback
        'progress_hooks': [progress_hook],
        
        # Embed metadata
        'writethumbnail': False,
        'writesubtitles': False,
        
        # Playlist options
        'ignoreerrors': True,  # Continue on download errors
        'no_warnings': False,
        
        # Verbose output
        'verbose': False,
        'quiet': False,
        
        # Rate limiting (optional - uncomment if needed)
        # 'ratelimit': 5000000,  # 5MB/s
    }


def progress_hook(d: dict) -> None:
    """Display download progress."""
    if d['status'] == 'downloading':
        filename = d.get('filename', 'Unknown')
        percent = d.get('_percent_str', 'N/A')
        speed = d.get('_speed_str', 'N/A')
        eta = d.get('_eta_str', 'N/A')
        print(f"\r⬇️  Downloading: {percent} | Speed: {speed} | ETA: {eta}", end='', flush=True)
    elif d['status'] == 'finished':
        print(f"\n✅ Download complete: {d.get('filename', 'Unknown')}")
    elif d['status'] == 'error':
        print(f"\n❌ Error downloading: {d.get('filename', 'Unknown')}")


def download_youtube(url: str, output_dir: str = None) -> bool:
    """
    Download a YouTube video or playlist.
    
    Args:
        url: YouTube video URL or playlist URL
        output_dir: Directory to save downloads (defaults to current working directory)
    
    Returns:
        bool: True if download was successful, False otherwise
    """
    if output_dir is None:
        output_dir = os.getcwd()
    
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Download directory: {output_dir}")
    print(f"🔗 URL: {url}")
    print("-" * 50)
    
    # Get download options
    ydl_opts = get_download_options(output_dir)
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info first to determine if it's a playlist
            info = ydl.extract_info(url, download=False)
            
            if info is None:
                print("❌ Could not extract video information. Please check the URL.")
                return False
            
            # Check if it's a playlist
            if 'entries' in info:
                playlist_title = info.get('title', 'Unknown Playlist')
                video_count = len(list(info['entries']))
                print(f"📋 Playlist detected: {playlist_title}")
                print(f"📊 Total videos: {video_count}")
                print("-" * 50)
            else:
                video_title = info.get('title', 'Unknown Title')
                duration = info.get('duration_string', 'Unknown')
                print(f"🎬 Video: {video_title}")
                print(f"⏱️  Duration: {duration}")
                print("-" * 50)
            
            # Download the video(s)
            ydl.download([url])
            
        print("\n" + "=" * 50)
        print("🎉 All downloads completed successfully!")
        return True
        
    except yt_dlp.utils.DownloadError as e:
        print(f"\n❌ Download error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


def main():
    """Main entry point."""
    # Check command line arguments
    if len(sys.argv) < 2:
        print("YouTube Video/Playlist Downloader")
        print("=" * 40)
        print("\nUsage: python youtube_downloader.py <youtube_url>")
        print("\nExamples:")
        print('  python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"')
        print('  python youtube_downloader.py "https://www.youtube.com/playlist?list=PLAYLIST_ID"')
        print('  python youtube_downloader.py "https://youtu.be/VIDEO_ID"')
        sys.exit(1)
    
    url = sys.argv[1]
    
    # Validate URL (basic check)
    if not any(domain in url.lower() for domain in ['youtube.com', 'youtu.be']):
        print("⚠️  Warning: URL doesn't appear to be a YouTube link.")
        print("Attempting download anyway...")
    
    # Download
    success = download_youtube(url)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
