import os
import ssl
import json
import subprocess
import re
from pytube import YouTube
from pydub import AudioSegment
from pydub.utils import which

CONFIG_FILE = 'config.json'

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as file:
            return json.load(file)
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as file:
        json.dump(config, file, indent=4)

def progress_function(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage = (bytes_downloaded / total_size) * 100
    print(f'Download progress: {percentage:.2f}%')

def compress_video(input_path, output_path, compression_rate):
    if compression_rate == 0:
        print("Skipping compression as compression rate is 0%")
        return input_path
    
    crf_value = int((100 - compression_rate) * 51 / 100)
    command = [
        'ffmpeg',
        '-i', input_path,
        '-vcodec', 'libx264',
        '-crf', str(crf_value),
        output_path
    ]
    process = subprocess.Popen(command, stderr=subprocess.PIPE, text=True)

    total_duration = None
    time_pattern = re.compile(r'time=(\d{2}:\d{2}:\d{2}.\d{2})')
    duration_pattern = re.compile(r'Duration: (\d{2}:\d{2}:\d{2}.\d{2})')

    for line in process.stderr:
        if total_duration is None:
            duration_match = duration_pattern.search(line)
            if duration_match:
                total_duration = duration_match.group(1)
                print(f'Total Duration: {total_duration}')

        time_match = time_pattern.search(line)
        if time_match:
            current_time = time_match.group(1)
            if total_duration:
                total_seconds = get_seconds(total_duration)
                current_seconds = get_seconds(current_time)
                percentage = (current_seconds / total_seconds) * 100
                print(f'Compression progress: {percentage:.2f}%')

    process.wait()
    print(f"Video compressed successfully and saved to '{output_path}' with compression rate {compression_rate}% (CRF={crf_value})")
    return output_path

def get_seconds(time_str):
    h, m, s = map(float, time_str.split(':'))
    return int(h * 3600 + m * 60 + s)

def download_youtube_video(url, output_path='output', download_audio=False, compression_rate=0):
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    ssl._create_default_https_context = ssl._create_unverified_context

    try:
        yt = YouTube(url, on_progress_callback=progress_function)
        stream = None  # Initialize the stream variable
        
        if download_audio:
            stream = yt.streams.filter(only_audio=True).first()
            audio_file_path = stream.download(output_path=output_path)
            base, ext = os.path.splitext(audio_file_path)
            mp3_file_path = base + '.mp3'
            
            AudioSegment.converter = which("ffmpeg")
            AudioSegment.ffprobe = which("ffprobe")

            AudioSegment.from_file(audio_file_path).export(mp3_file_path, format='mp3')
            os.remove(audio_file_path)
            print(f"Audio '{yt.title}' has been downloaded and converted to mp3 successfully to '{mp3_file_path}'!")
        else:
            stream = yt.streams.get_highest_resolution()
            video_file_path = stream.download(output_path=output_path)
            if compression_rate > 0:
                base, ext = os.path.splitext(video_file_path)
                compressed_video_path = base + '_compressed.mp4'
                compressed_video_path = compress_video(video_file_path, compressed_video_path, compression_rate)
                os.remove(video_file_path)
                print(f"Video '{yt.title}' has been downloaded and compressed successfully to '{compressed_video_path}'!")
            else:
                print(f"Video '{yt.title}' has been downloaded successfully to '{video_file_path}'!")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    config = load_config()
    default_output_path = config.get('output_path', 'output')

    url = input("Enter the YouTube video URL: ")
    download_type = input("Do you want to download audio only? (yes/no, default is no): ").strip().lower()
    download_audio = (download_type == 'yes')
    
    output_path = input(f"Enter the output path (default is '{default_output_path}'): ") or default_output_path

    compression_rate = 0
    if not download_audio:
        compression_rate = input("Enter the compression rate as a percentage (0-100, default is 0 for no compression): ").strip()
        compression_rate = int(compression_rate) if compression_rate.isdigit() else 0
        compression_rate = max(0, min(100, compression_rate))

    config['output_path'] = output_path
    save_config(config)

    download_youtube_video(url, output_path, download_audio, compression_rate)
