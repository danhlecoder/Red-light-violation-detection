"""
File utility functions for the traffic monitoring system
"""
import os
import json
import uuid
from werkzeug.utils import secure_filename

from src.core.config import ALLOWED_EXTENSIONS, UPLOAD_FOLDER, BOUNDARIES_FOLDER, logger

def allowed_file(filename):
    """
    Check if file has an allowed extension
    
    Args:
        filename: Name of the file to check
        
    Returns:
        bool: True if file extension is allowed
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file):
    """
    Save uploaded file with a unique ID
    
    Args:
        file: File object from request
        
    Returns:
        tuple: (video_id, video_path) if successful, (None, None) otherwise
    """
    import traceback
    
    if not file or file.filename == '':
        logger.error("No file selected")
        return None, None
        
    if not allowed_file(file.filename):
        logger.error(f"File type not allowed: {file.filename}")
        return None, None
    
    try:
        # Đảm bảo thư mục upload tồn tại
        if not os.path.exists(UPLOAD_FOLDER):
            try:
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                logger.info(f"Đã tạo thư mục upload: {UPLOAD_FOLDER}")
            except Exception as e:
                logger.error(f"Không thể tạo thư mục upload: {str(e)}")
                return None, None
        
        # Kiểm tra quyền ghi vào thư mục
        if not os.access(UPLOAD_FOLDER, os.W_OK):
            logger.error(f"Không có quyền ghi vào thư mục upload: {UPLOAD_FOLDER}")
            return None, None
        
        # Create unique ID for video
        video_id = str(uuid.uuid4())
        
        # Save file with secure filename
        filename = secure_filename(file.filename)
        video_path = os.path.join(UPLOAD_FOLDER, f"{video_id}_{filename}")
        
        # Kiểm tra dung lượng đĩa còn trống
        try:
            import shutil
            disk_usage = shutil.disk_usage(os.path.dirname(UPLOAD_FOLDER))
            required_space = getattr(file, 'content_length', 0)
            if required_space > 0 and disk_usage.free < required_space:
                logger.error(f"Không đủ dung lượng đĩa trống. Cần: {required_space} bytes, Còn trống: {disk_usage.free} bytes")
                return None, None
        except Exception as e:
            logger.warning(f"Không thể kiểm tra dung lượng đĩa: {str(e)}")
        
        # Lưu file
        logger.info(f"Đang lưu file {filename} vào {video_path}")
        file.save(video_path)
        
        # Kiểm tra file đã được lưu thành công
        if not os.path.exists(video_path):
            logger.error(f"File không được lưu thành công: {video_path}")
            return None, None
            
        file_size = os.path.getsize(video_path)
        logger.info(f"File saved successfully: {video_path}, size: {file_size} bytes")
        return video_id, video_path
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        logger.error(traceback.format_exc())
        return None, None

def save_boundaries(boundary_data, video_id):
    """
    Save boundary data to file
    
    Args:
        boundary_data: Boundary data to save
        video_id: ID of the video
        
    Returns:
        str: Filename if successful, None otherwise
    """
    try:
        filename = f"{video_id}_boundaries.json"
        filepath = os.path.join(BOUNDARIES_FOLDER, filename)
        
        with open(filepath, 'w') as f:
            json.dump(boundary_data, f)
        
        logger.info(f"Boundary data saved: {filepath}")
        return filename
    except Exception as e:
        logger.error(f"Error saving boundary data: {str(e)}")
        return None

def load_boundaries(video_id):
    """
    Load boundary data from file
    
    Args:
        video_id: ID of the video
        
    Returns:
        dict: Boundary data if found, None otherwise
    """
    try:
        filename = f"{video_id}_boundaries.json"
        filepath = os.path.join(BOUNDARIES_FOLDER, filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        
        logger.info(f"No boundary data found for video ID: {video_id}")
        return None
    except Exception as e:
        logger.error(f"Error loading boundary data: {str(e)}")
        return None 