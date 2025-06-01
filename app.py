import os
import sys
import re
import traceback
import subprocess

try:
    import yt_dlp
    from colorama import init as colorama_init, Fore, Style
    colorama_init(autoreset=True)
except ImportError:
    print("Error: Required libraries 'yt_dlp' or 'colorama' are not installed.")
    print("Please install them using: pip install yt-dlp colorama")
    sys.exit(1)

try:
    import mutagen
    from mutagen.id3 import ID3, ID3NoHeaderError, TPE1, TIT2
    from mutagen.mp4 import MP4, MP4Cover
    MUTAGEN_AVAILABLE = True
except ImportError:
    print("Warning: Library 'mutagen' is not installed. 'MP3 Tools' will not be available.")
    print("Please install it using: pip install mutagen")
    MUTAGEN_AVAILABLE = False


# --- Global Configuration & Constants --- #
YOUTUBE_DOWNLOAD_SUBDIR_NAME = "YouTubeDownloads"

VIDEO_CONVERTER_INPUT_DIR_NAME = "VideosToConvert"
VIDEO_CONVERTER_OUTPUT_DIR_NAME = "ConvertedMP3s"
TAG_REMOVER_DIR_NAME = "Audio_For_Tag_Removal"
RENAMER_DIR_NAME = "Audio_For_Renaming"


# --- Configuration for MP3 Converter --- #
VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv',
    '.webm', '.mpeg', '.mpg', '.ts', '.vob', '.m4v',
    '.3gp'
}
AUDIO_BITRATE_CONVERTER = '192k'
OVERWRITE_EXISTING_CONVERTED_MP3 = False

# --- General Helper Functions --- #
def get_main_script_directory():
    """Gets the directory where the script is located."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        try:
            return os.path.dirname(os.path.abspath(__file__))
        except NameError:
            return os.path.abspath(".")

def ensure_directory_exists(dir_path):
    """Creates a directory if it doesn't exist."""
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path)
            print(f"{Fore.GREEN}Directory created: {dir_path}{Style.RESET_ALL}")
            return True
        except OSError as e:
            print(f"{Fore.RED}Error creating directory {dir_path}: {e}{Style.RESET_ALL}")
            return False
    return True

# --- YouTube Downloader Section (Largely Unchanged from previous combined version) --- #
def yt_dl_print_banner():
    banner = f"""
{Fore.CYAN}╭─────────────────────────────────────────────────────────────────╮
{Fore.LIGHTBLUE_EX}│   ██╗   ██╗ ██████╗ ██╗   ██╗████████╗██╗   ██╗██████╗ ███████╗ │
{Fore.LIGHTBLUE_EX}│   ╚██╗ ██╔╝██╔═══██╗██║   ██║╚══██╔══╝██║   ██║██╔══██╗██╔════╝ │
{Fore.LIGHTCYAN_EX}│    ╚████╔╝ ██║   ██║██║   ██║   ██║   ██║   ██║██████╔╝█████╗   │
{Fore.LIGHTCYAN_EX}│     ╚██╔╝  ██║   ██║██║   ██║   ██║   ██║   ██║██╔══██╗██╔══╝   │
{Fore.LIGHTBLUE_EX}│      ██║   ╚██████╔╝╚██████╔╝   ██║   ╚██████╔╝██████╔╝███████╗ │
{Fore.LIGHTBLUE_EX}│      ╚═╝    ╚═════╝  ╚═════╝    ╚═╝    ╚═════╝ ╚═════╝ ╚══════╝ │
{Fore.CYAN}├─────────────────────────────────────────────────────────────────┤
{Fore.LIGHTCYAN_EX}│         🚀  Y O U T U B E   D O W N L O A D E R  🚀             │
{Fore.CYAN}╰─────────────────────────────────────────────────────────────────╯
{Style.RESET_ALL}"""
    print(banner)

def yt_dl_sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def yt_dl_get_video_info(url):
    ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"\n{Fore.RED}🔥 Error getting video info: {str(e)}{Style.RESET_ALL}")
        return None

def yt_dl_remove_ansi_escape(text):
    if text is None: return ""
    return re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub('', text)

def yt_dl_progress_hook(d):
    if d['status'] == 'downloading':
        percent = yt_dl_remove_ansi_escape(d.get('_percent_str', 'N/A')).strip('% ')
        speed = d.get('_speed_str', 'N/A')
        eta = d.get('_eta_str', 'N/A')
        try: pct_num = float(percent)
        except ValueError: pct_num = 0.0
        spinner = ['⣾','⣽','⣻','⢿','⡿','⣟','⣯','⣷'][int(d.get('elapsed', 0)*10)%8]
        color = Fore.LIGHTRED_EX if pct_num < 30 else Fore.LIGHTYELLOW_EX if pct_num < 70 else Fore.LIGHTGREEN_EX
        print(f"\r{color}{spinner} {Fore.YELLOW}Progress: {color}{percent:>6}% {Fore.LIGHTMAGENTA_EX}∥ {Fore.LIGHTGREEN_EX}Speed: {Fore.CYAN}{speed:>12} {Fore.LIGHTMAGENTA_EX}∥ {Fore.LIGHTBLUE_EX}ETA: {Fore.LIGHTCYAN_EX}{eta:>8}{Style.RESET_ALL}", end='', flush=True)
    elif d['status'] == 'finished':
        print(f"\r{Fore.GREEN}⏳ Finalizing download... please wait{Style.RESET_ALL}                 ", end='', flush=True)

def yt_dl_download_video(url, quality_format, download_dir_path):
    try:
        video_info = yt_dl_get_video_info(url)
        if not video_info:
            print(f"{Fore.RED}❌ Could not get video information{Style.RESET_ALL}")
            return False
        title = yt_dl_sanitize_filename(video_info['title'])
        ensure_directory_exists(download_dir_path)
        output_template = os.path.join(download_dir_path, f"{title}.%(ext)s")
        ydl_opts = {
            'format': quality_format, 'outtmpl': output_template,
            'progress_hooks': [yt_dl_progress_hook], 'nocheckcertificate': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192',
            }] if quality_format == 'bestaudio/best' else [{
                'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4', 'when': 'post_process'
            }]
        }
        print(f"\n{Fore.GREEN}📡 Downloading: {Fore.YELLOW}{title}{Style.RESET_ALL}")
        print(f"{Fore.BLUE}⌛ Preparing download...{Style.RESET_ALL}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"\r{Fore.GREEN}🎉 ✓ Download completed successfully!{Style.RESET_ALL}              ")
        print(f"{Fore.CYAN}📂 File saved to: {Fore.YELLOW}{download_dir_path}{Style.RESET_ALL}")
        return True
    except yt_dlp.utils.DownloadError as e:
        print(f"\n{Fore.RED}💥 yt-dlp Download Error: {str(e)}{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"\n{Fore.RED}⚡ Unexpected Error during download: {str(e)}{Style.RESET_ALL}")
        traceback.print_exc()
        return False

def yt_dl_print_quality_menu():
    print(f"\n{Fore.WHITE}╔════════════════════════════════════════╗")
    print(f"║{Fore.MAGENTA}       📽  VIDEO QUALITY OPTIONS         {Fore.WHITE}║")
    print(f"╠════════════════════════════════════════╣")
    print(f"║{Fore.WHITE} 1. {Fore.GREEN}🎯 Best quality (4K if available)   {Fore.WHITE}║")
    print(f"║{Fore.WHITE} 2. {Fore.YELLOW}🖥  1080p HD                         {Fore.WHITE}║")
    print(f"║{Fore.WHITE} 3. {Fore.YELLOW}💻 720p HD                          {Fore.WHITE}║")
    print(f"║{Fore.WHITE} 4. {Fore.YELLOW}📱 480p                             {Fore.WHITE}║")
    print(f"║{Fore.WHITE} 5. {Fore.YELLOW}📼 360p                             {Fore.WHITE}║")
    print(f"║{Fore.WHITE} 6. {Fore.CYAN}🎧 Audio only (High quality MP3)    {Fore.WHITE}║")
    print(f"║{Fore.WHITE} 0. {Fore.RED}🚪 Return to Main Menu              {Fore.WHITE}║")
    print(f"╚════════════════════════════════════════╝{Style.RESET_ALL}")

def yt_dl_get_quality_format(choice):
    q_map = {'1': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
             '2': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]',
             '3': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]',
             '4': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]',
             '5': 'bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best[height<=360]',
             '6': 'bestaudio/best'}
    return q_map.get(choice, q_map['1'])

def yt_dl_extract_youtube_url(text):
    match = re.search(r'(?:https?://)?(?:www\.)?(?:m\.)?(?:youtube\.com|youtu\.be)/(?:watch\?v=|embed/|v/|shorts/)?([a-zA-Z0-9_-]{11})', text)
    if match and match.group(1): return f"https://www.youtube.com/watch?v={match.group(1)}"
    return None

def run_youtube_downloader():
    main_script_dir = get_main_script_directory()
    yt_download_path = os.path.join(main_script_dir, YOUTUBE_DOWNLOAD_SUBDIR_NAME)
    yt_dl_print_banner()
    if not ensure_directory_exists(yt_download_path): return

    while True:
        yt_dl_print_quality_menu()
        choice = input(f"\n{Fore.MAGENTA}✨ Enter quality choice [0-6]: {Style.RESET_ALL}").strip()
        if choice == '0': break
        if choice not in ['1','2','3','4','5','6']:
            print(f"{Fore.YELLOW}⚠ Invalid choice. Using default (best).{Style.RESET_ALL}"); choice = '1'
        
        quality_format = yt_dl_get_quality_format(choice)
        url_input = input(f"\n{Fore.CYAN}🌐 Enter YouTube URL or video ID: {Style.RESET_ALL}").strip()
        url = yt_dl_extract_youtube_url(url_input)
        if not url:
             if re.match(r'^[a-zA-Z0-9_-]{11}$', url_input):
                 url = f"https://www.youtube.com/watch?v={url_input}"
        
        if url:
            print(f"{Fore.GREEN}🔗 Using URL: {Fore.CYAN}{url}{Style.RESET_ALL}")
            q_desc = {'1':'Best','2':'1080p','3':'720p','4':'480p','5':'360p','6':'Audio MP3'}.get(choice)
            print(f"\n{Fore.GREEN}⚡ Selected quality: {Fore.CYAN}{q_desc}{Style.RESET_ALL}")
            yt_dl_download_video(url, quality_format, yt_download_path)
        else:
            print(f"\n{Fore.RED}⚠ Invalid YouTube URL or video ID.{Style.RESET_ALL}")
            continue
        
        if input(f"\n{Fore.MAGENTA}🔄 Download another? (y/n): {Style.RESET_ALL}").lower().strip() != 'y': break
    print(f"\n{Fore.MAGENTA}✨ Returning to main menu. Downloads in: {Fore.YELLOW}{yt_download_path}{Style.RESET_ALL}\n")

# --- Video to MP3 Converter Section --- #
def converter_convert_videos_to_mp3(input_directory, output_directory):
    print(f"\n{Fore.CYAN}--- Initializing MP3 Conversion ---{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Input Directory: {Style.BRIGHT}{input_directory}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Output Directory: {Style.BRIGHT}{output_directory}{Style.RESET_ALL}")
    found_videos, converted_count, skipped_count, error_count = 0, 0, 0, 0

    try:
        subprocess.run(['ffmpeg', '-version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"{Fore.GREEN}ffmpeg found.{Style.RESET_ALL}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"\n{Fore.RED}Error: ffmpeg not found. Please install ffmpeg and ensure it's in PATH.{Style.RESET_ALL}")
        return

    for filename in os.listdir(input_directory):
        input_filepath = os.path.join(input_directory, filename)
        if os.path.isfile(input_filepath) and os.path.splitext(filename)[1].lower() in VIDEO_EXTENSIONS:
            found_videos += 1
            base_name = os.path.splitext(filename)[0]
            output_filename = f"{base_name}.mp3"
            output_filepath = os.path.join(output_directory, output_filename)
            print(f"\n{Fore.CYAN}Found video: {Style.BRIGHT}{filename}{Style.RESET_ALL}")

            if not OVERWRITE_EXISTING_CONVERTED_MP3 and os.path.exists(output_filepath):
                print(f"{Fore.YELLOW}Skipping: Output '{output_filename}' already exists.{Style.RESET_ALL}")
                skipped_count += 1; continue

            command = ['ffmpeg', '-i', input_filepath, '-vn', '-acodec', 'libmp3lame', '-ab', AUDIO_BITRATE_CONVERTER]
            command.append('-y' if OVERWRITE_EXISTING_CONVERTED_MP3 else '-n')
            command.append(output_filepath)
            
            print(f"{Fore.LIGHTBLUE_EX}Converting to: {Style.BRIGHT}{output_filename}{Style.RESET_ALL}...")
            try:
                result = subprocess.run(command, check=True, capture_output=True, text=True)
                print(f"{Fore.GREEN}Successfully converted.{Style.RESET_ALL}")
                converted_count += 1
            except subprocess.CalledProcessError as e:
                print(f"{Fore.RED}Error converting '{filename}': {e.stderr}{Style.RESET_ALL}"); error_count += 1
            except Exception as e:
                print(f"{Fore.RED}Unexpected error for '{filename}': {e}{Style.RESET_ALL}"); error_count += 1
    
    print(f"\n{Fore.CYAN}--- Conversion Summary ---{Style.RESET_ALL}")
    print(f"Found: {found_videos}, Converted: {converted_count}, Skipped: {skipped_count}, Errors: {error_count}")

def run_video_to_mp3_converter():
    main_dir = get_main_script_directory()
    input_dir = os.path.join(main_dir, VIDEO_CONVERTER_INPUT_DIR_NAME)
    output_dir = os.path.join(main_dir, VIDEO_CONVERTER_OUTPUT_DIR_NAME)

    print(f"\n{Fore.MAGENTA}--- Video to MP3 Converter ---{Style.RESET_ALL}")
    if not ensure_directory_exists(input_dir) or not ensure_directory_exists(output_dir):
        print(f"{Fore.RED}Could not create necessary directories. Aborting.{Style.RESET_ALL}"); return
    
    print(f"{Fore.YELLOW}This tool converts videos from '{VIDEO_CONVERTER_INPUT_DIR_NAME}' to MP3s in '{VIDEO_CONVERTER_OUTPUT_DIR_NAME}'.{Style.RESET_ALL}")
    if input(f"{Fore.CYAN}Proceed? (y/n): {Style.RESET_ALL}").strip().lower() == 'y':
        converter_convert_videos_to_mp3(input_dir, output_dir)
    else:
        print(f"{Fore.YELLOW}Conversion cancelled.{Style.RESET_ALL}")
    print(f"\n{Fore.MAGENTA}--- Returning to main menu ---{Style.RESET_ALL}")

# --- MP3 Tools: Tag Remover --- #
def tag_remover_remove_id3_tags(file_path):
    try:
        audio = ID3(file_path)
        audio.delete()
        audio.save()
        print(f"{Fore.GREEN}ID3 tags removed from: {os.path.basename(file_path)}{Style.RESET_ALL}")
        return True
    except ID3NoHeaderError:
        print(f"{Fore.YELLOW}No ID3 tags found in: {os.path.basename(file_path)}{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"{Fore.RED}Error removing ID3 tags from {os.path.basename(file_path)}: {e}{Style.RESET_ALL}")
        return False

def tag_remover_remove_mp4_tags(file_path):
    try:
        audio = MP4(file_path)
        if audio.tags:
            audio.delete()
            audio.save()
            print(f"{Fore.GREEN}MP4 tags removed from: {os.path.basename(file_path)}{Style.RESET_ALL}")
            return True
        else:
            print(f"{Fore.YELLOW}No MP4 tags found in: {os.path.basename(file_path)}{Style.RESET_ALL}")
            return False
    except Exception as e:
        print(f"{Fore.RED}Error removing MP4 tags from {os.path.basename(file_path)}: {e}{Style.RESET_ALL}")
        return False

def tag_remover_process_directory(directory_path):
    print(f"\n{Fore.CYAN}Processing directory: {directory_path}{Style.RESET_ALL}")
    processed_files = 0
    audio_files = [os.path.join(root, file) for root, _, files in os.walk(directory_path) 
                   for file in files if file.lower().endswith(('.mp3', '.m4a', '.mp4'))]

    if not audio_files:
        print(f"{Fore.YELLOW}No compatible audio files found.{Style.RESET_ALL}"); return

    print(f"\n{Fore.CYAN}Step 1: Removing ID3 tags...{Style.RESET_ALL}")
    for fp in audio_files:
        if fp.lower().endswith('.mp3'):
             tag_remover_remove_id3_tags(fp)
    
    print(f"\n{Fore.CYAN}Step 2: Removing MP4 (iTunes-style) tags...{Style.RESET_ALL}")
    for fp in audio_files:
        if fp.lower().endswith(('.m4a', '.mp4')):
            tag_remover_remove_mp4_tags(fp)
        processed_files+=1
    
    print(f"\n{Fore.GREEN}{len(audio_files)} audio file(s) scanned. Tag removal attempted.{Style.RESET_ALL}")

def run_tag_remover():
    main_dir = get_main_script_directory()
    target_dir = os.path.join(main_dir, TAG_REMOVER_DIR_NAME)
    print(f"\n{Fore.MAGENTA}--- MP3 Tag Remover ---{Style.RESET_ALL}")
    if not ensure_directory_exists(target_dir):
        print(f"{Fore.RED}Could not create directory '{TAG_REMOVER_DIR_NAME}'. Aborting.{Style.RESET_ALL}"); return
    print(f"{Fore.YELLOW}This tool will remove ID3/MP4 tags from audio files in '{TAG_REMOVER_DIR_NAME}'.{Style.RESET_ALL}")
    if input(f"{Fore.CYAN}Proceed? (y/n): {Style.RESET_ALL}").strip().lower() == 'y':
        tag_remover_process_directory(target_dir)
    else:
        print(f"{Fore.YELLOW}Tag removal cancelled.{Style.RESET_ALL}")

# --- MP3 Tools: Renamer from Tag --- #
def renamer_sanitize_filename(name):
    if not isinstance(name, str): return "Unknown"
    name = re.sub(r'[\\/*?:"<>|\x00-\x1F]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    while name.endswith('.') or name.endswith(' '): name = name[:-1]
    return name[:150].strip() or "Unknown"

def renamer_process_audio_files(folder_path):
    print(f"\n{Fore.CYAN}--- Starting Audio File Renaming ---{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Processing files in: {folder_path}{Style.RESET_ALL}")
    renamed_m4a, renamed_mp3, skipped_m4a, skipped_mp3, errors = 0,0,0,0,0

    for filename in os.listdir(folder_path):
        original_full_path = os.path.join(folder_path, filename)
        if not os.path.isfile(original_full_path): continue

        base_name, extension = os.path.splitext(filename)
        ext_lower = extension.lower()
        
        artist, title = None, None
        sanitized_artist, sanitized_title = "Unknown", "Unknown"

        print(f"\n{Fore.CYAN}Processing: '{filename}'{Style.RESET_ALL}")
        try:
            audio = mutagen.File(original_full_path, easy=True)
            if not audio:
                print(f" {Fore.YELLOW}Skipped: Mutagen could not parse file.{Style.RESET_ALL}")
                if ext_lower == '.m4a': skipped_m4a+=1
                elif ext_lower == '.mp3': skipped_mp3+=1
                continue
            
            artist_list = audio.get('artist')
            title_list = audio.get('title')
            if artist_list: artist = " / ".join(artist_list).strip()
            if title_list: title = title_list[0].strip()

            if not artist or not title:
                missing = [t for t,v in [('artist',artist),('title',title)] if not v]
                print(f" {Fore.YELLOW}Skipped: Missing tag(s): {', '.join(missing)}.{Style.RESET_ALL}")
                if ext_lower == '.m4a': skipped_m4a+=1
                elif ext_lower == '.mp3': skipped_mp3+=1
                continue

            sanitized_artist = renamer_sanitize_filename(artist)
            sanitized_title = renamer_sanitize_filename(title)
            print(f" {Fore.GREEN}Tags: Artist='{sanitized_artist}', Title='{sanitized_title}'{Style.RESET_ALL}")

        except Exception as e:
            print(f" {Fore.RED}Skipped: Error reading metadata: {e}{Style.RESET_ALL}")
            if ext_lower == '.m4a': skipped_m4a+=1; errors+=1
            elif ext_lower == '.mp3': skipped_mp3+=1; errors+=1
            continue

        new_base_name = f"{sanitized_artist} - {sanitized_title}"
        new_filename = f"{new_base_name}{extension}"
        new_full_path = os.path.join(folder_path, new_filename)

        if original_full_path == new_full_path:
            print(f" {Fore.YELLOW}Skipped: Filename already correct.{Style.RESET_ALL}")
            if ext_lower == '.m4a': skipped_m4a+=1
            elif ext_lower == '.mp3': skipped_mp3+=1
            continue
        
        if os.path.exists(new_full_path):
            print(f" {Fore.YELLOW}Skipped: Target '{new_filename}' already exists.{Style.RESET_ALL}")
            if ext_lower == '.m4a': skipped_m4a+=1
            elif ext_lower == '.mp3': skipped_mp3+=1
            continue
        try:
            os.rename(original_full_path, new_full_path)
            print(f" {Fore.GREEN}Renamed to: '{new_filename}'{Style.RESET_ALL}")
            if ext_lower == '.m4a': renamed_m4a+=1
            elif ext_lower == '.mp3': renamed_mp3+=1
        except OSError as e:
            print(f" {Fore.RED}Error renaming: {e}{Style.RESET_ALL}")
            errors+=1
            if ext_lower == '.m4a': skipped_m4a+=1
            elif ext_lower == '.mp3': skipped_mp3+=1
            
    print(f"\n{Fore.CYAN}--- Renaming Summary ---{Style.RESET_ALL}")
    print(f"M4A Renamed: {renamed_m4a}, MP3 Renamed: {renamed_mp3}")
    print(f"M4A Skipped: {skipped_m4a}, MP3 Skipped: {skipped_mp3}, Errors: {errors}")


def run_renamer_from_tag():
    main_dir = get_main_script_directory()
    target_dir = os.path.join(main_dir, RENAMER_DIR_NAME)
    print(f"\n{Fore.MAGENTA}--- MP3/M4A Renamer from Tags ---{Style.RESET_ALL}")
    if not ensure_directory_exists(target_dir):
        print(f"{Fore.RED}Could not create directory '{RENAMER_DIR_NAME}'. Aborting.{Style.RESET_ALL}"); return
    print(f"{Fore.YELLOW}This tool renames MP3/M4A files in '{RENAMER_DIR_NAME}' based on their Artist/Title tags.{Style.RESET_ALL}")
    if input(f"{Fore.CYAN}Proceed? (y/n): {Style.RESET_ALL}").strip().lower() == 'y':
        renamer_process_audio_files(target_dir)
    else:
        print(f"{Fore.YELLOW}Renaming cancelled.{Style.RESET_ALL}")

# --- MP3 Tools Submenu --- #
def display_mp3_tools_menu():
    print(f"\n{Fore.WHITE}╔════════════════════════════════════════╗")
    print(f"║ {Fore.YELLOW}{Style.BRIGHT}        🛠️ MP3 Tools 🛠️                {Style.RESET_ALL}{Fore.WHITE}║")
    print(f"╠════════════════════════════════════════╣")
    print(f"║ {Fore.CYAN}1. Remove Tags from Audio Files        {Style.RESET_ALL}{Fore.WHITE}║")
    print(f"║ {Fore.CYAN}2. Rename Audio from Tags              {Style.RESET_ALL}{Fore.WHITE}║")
    print(f"╠════════════════════════════════════════╣")
    print(f"║ {Fore.RED}0. Return to Main Menu                 {Style.RESET_ALL}{Fore.WHITE}║")
    print(f"╚════════════════════════════════════════╝{Style.RESET_ALL}")

def run_mp3_tools_submenu():
    if not MUTAGEN_AVAILABLE:
        print(f"\n{Fore.RED}MP3 Tools require the 'mutagen' library. Please install it.{Style.RESET_ALL}")
        return
        
    while True:
        display_mp3_tools_menu()
        choice = input(f"\n{Fore.YELLOW}{Style.BRIGHT}✨ Enter MP3 Tool choice [0-2]: {Style.RESET_ALL}").strip()
        if choice == '1': run_tag_remover()
        elif choice == '2': run_renamer_from_tag()
        elif choice == '0': break
        else: print(f"\n{Fore.RED}❌ Invalid choice.{Style.RESET_ALL}")
        input(f"\n{Fore.CYAN}Press Enter to return to MP3 Tools menu...{Style.RESET_ALL}")
        os.system('cls' if os.name == 'nt' else 'clear')

# --- Main Application Menu and Execution --- #
def display_main_application_menu():
    print(f"\n{Fore.WHITE}╔════════════════════════════════════════╗")
    print(f"║ {Fore.YELLOW}{Style.BRIGHT}        🚀 MAIN MEDIA TOOL 🚀          {Style.RESET_ALL}{Fore.WHITE}║")
    print(f"╠════════════════════════════════════════╣")
    print(f"║ {Fore.LIGHTGREEN_EX}1. YouTube Video Downloader            {Style.RESET_ALL}{Fore.WHITE}║")
    print(f"║ {Fore.LIGHTBLUE_EX}2. Convert Video to MP3                {Style.RESET_ALL}{Fore.WHITE}║")
    print(f"║ {Fore.GREEN}3. MP3 Tools                           {Style.RESET_ALL}{Fore.WHITE}║")
    print(f"╠════════════════════════════════════════╣")
    print(f"║ {Fore.RED}0. Exit Application                    {Style.RESET_ALL}{Fore.WHITE}║")
    print(f"╚════════════════════════════════════════╝{Style.RESET_ALL}")

def main_combined_script():
    """Main function to run the combined application."""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_main_title()
        display_main_application_menu()
        
        choice = input(f"\n{Fore.MAGENTA}{Style.BRIGHT}✨ Enter your choice [0-3]: {Style.RESET_ALL}").strip()

        if choice == '1':
            run_youtube_downloader()
        elif choice == '2':
            run_video_to_mp3_converter()
        elif choice == '3':
            run_mp3_tools_submenu()
        elif choice == '0':
            print(f"\n{Fore.LIGHTMAGENTA_EX}👋 Exiting application. Goodbye!{Style.RESET_ALL}\n")
            break
        else:
            print(f"\n{Fore.RED}❌ Invalid choice. Please try again.{Style.RESET_ALL}")
        
        if choice != '0':
            input(f"\n{Fore.CYAN}Press Enter to return to the main menu...{Style.RESET_ALL}")

def print_main_title():
    """Prints the main application title using 6-line ASCII art blocks, left-aligned."""

    letters = {
        'S': [
            " ██████╗ ",
            "██╔════╝ ",
            "╚█████╗  ",
            " ╚═══██╗ ",
            "██████╔╝ ",
            "╚═════╝  "
        ],
        'I': [
            "███████╗",
            " ╚═██╔═╝",
            "   ██║  ",
            "   ██║  ",
            " ╔═██╚═╗",
            " ███████"
        ],
        'M': [
            "███╗   ███╗",
            "████╗ ████║",
            "██╔████╔██║",
            "██║╚██╔╝██║",
            "██║ ╚═╝ ██║",
            "╚═╝     ╚═╝"
        ],
        'P': [
            "██████╔╗ ",
            "██╔══██║ ",
            "██████╔╝ ",
            "██╔═══╝  ",
            "██║      ",
            "╚═╝      "
        ],
        'L': [
            "██╗      ",
            "██║      ",
            "██║      ",
            "██║      ",
            "███████╗ ",
            "╚══════╝ "
        ],
        'E': [
            "███████╗ ",
            "██╔════╝ ",
            "██████╗  ",
            "██╔════╝ ",
            "███████╗ ",
            "╚══════╝ "
        ],
        'D': [
            "██████╗  ",
            "██╔══██╗ ",
            "██║  ██║ ",
            "██║  ██║ ",
            "██████╔╝ ",
            "╚═════╝  "
        ],
        'A': [
            "  █████  ",
            " ██╔═╗██ ",
            "█████████",
            "██╔═══╗██",
            "██║   ║██",
            "╚═╝   ╚═╝"
        ],
        'T': [
            "████████╗",
            "╚══██╔══╝",
            "   ██║   ",
            "   ██║   ",
            "   ██║   ",
            "   ╚═╝   "
        ],
        'O': [
            " ██████╗ ",
            "██╔═══██╗",
            "██║   ██║",
            "██║   ██║",
            "╚██████╔╝",
            " ╚═════╝ "
        ]
    }

    words_config = [
        ("SIMPLE", [Fore.GREEN, Fore.GREEN, Fore.LIGHTGREEN_EX, Fore.LIGHTGREEN_EX, Fore.GREEN, Fore.GREEN]),
        ("MEDIA",  [Fore.CYAN, Fore.CYAN, Fore.LIGHTCYAN_EX, Fore.LIGHTCYAN_EX, Fore.CYAN, Fore.CYAN]),
        ("TOOLS",  [Fore.BLUE, Fore.BLUE, Fore.LIGHTBLUE_EX, Fore.LIGHTBLUE_EX, Fore.BLUE, Fore.BLUE])
    ]

    letter_spacing = " "

    print("\n")

    for word_str, line_colors in words_config:
        assembled_lines = [""] * 6
        for char_key in word_str:
            if char_key in letters:
                letter_art = letters[char_key]
                for i in range(6):
                    assembled_lines[i] += letter_art[i] + letter_spacing
            else:
                for i in range(6):
                    assembled_lines[i] += "        " + letter_spacing

        for i in range(6):
            line_to_print = assembled_lines[i].rstrip(letter_spacing)
            colored_line = line_colors[i] + line_to_print + Style.RESET_ALL
            print(colored_line)
        
        if word_str != words_config[-1][0]:
             print("\n")


if __name__ == "__main__":
    main_combined_script()