"""
Module chính của ứng dụng hệ thống giám sát giao thông
"""
import os
from dotenv import load_dotenv
import logging
import threading
import time
from flask import Flask, render_template, request, jsonify, send_from_directory

# Nhập cấu hình
from src.core.config import (
    logger, MODEL_PATH, UPLOAD_FOLDER, PROCESSED_FOLDER, 
    BOUNDARIES_FOLDER, VIOLATIONS_FOLDER,
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG, ENABLE_LAZY_LOADING,
    STATIC_FOLDER, TEMPLATE_FOLDER, PRELOAD_MODEL
)

# Nhập các controller
from src.controllers.api_controller import api, set_video_processor
from src.controllers.view_controller import views

# Nhập các service
from src.services.video_processor import VideoProcessor

# Tải các biến môi trường từ file .env nếu tồn tại
load_dotenv()

# Thiết lập các biến môi trường cần thiết nếu chưa có
if 'SERVER_URL' not in os.environ:
    os.environ['SERVER_URL'] = 'http://localhost:5000'

# Thiết lập Discord webhook URL nếu chưa có
if 'DISCORD_WEBHOOK_URL' not in os.environ:
    os.environ['DISCORD_WEBHOOK_URL'] = 'https://discord.com/api/webhooks/1372935139474280489/tD2uU2vOLyeaq-dhDWWWF9ze64azEdI1yetZaUvyp-l3YNwap-4D5GgXa3tfHystbJCf'

# Cấu hình logger
logger = logging.getLogger('app')

# Tạo ứng dụng Flask
app = Flask(__name__, 
            static_folder=STATIC_FOLDER,
            template_folder=TEMPLATE_FOLDER)

# Cấu hình ứng dụng
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024 * 1024  # Giới hạn tải lên 500MB

# Đăng ký các blueprint
app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(views)

# Khởi tạo video processor (lazy loading)
video_processor = VideoProcessor(MODEL_PATH)

# Thiết lập video processor trong API controller
set_video_processor(video_processor)

def preload_model_after_startup():
    """
    Tải mô hình sau khi máy chủ đã khởi động
    """
    # Đợi 5 giây cho máy chủ khởi động hoàn toàn
    time.sleep(5)
    logger.info("Server fully started, preloading model...")
    video_processor.preload_model()
    # Khởi động worker để xử lý song song
    video_processor.start_processing_workers(2)
    logger.info("Model preloading initiated")

# Ghi log khởi động ứng dụng
logger.info("Application initialized with lazy model loading")

# Route gốc
@app.route('/')
def index():
    """Hiển thị trang chủ"""
    return render_template('index.html')

if __name__ == '__main__':
    logger.info(f"Starting server on {FLASK_HOST}:{FLASK_PORT}")
    
    # Tải mô hình sau khi máy chủ đã khởi động
    if ENABLE_LAZY_LOADING:
        logger.info("Lazy loading enabled. Starting model preload thread...")
        preload_thread = threading.Thread(target=preload_model_after_startup)
        preload_thread.daemon = True
        preload_thread.start()
    else:
        logger.info("Lazy loading disabled. Model will be loaded on first use.")
    
    # Khởi động máy chủ
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, threaded=True) 