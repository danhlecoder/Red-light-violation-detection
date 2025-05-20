"""
API controller for the traffic monitoring system
"""
from flask import Blueprint, jsonify, request, send_from_directory, current_app
import os
import random
import traceback
import time
import asyncio
from functools import wraps

from src.core.config import logger, PROCESSED_FOLDER, VIOLATIONS_FOLDER
from src.utils.file_utils import save_uploaded_file, save_boundaries, load_boundaries
from src.utils.video_utils import get_latest_frame, create_empty_frame, save_frame, read_frame
from src.bot.discord_bot import send_violation_to_discord
from src.bot.telegram_bot import send_violation_to_telegram

# Create API blueprint
api = Blueprint('api', __name__)

# Reference to video processor service (will be set during app initialization)
video_processor = None

# Caching mechanism
cache = {}
cache_ttl = {
    'get_latest_frame': 0.05,  # 50ms (decreased from 100ms for faster updates)
    'get_stats': 1,           # 1 second (decreased from 2s for more frequent updates)
    'get_violations': 5       # 5 seconds
}

def cached(key, ttl_seconds=1):
    """
    Decorator to cache API responses
    
    Args:
        key: Cache key prefix
        ttl_seconds: Time to live in seconds
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Tạo cache key dựa trên tên hàm và tham số
            cache_key = f"{key}_{request.path}_{str(request.args)}"
            
            # Kiểm tra xem có trong cache không và còn hạn không
            if cache_key in cache and time.time() - cache[cache_key]['timestamp'] < ttl_seconds:
                return cache[cache_key]['data']
            
            # Nếu không có trong cache hoặc hết hạn, gọi hàm gốc
            result = f(*args, **kwargs)
            
            # Lưu kết quả vào cache
            cache[cache_key] = {
                'data': result,
                'timestamp': time.time()
            }
            
            # Xóa các cache cũ nếu quá nhiều
            if len(cache) > 100:  # Giới hạn kích thước cache
                oldest_key = min(cache.items(), key=lambda x: x[1]['timestamp'])[0]
                del cache[oldest_key]
                
            return result
        return decorated_function
    return decorator

def set_video_processor(processor):
    """
    Set the video processor reference
    
    Args:
        processor: VideoProcessor instance
    """
    global video_processor
    video_processor = processor
    logger.warning("Video processor reference set in API controller")

@api.route('/upload', methods=['POST'])
def upload_file():
    """Handle video upload"""
    try:
        if 'video' not in request.files:
            logger.error("Không có file được gửi lên")
            return jsonify({'error': 'No file was sent'}), 400
        
        file = request.files['video']
        
        if file.filename == '':
            logger.error("Không có file được chọn")
            return jsonify({'error': 'No file selected'}), 400
        
        # Kiểm tra kích thước file
        if not hasattr(file, 'content_length'):
            # Nếu không có thuộc tính content_length, đọc toàn bộ file để xác định kích thước
            file_data = file.read()
            file_size = len(file_data)
            # Đặt lại con trỏ file về đầu
            file.seek(0)
        else:
            file_size = file.content_length
        
        # Kiểm tra kích thước file (giới hạn 2GB)
        max_size = 2 * 1024 * 1024 * 1024  # 2GB
        if file_size > max_size:
            logger.error(f"File quá lớn: {file_size} bytes (giới hạn: {max_size} bytes)")
            return jsonify({'error': f'File too large. Maximum size is 2GB'}), 413
        
        # Save uploaded file
        logger.info(f"Bắt đầu lưu file: {file.filename}")
        video_id, video_path = save_uploaded_file(file)
        
        if not video_id or not video_path:
            logger.error("Lỗi khi lưu file")
            return jsonify({'error': 'Error saving file'}), 500
        
        # Load boundaries if they exist
        try:
            boundaries = load_boundaries(video_id)
            if boundaries:
                logger.info(f"Found boundary data for video ID: {video_id}")
            else:
                logger.info(f"No boundary data found for video ID: {video_id}, creating default boundaries")
                # Create empty default boundaries
                boundaries = {
                    'line': [],
                    'vehiclePolygon': [],
                    'trafficLightPolygon': []
                }
        except Exception as e:
            logger.error(f"Lỗi khi tải dữ liệu biên: {str(e)}")
            # Tạo biên mặc định nếu có lỗi
            boundaries = {
                'line': [],
                'vehiclePolygon': [],
                'trafficLightPolygon': []
            }
        
        # Clear cache when uploading new video
        global cache
        cache = {}
        
        # Start video processing
        try:
            if video_processor is None:
                logger.error("Video processor is None, không thể xử lý video")
                return jsonify({'error': 'Video processor not initialized'}), 500
                
            video_processor.start_processing(video_path, boundaries)
            logger.info(f"Đã bắt đầu xử lý video: {video_path}")
        except Exception as e:
            logger.error(f"Lỗi khi bắt đầu xử lý video: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': f'Error starting video processing: {str(e)}'}), 500
        
        return jsonify({
            'success': True,
            'video_id': video_id,
            'message': 'Video uploaded and processing started'
        })
    except Exception as e:
        logger.error(f"Lỗi không xác định khi xử lý upload: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@api.route('/save_boundaries', methods=['POST'])
def save_boundaries_route():
    """Save boundary data"""
    data = request.json
    if not data:
        return jsonify({'error': 'No boundary data sent'}), 400
    
    video_id = data.get('video_id')
    if not video_id:
        # If no video_id, create a new ID
        video_id = "default"
    
    boundaries = data.get('boundaries')
    if not boundaries:
        return jsonify({'error': 'Invalid boundary data'}), 400
    
    # Save boundaries to file
    filename = save_boundaries(boundaries, video_id)
    
    # Update boundaries in video processor
    video_processor.update_boundaries(boundaries)
    
    # Clear cache when updating boundaries
    global cache
    cache = {}
    
    return jsonify({
        'success': True,
        'filename': filename,
        'message': 'Boundary data saved successfully'
    })

@api.route('/get_boundaries/<video_id>', methods=['GET'])
@cached('boundaries', ttl_seconds=60)  # Cache boundaries for 60 seconds
def get_boundaries_route(video_id):
    """Get boundary data for a video"""
    boundaries = load_boundaries(video_id)
    
    if boundaries:
        return jsonify({
            'success': True,
            'boundaries': boundaries
        })
    
    return jsonify({
        'success': False,
        'message': 'No boundary data found for this video'
    })

@api.route('/get_latest_frame', methods=['GET'])
@cached('frame', ttl_seconds=0.05)  # Cache frame for 50ms to reduce load but keep responsiveness
def get_latest_frame_route():
    """Get the latest processed frame"""
    try:
        # Completely remove logging for this high-frequency endpoint
        
        # Get latest frame filename
        latest_file = get_latest_frame()
        
        # Kiểm tra xem file có tồn tại không
        file_path = os.path.join(PROCESSED_FOLDER, latest_file)
        if not os.path.exists(file_path):
            # Tạo frame trống
            empty_frame = create_empty_frame(message="Không tìm thấy frame")
            empty_frame_path = "empty_frame.jpg"
            save_frame(empty_frame, empty_frame_path)
            latest_file = empty_frame_path
        
        # Return file from processed folder
        return send_from_directory(PROCESSED_FOLDER, latest_file)
        
    except Exception as e:
        # Minimize error logging for this high-frequency endpoint
        if random.random() < 0.01:  # Only log 1% of errors
            logger.error(f"Lỗi trong get_latest_frame: {str(e)}")
        
        try:
            # Tạo frame lỗi
            error_frame = create_empty_frame(message=f"Lỗi: {str(e)}")
            error_frame_path = "error_frame.jpg"
            save_frame(error_frame, error_frame_path)
            
            # Trả về frame lỗi
            return send_from_directory(PROCESSED_FOLDER, error_frame_path)
        except Exception as nested_e:
            logger.critical(f"Lỗi nghiêm trọng khi tạo frame lỗi: {str(nested_e)}")
            return jsonify({'error': f'Lỗi nghiêm trọng: {str(e)}, không thể tạo frame lỗi: {str(nested_e)}'}), 500

@api.route('/get_stats', methods=['GET'])
@cached('stats', ttl_seconds=1)  # Cache stats for 1 second (reduced from 2s)
def get_stats():
    """Get current statistics"""
    # Remove logging for this frequently called endpoint
    return jsonify(video_processor.get_stats())

@api.route('/get_violations', methods=['GET'])
@cached('violations', ttl_seconds=5)  # Cache violations for 5 seconds
def get_violations():
    """Get violations with pagination"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Remove logging for this endpoint
        
        if not video_processor:
            return jsonify({
                'success': False,
                'message': 'Hệ thống chưa sẵn sàng, vui lòng thử lại sau',
                'violations': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0
            })
        
        violations_data = video_processor.get_violations(page, per_page)
        
        # Thêm trường success để client biết API đã thành công
        violations_data['success'] = True
        
        return jsonify(violations_data)
    except Exception as e:
        # Ghi log chi tiết lỗi với traceback để dễ debug
        error_msg = f"Lỗi khi lấy dữ liệu vi phạm: {str(e)}"
        if random.random() < 0.05:  # Chỉ log 5% lỗi để giảm tải (giảm từ 10%)
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
        
        # Trả về lỗi cho client với HTTP 200 để tránh lỗi 500
        return jsonify({
            'success': False,
            'message': error_msg,
            'violations': [],
            'total': 0,
            'page': page if 'page' in locals() else 1,
            'per_page': per_page if 'per_page' in locals() else 10,
            'total_pages': 0
        })

@api.route('/stop_processing', methods=['POST'])
def stop_processing():
    """Stop video processing"""
    try:
        # Clear cache when stopping processing
        global cache
        cache = {}
        
        result = video_processor.stop_processing()
        
        return jsonify({
            'success': True,
            'stopped': result,
            'message': 'Đã dừng xử lý video' if result else 'Không có video nào đang được xử lý'
        })
    except Exception as e:
        logger.error(f"Lỗi khi dừng xử lý video: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Đã xảy ra lỗi khi dừng xử lý video'
        }), 500

@api.route('/processed/<path:filename>')
def processed_file(filename):
    """Serve processed files"""
    return send_from_directory(PROCESSED_FOLDER, filename)

@api.route('/violations/<path:filename>')
def violation_file(filename):
    """Serve violation image files"""
    try:
        if not os.path.exists(os.path.join(VIOLATIONS_FOLDER, filename)):
            if random.random() < 0.05:  # Giảm log xuống 5% (từ 10%)
                logger.error(f"Không tìm thấy file vi phạm: {filename}")
            return jsonify({
                'success': False,
                'message': f'Không tìm thấy file vi phạm: {filename}'
            }), 404
        
        return send_from_directory(VIOLATIONS_FOLDER, filename)
    except Exception as e:
        if random.random() < 0.05:  # Giảm log xuống 5% (từ 10%)
            logger.error(f"Lỗi khi truy xuất file vi phạm: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lỗi khi truy xuất file vi phạm: {str(e)}'
        }), 500

@api.route('/confirm_violation', methods=['POST'])
def confirm_violation():
    """Xác nhận vi phạm"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'Không có dữ liệu được gửi'}), 400
        
        violation_id = data.get('violation_id')
        if not violation_id:
            return jsonify({'success': False, 'message': 'Thiếu ID vi phạm'}), 400
        
        # Cập nhật trạng thái vi phạm (trong tương lai có thể lưu vào cơ sở dữ liệu)
        # Trong phiên bản hiện tại, chúng ta chỉ trả về thành công vì vi phạm đã được xác nhận
        
        # Clear cache
        global cache
        cache = {}
        
        # Lấy thông tin chi tiết về vi phạm để gửi lên Discord
        violation_info = None
        if video_processor:
            logger.info(f"Đang lấy thông tin vi phạm ID: {violation_id} để gửi thông báo")
            violation_info = video_processor.get_violation_by_id(violation_id)
            
            if violation_info:
                logger.info(f"Đã lấy được thông tin vi phạm: ID={violation_id}, Biển số={violation_info.get('licensePlate', 'N/A')}")
                
                # Log các URL ảnh và đường dẫn file
                scene_image_path = violation_info.get('scene_image', '')
                scene_image_url = violation_info.get('scene_image_url', '')
                logger.info(f"Ảnh toàn cảnh - Đường dẫn: {scene_image_path}, URL: {scene_image_url}")
                
                vehicle_image_path = violation_info.get('vehicle_image', '')
                vehicle_image_url = violation_info.get('vehicle_image_url', '')
                logger.info(f"Ảnh phương tiện - Đường dẫn: {vehicle_image_path}, URL: {vehicle_image_url}")
                
                # Đảm bảo có URL ảnh
                if not scene_image_url and scene_image_path:
                    violation_info['scene_image_url'] = f"/api/violations/{os.path.basename(scene_image_path)}"
                    logger.info(f"Đã tạo URL ảnh toàn cảnh mới: {violation_info['scene_image_url']}")
            else:
                logger.error(f"Không tìm thấy thông tin chi tiết của vi phạm ID: {violation_id}")
        
        # Gửi thông báo vi phạm lên Discord
        if violation_info:
            try:
                # Chạy hàm bất đồng bộ trong luồng chính
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                logger.info(f"Bắt đầu gửi thông tin vi phạm #{violation_id} lên Discord")
                logger.info(f"URL ảnh sẽ gửi lên Discord: {violation_info.get('scene_image_url', 'Không có')}")
                
                # Gọi hàm gửi thông báo đến Discord
                send_result = loop.run_until_complete(send_violation_to_discord(violation_info))
                
                # Đóng event loop
                loop.close()
                
                if send_result:
                    logger.info(f"Đã gửi thông tin vi phạm #{violation_id} lên Discord thành công")
                else:
                    logger.error(f"Không thể gửi thông tin vi phạm #{violation_id} lên Discord")
            except Exception as discord_err:
                logger.error(f"Lỗi khi gửi thông báo đến Discord: {str(discord_err)}")
                import traceback
                logger.error(traceback.format_exc())
                # Lỗi gửi Discord không ảnh hưởng đến kết quả API
            
            # Gửi thông báo vi phạm lên Telegram
            try:
                logger.info(f"Bắt đầu gửi thông tin vi phạm #{violation_id} lên Telegram")
                
                # Gọi hàm gửi thông báo đến Telegram
                send_result = send_violation_to_telegram(violation_info)
                
                if send_result:
                    logger.info(f"Đã gửi thông tin vi phạm #{violation_id} lên Telegram thành công")
                else:
                    logger.error(f"Không thể gửi thông tin vi phạm #{violation_id} lên Telegram")
            except Exception as telegram_err:
                logger.error(f"Lỗi khi gửi thông báo đến Telegram: {str(telegram_err)}")
                import traceback
                logger.error(traceback.format_exc())
                # Lỗi gửi Telegram không ảnh hưởng đến kết quả API
        else:
            logger.warning(f"Không thể gửi thông báo vì không có thông tin vi phạm ID: {violation_id}")
        
        return jsonify({
            'success': True,
            'message': f'Đã xác nhận vi phạm ID: {violation_id}'
        })
    except Exception as e:
        logger.error(f"Lỗi khi xác nhận vi phạm: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Lỗi khi xác nhận vi phạm: {str(e)}'
        }), 500

@api.route('/reject_violation', methods=['POST'])
def reject_violation():
    """Từ chối vi phạm (xóa khỏi danh sách)"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'Không có dữ liệu được gửi'}), 400
        
        violation_id = data.get('violation_id')
        if not violation_id:
            return jsonify({'success': False, 'message': 'Thiếu ID vi phạm'}), 400
        
        # Xóa vi phạm khỏi danh sách
        result = video_processor.remove_violation(violation_id)
        
        # Clear cache
        global cache
        cache = {}
        
        if result:
            return jsonify({
                'success': True,
                'message': f'Đã loại bỏ vi phạm ID: {violation_id}'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Không tìm thấy vi phạm ID: {violation_id}'
            }), 404
    except Exception as e:
        logger.error(f"Lỗi khi từ chối vi phạm: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lỗi khi từ chối vi phạm: {str(e)}'
        }), 500

@api.route('/add_manual_violation', methods=['POST'])
def add_manual_violation():
    """Thêm vi phạm thủ công"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'Không có dữ liệu được gửi'}), 400
        
        vehicle_type = data.get('vehicle_type', 'car')
        license_plate = data.get('license_plate', 'Không xác định')
        
        # Lấy frame hiện tại
        latest_frame_path = get_latest_frame()
        frame = None
        if latest_frame_path:
            frame = read_frame(os.path.join(PROCESSED_FOLDER, latest_frame_path))
        
        # Thêm vi phạm thủ công
        violation_id = video_processor.add_manual_violation(vehicle_type, license_plate, frame)
        
        # Clear cache
        global cache
        cache = {}
        
        if violation_id:
            return jsonify({
                'success': True,
                'violation_id': violation_id,
                'message': f'Đã thêm vi phạm thủ công với ID: {violation_id}'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Không thể thêm vi phạm thủ công'
            }), 500
    except Exception as e:
        logger.error(f"Lỗi khi thêm vi phạm thủ công: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Lỗi khi thêm vi phạm thủ công: {str(e)}'
        }), 500 