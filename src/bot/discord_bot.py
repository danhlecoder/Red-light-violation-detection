import discord
import aiohttp
import asyncio
import json
import os
from datetime import datetime
from discord import Webhook, Embed, Color
import logging
from pathlib import Path
import requests
import base64
from io import BytesIO

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("discord_bot")

# Cấu hình Discord Webhook - lấy từ biến môi trường hoặc sử dụng URL cố định
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/1372935139474280489/tD2uU2vOLyeaq-dhDWWWF9ze64azEdI1yetZaUvyp-l3YNwap-4D5GgXa3tfHystbJCf')

# URL gốc của server - thay đổi theo domain của bạn
SERVER_URL = os.environ.get('SERVER_URL', 'http://localhost:5000')

# Đường dẫn tới thư mục vi phạm
BASE_DIR = Path(__file__).parent.parent.absolute()
DATA_DIR = os.path.join(BASE_DIR, 'data')
VIOLATIONS_FOLDER = os.path.join(DATA_DIR, 'violations')

# Khởi tạo client discord
client = discord.Client(intents=discord.Intents.default())

async def send_violation_to_discord(violation_data):
    """
    Gửi thông tin vi phạm đến Discord thông qua webhook
    
    Args:
        violation_data (dict): Dữ liệu vi phạm gồm các thông tin như id, thời gian, loại phương tiện, biển số, ảnh...
    """
    try:
        if not DISCORD_WEBHOOK_URL:
            logger.error("CẢNH BÁO: DISCORD_WEBHOOK_URL chưa được cấu hình")
            return False
            
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
        
        # Xử lý hình ảnh vi phạm
        image_data = None
        image_url = None
        
        # 1. Thử lấy hình ảnh từ đường dẫn file
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
                try:
                    # Đọc file ảnh và mã hóa base64
                    with open(full_path, 'rb') as img_file:
                        image_data = base64.b64encode(img_file.read()).decode('utf-8')
                    logger.info(f"Đã đọc và mã hóa file ảnh: {full_path}")
                except Exception as e:
                    logger.error(f"Lỗi khi đọc file ảnh: {e}")
            else:
                logger.warning(f"Không tìm thấy file ảnh: {full_path}")
        
        # 2. Thử lấy URL ảnh từ dữ liệu
        if not image_data:
            scene_image_url = violation_data.get('scene_image_url', '')
            if scene_image_url:
                if scene_image_url.startswith('/'):
                    # Chuyển đổi URL tương đối thành URL tuyệt đối
                    scene_image_url = f"{SERVER_URL}{scene_image_url}"
                
                # Sử dụng URL trực tiếp
                image_url = scene_image_url
                logger.info(f"Sử dụng URL ảnh: {image_url}")
        
        # Tạo embed để hiển thị đẹp hơn trên Discord
        embed = Embed(
            title=f"🚨 Vi phạm - #{formatted_id} 🚨",
            description=f"Phát hiện vi phạm **{violation_type}** đã được xác nhận.",
            color=Color.red(),
            timestamp=datetime.now()
        )
        
        # Thêm thông tin chi tiết
        embed.add_field(name="⏰ Thời gian", value=timestamp_str, inline=True)
        embed.add_field(name="🚗 Loại phương tiện", value=vehicle_type, inline=True)
        embed.add_field(name="🔢 Biển số xe", value=license_plate, inline=True)
        
        # Thêm footer
        embed.set_footer(text=f"Hệ thống giám sát giao thông • Hôm nay lúc {datetime.now().strftime('%H:%M')}")
        
        # Gửi thông tin vi phạm qua webhook
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(DISCORD_WEBHOOK_URL, session=session)
            
            # Nếu có dữ liệu ảnh, gửi dưới dạng file
            if image_data:
                # Chuyển đổi base64 thành bytes
                image_bytes = base64.b64decode(image_data)
                file = discord.File(BytesIO(image_bytes), filename=f"violation_{formatted_id}.jpg")
                
                # Đặt ảnh vào embed
                embed.set_image(url=f"attachment://violation_{formatted_id}.jpg")
                
                # Gửi embed với file đính kèm
                await webhook.send(embed=embed, file=file)
                logger.info(f"Đã gửi thông tin vi phạm #{formatted_id} với file ảnh đính kèm")
            # Nếu có URL ảnh, sử dụng URL
            elif image_url:
                embed.set_image(url=image_url)
                await webhook.send(embed=embed)
                logger.info(f"Đã gửi thông tin vi phạm #{formatted_id} với URL ảnh: {image_url}")
            # Nếu không có ảnh, chỉ gửi thông tin
            else:
                await webhook.send(embed=embed)
                logger.info(f"Đã gửi thông tin vi phạm #{formatted_id} không có ảnh")
        
        logger.info(f"Đã gửi thông tin vi phạm #{formatted_id} lên Discord thành công")
        return True
        
    except Exception as e:
        logger.error(f"Lỗi khi gửi thông tin vi phạm lên Discord: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def process_violation_webhook(request_data):
    """
    Xử lý webhook từ server khi có vi phạm được xác nhận
    
    Args:
        request_data (dict): Dữ liệu từ webhook
    """
    try:
        violation_data = request_data.get('violation', {})
        if not violation_data:
            logger.error("Không có dữ liệu vi phạm trong request")
            return False
            
        return await send_violation_to_discord(violation_data)
    except Exception as e:
        logger.error(f"Lỗi khi xử lý webhook vi phạm: {e}")
        return False

# Hàm tiện ích để chuyển đổi dữ liệu từ Flask/FastAPI thành định dạng phù hợp
def convert_violation_data(request_json):
    """
    Chuyển đổi dữ liệu từ API web thành định dạng phù hợp cho Discord
    """
    # Đã chuyển đổi trong hàm xử lý chính
    return request_json

# Nếu chạy trực tiếp thông qua script
if __name__ == "__main__":
    logger.info("Bot Discord đang chạy. Đang chờ webhook vi phạm...")
    logger.info(f"Thư mục vi phạm: {VIOLATIONS_FOLDER}")
    
    # Kiểm tra thư mục vi phạm
    if os.path.exists(VIOLATIONS_FOLDER):
        files = os.listdir(VIOLATIONS_FOLDER)
        logger.info(f"Số lượng file trong thư mục vi phạm: {len(files)}")
        if files:
            logger.info(f"Một số file vi phạm: {files[:5]}")
    else:
        logger.warning(f"Thư mục vi phạm không tồn tại: {VIOLATIONS_FOLDER}")
    
    # Example để test
    test_data = {
        "id": "00001",
        "timestamp": "2023-10-25T15:30:45",
        "vehicleType": "Ô tô",
        "licensePlate": "51F-12345",
        "violation_type": "Vượt đèn đỏ",
        "scene_image": "violation_00001_scene.jpg"
    }
    
    # Chạy test gửi thông báo nếu có webhook URL
    if DISCORD_WEBHOOK_URL:
        asyncio.run(send_violation_to_discord(test_data))
        logger.info("Đã gửi dữ liệu vi phạm mẫu để kiểm tra.")
    else:
        logger.info("Vui lòng cấu hình DISCORD_WEBHOOK_URL để sử dụng bot.")
