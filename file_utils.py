from PyQt5.QtWidgets import QFileDialog
import magic
import cv2
import numpy as np
from PIL import Image
import tempfile
import os, io, sys
import ctypes
import ctypes.wintypes

def choose_files():
    files, _ = QFileDialog.getOpenFileNames(None, "Select Photos/Videos")
    return files

def choose_export_location(filename: str):
    path, _ = QFileDialog.getSaveFileName(None, "Export File", filename)
    return path

def is_image(data: bytes) -> bool:
    mime = magic.from_buffer(data, mime=True)
    return mime.startswith("image/")

def is_video(data: bytes) -> bool:
    mime = magic.from_buffer(data, mime=True)
    return mime.startswith("video/")

def generate_video_thumbnail(video_bytes, size=(256, 256)):
    # Save video bytes to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
        tmp_file.write(video_bytes)
        tmp_filename = tmp_file.name
    
    cap = cv2.VideoCapture(tmp_filename)
    ret, frame = cap.read()
    cap.release()
    
    os.unlink(tmp_filename)  # Delete temp file immediately
    
    if not ret:
        return None
    
    # Convert BGR to RGB for PIL
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)
    img.thumbnail(size, Image.LANCZOS)
    return img

def generate_thumbnail(image_bytes, size=(256, 256)):
    img = Image.open(io.BytesIO(image_bytes))
    img = img.convert("RGB")
    img.thumbnail(size, Image.LANCZOS)
    return img

def set_file_creation_time_windows(path, ctime):
    FILE_WRITE_ATTRIBUTES = 0x0100
    handle = ctypes.windll.kernel32.CreateFileW(
        ctypes.c_wchar_p(path),
        FILE_WRITE_ATTRIBUTES,
        0,
        None,
        3,  # OPEN_EXISTING
        0,
        None
    )
    if handle == -1:
        print("Failed to open file handle for creation time.")
        return

    # Convert UNIX timestamp to Windows FILETIME format (100-nanosecond intervals since 1601)
    wintime = int((ctime + 11644473600) * 10000000)
    low = wintime & 0xFFFFFFFF
    high = wintime >> 32

    ft = ctypes.wintypes.FILETIME(low, high)
    ctypes.windll.kernel32.SetFileTime(handle, ctypes.byref(ft), None, None)
    ctypes.windll.kernel32.CloseHandle(handle)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller .exe """
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)