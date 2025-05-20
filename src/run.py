"""
Điểm khởi đầu cho hệ thống giám sát giao thông
"""
import os
import sys
import time
import threading

# Thêm thư mục cha vào đường dẫn Python
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.app import app, video_processor
from src.core.config import (
    logger, FLASK_HOST, FLASK_PORT, FLASK_DEBUG,
    ENABLE_LAZY_LOADING, PRELOAD_MODEL, WORKER_THREADS
)
from src.utils.setup import create_directories

def preload_model_background():
    """
    Tải mô hình trong nền sau khi máy chủ đã khởi động
    """
    # Đợi 5 giây để máy chủ khởi động hoàn toàn
    time.sleep(5)
    logger.info("Tiến hành tải mô hình trong nền...")
    
    # Tải mô hình
    video_processor.preload_model()
    
    # Khởi động các worker xử lý frame
    video_processor.start_processing_workers(WORKER_THREADS)
    
    logger.info(f"Hoàn tất tải mô hình và khởi động {WORKER_THREADS} worker")

if __name__ == '__main__':
    try:
        # Đảm bảo tất cả các thư mục tồn tại
        create_directories()
        
        # Khởi động thread tải mô hình trong nền (nếu được bật)
        if ENABLE_LAZY_LOADING and PRELOAD_MODEL:
            logger.info("Máy chủ sẽ tải mô hình trong nền sau khi khởi động")
            preload_thread = threading.Thread(target=preload_model_background)
            preload_thread.daemon = True
            preload_thread.start()
        
        # Khởi động ứng dụng
        logger.info(f"Khởi động Traffic Monitoring System trên {FLASK_HOST}:{FLASK_PORT}")
        logger.info(f"Chế độ lazy loading: {'BẬT' if ENABLE_LAZY_LOADING else 'TẮT'}")
        app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, threaded=True)
    except Exception as e:
        logger.error(f"Lỗi khởi động ứng dụng: {str(e)}")
        sys.exit(1)
