# Simple Media Tools

<p align="center">
  </p>

This is a multi-functional command-line Python script that provides a suite of tools for downloading from YouTube, converting video formats, and managing MP3 audio files.

## 🚀 Features

* **YouTube Downloader:**
    * Download videos and audio from YouTube in various qualities.
    * Quality selection available (Best, 1080p, 720p, 480p, 360p, Audio-only).
    * Saves downloaded files to the `YouTubeDownloads` folder.
* **Video to MP3 Converter:**
    * Convert video files (common formats) to MP3 format.
    * Reads videos from the `VideosToConvert` folder.
    * Saves output MP3 files to the `ConvertedMP3s` folder.
    * Requires `ffmpeg` to be installed.
* **MP3 Tools:**
    * **Tag Remover:** Removes ID3 and MP4 tags from audio files (`.mp3`, `.m4a`, `.mp4`) located in the `Audio_For_Tag_Removal` folder.
    * **Rename from Tag:** Renames audio files (`.mp3`, `.m4a`) based on their Artist and Title tags. Files should be placed in the `Audio_For_Renaming` folder.
* **Command Line Interface (CLI):**
    * Interactive and user-friendly menu for selecting tools.
    * Colored output for better readability (using the `colorama` library).
* **Organized Folder Structure:**
    * Automatically creates necessary folders for inputs and outputs for each module.
* **ASCII Art Title:**
    * Displays an "Simple Media Tools" ASCII art title above the main menu.

## 🛠 Prerequisites

1.  **Python:** Version 3.7 or higher is recommended.
2.  **pip:** For installing Python libraries.
3.  **FFmpeg:**
    * **Very Important:** For the YouTube Downloader (format conversion part) and the Video to MP3 Converter tool to function correctly, `ffmpeg` must be installed on your system and its path added to your system's `PATH` environment variable.
    * You can download `ffmpeg` from the [official FFmpeg website](https://ffmpeg.org/download.html).
4.  **Python Libraries:** This script requires the following Python libraries:
    * `yt-dlp`
    * `colorama`
    * `mutagen`

## ⚙️ Installation and Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/payam-shg/Simple-Media-Tools.git
    cd Simple-Media-Tools
    ```

2.  **Install required Python libraries:**

    run the following command to install them:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Ensure FFmpeg is installed:** Follow the installation steps for `ffmpeg` (mentioned in the Prerequisites section).

## ▶️ How to Use

1.  Run the main script:
    ```bash
    python app.py
    ```
2.  The main menu will be displayed. Enter the number corresponding to the tool you want to use and press Enter.
3.  Follow the instructions for each section. Place your input files in the designated folders as indicated by the script.

## 📁 Folder Structure

The script will automatically create the following folders next to the executable file (if they don't already exist):

* `YouTubeDownloads/`: Files downloaded from YouTube are saved here.
* `VideosToConvert/`: Place video files you want to convert to MP3 in this folder.
* `ConvertedMP3s/`: Converted MP3 files are saved in this folder.
* `Audio_For_Tag_Removal/`: Place audio files (mp3, m4a, mp4) from which you want to remove tags in this folder.
* `Audio_For_Renaming/`: Place audio files (mp3, m4a) that you want to rename based on their tags in this folder.
