"""
Module cấu hình cho hệ thống giám sát giao thông
"""
import os
import logging
import sys
import time
from pathlib import Path

# Thư mục cơ sở
BASE_DIR = Path(__file__).parent.parent.absolute()
MODEL_DIR = os.path.join(BASE_DIR, 'models/weights')
DATA_DIR = os.path.join(BASE_DIR, 'data')

# Thư mục dữ liệu
UPLOAD_FOLDER = os.path.join(DATA_DIR, 'uploads')
PROCESSED_FOLDER = os.path.join(DATA_DIR, 'processed')
BOUNDARIES_FOLDER = os.path.join(DATA_DIR, 'boundaries')
VIOLATIONS_FOLDER = os.path.join(DATA_DIR, 'violations')

# Đảm bảo tất cả các thư mục đều tồn tại
for folder in [UPLOAD_FOLDER, PROCESSED_FOLDER, BOUNDARIES_FOLDER, VIOLATIONS_FOLDER]:
    os.makedirs(folder, exist_ok=True)

# Cấu hình mô hình
MODEL_PATH = os.path.join(MODEL_DIR, 'v5.pt')

# Cờ tối ưu hóa hiệu suất
ENABLE_LAZY_LOADING = True  # Bật/tắt lazy loading của mô hình
PRELOAD_MODEL = True  # Tự động tải mô hình sau khi khởi động
WORKER_THREADS = 2  # Số lượng worker thread xử lý frame
FRAME_BUFFER_SIZE = 30  # Kích thước buffer cho frame đang xử lý

# Cấu hình Flask
FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')
FLASK_PORT = int(os.environ.get('FLASK_PORT', 5000))
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
STATIC_FOLDER = os.path.join(BASE_DIR, 'static')
TEMPLATE_FOLDER = os.path.join(BASE_DIR, 'static', 'templates')
MAX_CONTENT_LENGTH = 2 * 1024 * 1024 * 1024  # Giới hạn 2GB

# Cấu hình tải lên tập tin
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv'}

# Bộ lọc log tùy chỉnh để giảm tần suất ghi log
class ThrottledLogFilter(logging.Filter):
    def __init__(self, rate_limit=1.0):
        super().__init__()
        self.rate_limit = rate_limit  # Số giây giữa các log
        self.last_log = {}  # Dict để theo dõi thời gian log cuối cùng cho mỗi thông báo
    
    def filter(self, record):
        # Luôn ghi log các thông báo lỗi và nghiêm trọng
        if record.levelno >= logging.ERROR:
            return True
            
        # Tạo khóa dựa trên nội dung thông báo
        key = f"{record.module}:{record.levelname}:{record.getMessage()}"
        
        # Kiểm tra xem chúng ta đã thấy thông báo này gần đây chưa
        now = time.time()
        if key in self.last_log and now - self.last_log[key] < self.rate_limit:
            return False  # Bỏ qua log này
            
        # Cập nhật thời gian log cuối và cho phép thông báo
        self.last_log[key] = now
        
        # Dọn dẹp các mục cũ để tránh rò rỉ bộ nhớ
        if len(self.last_log) > 1000:
            # Xóa các mục cũ nhất
            old_keys = sorted(self.last_log.items(), key=lambda x: x[1])[:500]
            for k, _ in old_keys:
                del self.last_log[k]
                
        return True

# Tạo bộ lọc log
log_filter = ThrottledLogFilter(rate_limit=5.0)  # Giới hạn log tương tự đến một lần mỗi 5 giây

# Cấu hình logging
logging.basicConfig(
    level=logging.WARNING,  # Tăng mức lên WARNING để giảm khối lượng log
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('traffic')
logger.addFilter(log_filter)

# Cấu hình xử lý video
FRAME_WIDTH = 1920  # Tăng từ 1280 để có chất lượng cao hơn
FRAME_HEIGHT = 1080  # Tăng từ 720 để có chất lượng cao hơn

# Cấu hình cache
ENABLE_RESULT_CACHING = True  # Bật cache kết quả xử lý
CACHE_TIMEOUT = 3600  # Thời gian cache kết quả (giây)

# Cấu hình Discord
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/1372935139474280489/tD2uU2vOLyeaq-dhDWWWF9ze64azEdI1yetZaUvyp-l3YNwap-4D5GgXa3tfHystbJCf')

# Cấu hình Telegram
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '7964241802:AAHSM6g6CPOvz2kPZvbc50YdKavKWGalI1k')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '7519520037')  # Cần thiết lập ID chat/group để nhận thông báo

# Chỉ log cấu hình quan trọng khi khởi động
logger.warning(f"Starting Traffic Monitoring System - Model path: {MODEL_PATH}")
logger.warning(f"Flask config: host={FLASK_HOST}, port={FLASK_PORT}, debug={FLASK_DEBUG}")
logger.warning(f"Video resolution set to: {FRAME_WIDTH}x{FRAME_HEIGHT}")

# Log cấu hình
logger.info(f"Model path: {MODEL_PATH}")
logger.info(f"Upload folder: {UPLOAD_FOLDER}")
logger.info(f"Processed folder: {PROCESSED_FOLDER}")
logger.info(f"Lazy loading: {ENABLE_LAZY_LOADING}")
if DISCORD_WEBHOOK_URL:
    logger.info("Discord webhook connected")
else:
    logger.warning("Discord webhook connected false")
if TELEGRAM_BOT_TOKEN:
    logger.info("Telegram bot configured")
    if TELEGRAM_CHAT_ID:
        logger.info(f"Telegram notifications will be sent to chat ID: {TELEGRAM_CHAT_ID}")
    else:
        logger.warning("Telegram chat ID not configured. You'll need to provide it when calling the notification functions.")
else:
    logger.warning("Telegram bot token not configured. Traffic violations won't be sent to Telegram.") 