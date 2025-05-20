import asyncio
import json
import os
import logging
from pathlib import Path
import base64
from io import BytesIO
from datetime import datetime

import aiohttp
from telegram import Bot, InputFile
from telegram.constants import ParseMode

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("telegram_bot")

# Cấu hình Telegram Bot - lấy từ biến môi trường hoặc sử dụng token cố định
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '7964241802:AAHSM6g6CPOvz2kPZvbc50YdKavKWGalI1k')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '7519520037')  # ID của chat/group/channel

# URL gốc của server - thay đổi theo domain của bạn
SERVER_URL = os.environ.get('SERVER_URL', 'http://localhost:5000')

# Đường dẫn tới thư mục vi phạm
BASE_DIR = Path(__file__).parent.parent.absolute()
DATA_DIR = os.path.join(BASE_DIR, 'data')
VIOLATIONS_FOLDER = os.path.join(DATA_DIR, 'violations')

def send_telegram_message(chat_id, text):
    """
    Gửi tin nhắn văn bản đến Telegram sử dụng requests thay vì asyncio
    
    Args:
        chat_id (str): ID của chat/group/channel để gửi tin nhắn
        text (str): Nội dung tin nhắn
    """
    import requests
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logger.info(f"Đã gửi tin nhắn thành công đến chat_id: {chat_id}")
            return True
        else:
            logger.error(f"Lỗi khi gửi tin nhắn: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi gửi tin nhắn: {e}")
        return False

def send_telegram_photo(chat_id, photo_path, caption):
    """
    Gửi ảnh đến Telegram sử dụng requests thay vì asyncio
    
    Args:
        chat_id (str): ID của chat/group/channel để gửi tin nhắn
        photo_path (str): Đường dẫn đến file ảnh
        caption (str): Chú thích cho ảnh
    """
    import requests
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    try:
        # Đọc file ảnh
        with open(photo_path, 'rb') as photo_file:
            files = {'photo': photo_file}
            payload = {
                "chat_id": chat_id,
                "caption": caption,
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, data=payload, files=files)
            
        if response.status_code == 200:
            logger.info(f"Đã gửi ảnh thành công đến chat_id: {chat_id}")
            return True
        else:
            logger.error(f"Lỗi khi gửi ảnh: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Lỗi khi gửi ảnh: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def send_violation_to_telegram(violation_data, chat_id=None):
    """
    Gửi thông tin vi phạm đến Telegram sử dụng requests thay vì asyncio
    
    Args:
        violation_data (dict): Dữ liệu vi phạm gồm các thông tin như id, thời gian, loại phương tiện, biển số, ảnh...
        chat_id (str, optional): ID của chat/group/channel để gửi tin nhắn. Nếu không cung cấp, sẽ sử dụng TELEGRAM_CHAT_ID.
    """
    try:
        if not TELEGRAM_BOT_TOKEN:
            logger.error("CẢNH BÁO: TELEGRAM_BOT_TOKEN chưa được cấu hình")
            return False
            
        if not chat_id and not TELEGRAM_CHAT_ID:
            logger.error("CẢNH BÁO: TELEGRAM_CHAT_ID chưa được cấu hình")
            return False
            
        # Sử dụng chat_id được cung cấp hoặc mặc định
        target_chat_id = chat_id or TELEGRAM_CHAT_ID
            
        # In dữ liệu nhận được để debug
        logger.info(f"Dữ liệu vi phạm nhận được: {json.dumps(violation_data, indent=2, ensure_ascii=False)}")
        
        # Lấy thông tin từ dữ liệu vi phạm
        violation_id = violation_data.get('id', 'N/A')
        timestamp = violation_data.get('timestamp', datetime.now().isoformat())
        vehicle_type = violation_data.get('vehicleType', 'Không xác định')
        license_plate = violation_data.get('licensePlate', 'Không xác định')
        violation_type = violation_data.get('violation_type', 'Vượt đèn đỏ')
        
        # Định dạng ID vi phạm
        if isinstance(violation_id, (int, str)) and str(violation_id).isdigit():
            formatted_id = str(violation_id).zfill(5)
        else:
            formatted_id = str(violation_id)
        
        # Chuyển đổi timestamp sang đối tượng datetime
        try:
            if isinstance(timestamp, str):
                # Xử lý nhiều định dạng timestamp khác nhau
                if "T" in timestamp:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
                timestamp_str = dt.strftime('%H:%M:%S %d/%m/%Y')
            else:
                timestamp_str = datetime.now().strftime('%H:%M:%S %d/%m/%Y')
        except Exception as e:
            logger.error(f"Lỗi khi phân tích timestamp: {e}")
            timestamp_str = str(timestamp)
        
        # Tạo nội dung tin nhắn
        message_text = (
            f"🚨 *VI PHẠM - #{formatted_id}* 🚨\n\n"
            f"Phát hiện vi phạm *{violation_type}* đã được xác nhận.\n\n"
            f"⏰ *Thời gian:* {timestamp_str}\n"
            f"🚗 *Loại phương tiện:* {vehicle_type}\n"
            f"🔢 *Biển số xe:* {license_plate}\n\n"
            f"_Hệ thống giám sát giao thông • Hôm nay lúc {datetime.now().strftime('%H:%M')}_"
        )
        
        # Xử lý hình ảnh vi phạm
        scene_image_path = violation_data.get('scene_image', '')
        if scene_image_path:
            # Tạo đường dẫn đầy đủ
            if os.path.isabs(scene_image_path):
                full_path = scene_image_path
            else:
                # Nếu là đường dẫn tương đối, thử tìm trong thư mục vi phạm
                file_name = os.path.basename(scene_image_path)
                full_path = os.path.join(VIOLATIONS_FOLDER, file_name)
                
                # Nếu không tìm thấy, thử tìm file theo ID
                if not os.path.exists(full_path):
                    # Tìm kiếm file ảnh có ID tương tự trong thư mục vi phạm
                    if os.path.exists(VIOLATIONS_FOLDER):
                        for file in os.listdir(VIOLATIONS_FOLDER):
                            if f"violation_{formatted_id}_scene" in file:
                                full_path = os.path.join(VIOLATIONS_FOLDER, file)
                                logger.info(f"Đã tìm thấy file ảnh thay thế: {file}")
                                break
            
            # Kiểm tra xem file có tồn tại không
            if os.path.exists(full_path):
                logger.info(f"Đã tìm thấy file ảnh: {full_path}")
                return send_telegram_photo(target_chat_id, full_path, message_text)
        
        # Nếu không có ảnh, gửi tin nhắn văn bản
        return send_telegram_message(target_chat_id, message_text)
        
    except Exception as e:
        logger.error(f"Lỗi khi gửi thông tin vi phạm lên Telegram: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def process_violation_webhook(request_data, chat_id=None):
    """
    Xử lý webhook từ server khi có vi phạm được xác nhận
    
    Args:
        request_data (dict): Dữ liệu từ webhook
        chat_id (str, optional): ID của chat/group/channel để gửi tin nhắn
    """
    try:
        violation_data = request_data.get('violation', {})
        if not violation_data:
            logger.error("Không có dữ liệu vi phạm trong request")
            return False
            
        return send_violation_to_telegram(violation_data, chat_id)
    except Exception as e:
        logger.error(f"Lỗi khi xử lý webhook vi phạm: {e}")
        return False

def send_test_message(chat_id):
    """
    Gửi tin nhắn test để kiểm tra kết nối với Telegram
    
    Args:
        chat_id (str): ID của chat/group/channel để gửi tin nhắn
    """
    return send_telegram_message(
        chat_id, 
        "🔄 Hệ thống giám sát giao thông đã kết nối thành công với Telegram Bot!"
    )

# Nếu chạy trực tiếp thông qua script
if __name__ == "__main__":
    logger.info("Bot Telegram đang chạy. Đang chờ webhook vi phạm...")
    logger.info(f"Thư mục vi phạm: {VIOLATIONS_FOLDER}")
    
    # Kiểm tra thư mục vi phạm
    if os.path.exists(VIOLATIONS_FOLDER):
        files = os.listdir(VIOLATIONS_FOLDER)
        logger.info(f"Số lượng file trong thư mục vi phạm: {len(files)}")
        if files:
            logger.info(f"Một số file vi phạm: {files[:5]}")
    else:
        logger.warning(f"Thư mục vi phạm không tồn tại: {VIOLATIONS_FOLDER}")
    
    # Kiểm tra cấu hình Telegram
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN chưa được cấu hình. Vui lòng cấu hình để sử dụng bot.")
    elif not TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_CHAT_ID chưa được cấu hình. Vui lòng cung cấp chat_id khi gọi hàm gửi thông báo.")
    
    # Example để test
    test_data = {
        "id": "00001",
        "timestamp": "2023-10-25T15:30:45",
        "vehicleType": "Ô tô",
        "licensePlate": "51F-12345",
        "violation_type": "Vượt đèn đỏ",
        "scene_image": "violation_00004_scene.jpg"  # Sử dụng file có sẵn trong thư mục vi phạm
    }
    
    # Nếu có chat_id, chạy test gửi thông báo
    if TELEGRAM_CHAT_ID and TELEGRAM_BOT_TOKEN:
        logger.info(f"Đang thử gửi tin nhắn test đến chat_id: {TELEGRAM_CHAT_ID}")
        send_test_message(TELEGRAM_CHAT_ID)
        
        logger.info("Đang thử gửi dữ liệu vi phạm mẫu để kiểm tra...")
        send_violation_to_telegram(test_data)
    else:
        logger.info("Vui lòng cấu hình TELEGRAM_BOT_TOKEN và TELEGRAM_CHAT_ID để test bot.")
        logger.info("Bạn có thể sử dụng lệnh sau để chạy bot với chat_id cụ thể:")
        logger.info("$env:TELEGRAM_CHAT_ID=\"YOUR_CHAT_ID\"; python bot/telegram_bot.py")
