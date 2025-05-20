"""
Video utility functions for the traffic monitoring system
"""
import os
import cv2
import numpy as np
import time
import threading
import glob

from src.core.config import logger, PROCESSED_FOLDER

def create_empty_frame(width=1280, height=720, message="Processing..."):
    """
    Create an empty frame with a message
    
    Args:
        width: Frame width
        height: Frame height
        message: Message to display
        
    Returns:
        np.ndarray: Empty frame with message
    """
    # Create a gray frame
    frame = np.ones((height, width, 3), dtype=np.uint8) * 128
    
    # Add message
    cv2.putText(frame, message, (width//2 - 100, height//2), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    return frame

def save_frame(frame, filename):
    """
    Save frame to file
    
    Args:
        frame: Frame to save
        filename: Filename to save as
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        filepath = os.path.join(PROCESSED_FOLDER, filename)
        cv2.imwrite(filepath, frame)
        
        # Verify file was created
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            logger.error(f"Failed to save frame: {filepath}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error saving frame: {str(e)}")
        return False

def clear_processed_frames():
    """
    Clear all processed frames from the processed folder
    
    Returns:
        int: Number of files removed
    """
    count = 0
    try:
        for file in os.listdir(PROCESSED_FOLDER):
            if file.startswith("frame_") and file.endswith(".jpg"):
                try:
                    os.remove(os.path.join(PROCESSED_FOLDER, file))
                    count += 1
                except Exception as e:
                    logger.error(f"Could not delete file {file}: {str(e)}")
        
        logger.info(f"Removed {count} old frames")
        return count
    except Exception as e:
        logger.error(f"Error clearing processed frames: {str(e)}")
        return 0

def get_latest_frame():
    """
    Get the latest processed frame
    
    Returns:
        str: Filename of latest frame if found, None otherwise
    """
    try:
        # Check if processed folder exists
        if not os.path.exists(PROCESSED_FOLDER):
            logger.warning(f"Processed folder does not exist: {PROCESSED_FOLDER}, creating it now")
            os.makedirs(PROCESSED_FOLDER, exist_ok=True)
            
            # Create an empty frame
            empty_frame = create_empty_frame(message="Đang khởi tạo hệ thống...")
            empty_frame_path = "empty_frame.jpg"
            save_frame(empty_frame, empty_frame_path)
            return empty_frame_path
        
        # Get all jpg files in processed folder
        try:
            jpg_files = [f for f in os.listdir(PROCESSED_FOLDER) if f.lower().endswith('.jpg')]
        except Exception as e:
            logger.error(f"Error listing files in processed folder: {str(e)}")
            jpg_files = []
        
        if not jpg_files:
            logger.warning("No processed frames found, creating empty frame")
            # Create an empty frame
            empty_frame = create_empty_frame(message="Đang xử lý video...")
            empty_frame_path = "empty_frame.jpg"
            save_frame(empty_frame, empty_frame_path)
            return empty_frame_path
        
        try:
            # Get latest file based on modification time
            latest_file = max(jpg_files, key=lambda f: os.path.getmtime(os.path.join(PROCESSED_FOLDER, f)))
            
            # Verify file exists and is readable
            file_path = os.path.join(PROCESSED_FOLDER, latest_file)
            if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                logger.warning(f"Latest frame file is invalid: {file_path}")
                # Create an empty frame
                empty_frame = create_empty_frame(message="Đang tạo lại frame...")
                empty_frame_path = "empty_frame.jpg"
                save_frame(empty_frame, empty_frame_path)
                return empty_frame_path
                
            return latest_file
        except Exception as e:
            logger.error(f"Error getting latest file: {str(e)}")
            # Create an empty frame
            empty_frame = create_empty_frame(message="Đang tạo lại frame...")
            empty_frame_path = "empty_frame.jpg"
            save_frame(empty_frame, empty_frame_path)
            return empty_frame_path
            
    except Exception as e:
        logger.error(f"Error getting latest frame: {str(e)}")
        
        try:
            # Create an error frame
            error_frame = create_empty_frame(message=f"Lỗi: {str(e)}")
            error_frame_path = "error_frame.jpg"
            save_frame(error_frame, error_frame_path)
            return error_frame_path
        except Exception as nested_error:
            logger.critical(f"Critical error creating error frame: {str(nested_error)}")
            return "error_frame.jpg"  # Return a default name even if save failed 

def read_frame(file_path):
    """
    Đọc frame từ file
    
    Args:
        file_path: Đường dẫn đến file ảnh
        
    Returns:
        np.ndarray: Frame đã đọc hoặc None nếu có lỗi
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"File không tồn tại: {file_path}")
            return None
            
        frame = cv2.imread(file_path)
        if frame is None:
            logger.error(f"Không thể đọc ảnh từ file: {file_path}")
            return None
            
        return frame
    except Exception as e:
        logger.error(f"Lỗi khi đọc frame: {str(e)}")
        return None 