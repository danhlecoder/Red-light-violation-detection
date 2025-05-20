"""
Dịch vụ xử lý video cho hệ thống giám sát giao thông
"""
import os
import cv2
import time
import threading
import uuid
import queue
from datetime import datetime

from src.core.config import logger, PROCESSED_FOLDER, VIOLATIONS_FOLDER, FRAME_WIDTH, FRAME_HEIGHT
from src.models.detector import TrafficDetector
from src.models.violation_detector import ViolationDetector
from src.utils.video_utils import create_empty_frame, save_frame, clear_processed_frames

class VideoProcessor:
    def __init__(self, model_path):
        """
        Khởi tạo bộ xử lý video
        
        Tham số:
            model_path: Đường dẫn đến file mô hình YOLO
        """
        self.model_path = model_path
        self.current_video_path = None
        self.current_boundaries = None
        self.current_detector = None
        self.current_violations = []
        self.vehicle_counts = {'car': 0, 'motorbike': 0, 'truck': 0, 'bus': 0}
        self.traffic_light_status = 'unknown'  # Mặc định là đèn đỏ
        self.processing_thread = None
        self.is_processing = False
        
        # Lazy loading của detector
        self.global_detector = None
        self.model_loaded = False
        self.model_loading = False
        self.loading_thread = None
        
        # Khởi tạo hàng đợi xử lý frame
        self.frame_queue = queue.Queue(maxsize=30)  # Giới hạn kích thước hàng đợi
        self.processing_workers = []
        self.max_workers = 2  # Số lượng worker xử lý tối đa
        
        logger.info(f"VideoProcessor đã được khởi tạo mà không tải mô hình. Mô hình sẽ được tải khi cần.")
    
    def load_model_async(self):
        """
        Tải mô hình YOLO bất đồng bộ
        """
        if self.model_loading or self.model_loaded:
            return
            
        self.model_loading = True
        self.loading_thread = threading.Thread(target=self._load_model)
        self.loading_thread.daemon = True
        self.loading_thread.start()
    
    def _load_model(self):
        """
        Tải mô hình YOLO vào bộ nhớ
        """
        try:
            logger.info(f"Đang tải mô hình từ {self.model_path}")
            if os.path.exists(self.model_path):
                start_time = time.time()
                self.global_detector = TrafficDetector(self.model_path)
                load_time = time.time() - start_time
                logger.info(f"Đã tải mô hình trong {load_time:.2f} giây")
                self.model_loaded = True
            else:
                logger.error(f"Không tìm thấy file mô hình: {self.model_path}")
                logger.info("Vui lòng đặt mô hình YOLO trong thư mục 'model' với tên 'v5.pt'")
        except Exception as e:
            logger.error(f"Lỗi khi tải mô hình YOLO: {str(e)}")
            logger.error("Ứng dụng sẽ chạy ở chế độ giới hạn không có phát hiện đối tượng")
        finally:
            self.model_loading = False
    
    def ensure_model_loaded(self):
        """
        Đảm bảo mô hình đã được tải trước khi sử dụng
        
        Trả về:
            bool: True nếu mô hình đã tải thành công, False nếu không
        """
        if self.model_loaded and self.global_detector:
            return True
            
        if not self.model_loading:
            # Tải mô hình đồng bộ
            try:
                start_time = time.time()
                logger.info(f"Đang tải mô hình đồng bộ từ: {self.model_path}")
                self.global_detector = TrafficDetector(self.model_path)
                load_time = time.time() - start_time
                logger.info(f"Đã tải mô hình YOLO thành công trong {load_time:.2f} giây")
                self.model_loaded = True
                return True
            except Exception as e:
                logger.error(f"Không thể tải mô hình YOLO: {str(e)}")
                return False
        else:
            # Đợi mô hình tải xong
            if self.loading_thread:
                logger.info("Đang đợi mô hình hoàn tất tải...")
                self.loading_thread.join(timeout=30)  # Đợi tối đa 30 giây
                return self.model_loaded
            return False
    
    def process_video(self, video_path, boundaries=None):
        """
        Xử lý video từng frame một
        
        Tham số:
            video_path: Đường dẫn đến file video
            boundaries: Dữ liệu biên giới cho phát hiện vi phạm (tùy chọn)
        """
        try:
            # Đặt cờ đang xử lý
            self.is_processing = True
            
            # Đảm bảo mô hình đã được tải
            self.ensure_model_loaded()
            
            # Tạo bộ phát hiện vi phạm nếu có dữ liệu biên
            if boundaries and self.global_detector:
                    self.current_detector = ViolationDetector(self.global_detector, boundaries)
            
            # Mở file video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                logger.error(f"Không thể mở video: {video_path}")
                self.is_processing = False
                return
            
            # Lấy thông tin video
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Kiểm tra thông tin video
            if fps <= 0:
                fps = 30  # Giá trị mặc định nếu không đọc được FPS
                logger.warning(f"Không thể đọc FPS từ video, sử dụng giá trị mặc định: {fps}")
            
            # Tính toán khoảng thời gian giữa các frame (ms)
            frame_interval = 1000.0 / fps
            
            # Thiết lập tốc độ phát lại (1.0 = tốc độ thực)
            playback_speed = 1.0
            
            # Biến đếm frame và thời gian
            frame_count = 0
            processed_frames = 0
            previous_frame_time = time.time() * 1000  # ms
            
            # Tối ưu: Chỉ xử lý 1 frame trong mỗi N frame để giảm tải
            process_every_n_frames = 5  # Giảm xuống 5 để xử lý nhiều frame hơn (trước đây là 3)
            
            # Tối ưu: Giữ nguyên kích thước frame để chất lượng cao hơn
            scale_factor = 1.0  # Không giảm kích thước nữa (trước đây là 0.75)
            
            # Vòng lặp xử lý video
            while self.is_processing:
                # Đọc frame từ video
                ret, frame = cap.read()
                
                # Nếu không đọc được frame, có thể đã hết video
                if not ret:
                    logger.warning("Đã đọc hết video hoặc có lỗi khi đọc frame")
                    break
                
                try:
                    # Tính thời gian hiện tại
                    current_frame_time = time.time() * 1000  # ms
                    
                    # Chỉ xử lý 1 frame trong mỗi N frame để giảm tải
                    should_process = frame_count % process_every_n_frames == 0
                    
                    if should_process:
                        # Tăng chất lượng ảnh bằng cách giữ nguyên kích thước
                        # Nếu cần, resize lên kích thước lớn hơn để tăng chất lượng
                        target_width = FRAME_WIDTH
                        target_height = FRAME_HEIGHT
                        
                        # Chỉ resize nếu kích thước hiện tại nhỏ hơn kích thước mục tiêu
                        if frame.shape[1] < target_width or frame.shape[0] < target_height:
                            # Tính tỷ lệ để giữ nguyên aspect ratio
                            ratio = min(target_width / frame.shape[1], target_height / frame.shape[0])
                            new_width = int(frame.shape[1] * ratio)
                            new_height = int(frame.shape[0] * ratio)
                            
                            # Resize frame với chất lượng cao (INTER_CUBIC)
                            frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
                        
                        # Bắt đầu đo thời gian xử lý
                        start_time = time.time() * 1000  # ms
                        
                        # Xử lý frame với detector
                        if self.current_detector:
                            if isinstance(self.current_detector, ViolationDetector):
                                # Sử dụng ViolationDetector để xử lý frame
                                annotated_frame, vehicle_counts, traffic_light_status, new_violations = self.current_detector.process_frame(frame)
                                
                                # Cập nhật thông tin
                                self.vehicle_counts = vehicle_counts
                                self.traffic_light_status = traffic_light_status
                                
                                # Thêm vi phạm mới vào danh sách
                                if new_violations:
                                    self.current_violations.extend(new_violations)
                                    # Giới hạn số lượng vi phạm lưu trữ để tiết kiệm bộ nhớ
                                    if len(self.current_violations) > 100:
                                        # Chỉ giữ lại 100 vi phạm mới nhất
                                        self.current_violations = self.current_violations[-100:]
                            else:
                                # Sử dụng detector thông thường để phát hiện đối tượng
                                # Phát hiện tất cả các phương tiện trong khung hình mà không cần vùng nhận diện
                                vehicles, traffic_lights, license_plates = self.global_detector.detect_objects(frame)
                                
                                # Đếm số lượng phương tiện theo loại
                                vehicle_counts = {
                                    'car': 0,
                                    'motorbike': 0,
                                    'truck': 0,
                                    'bus': 0
                                }
                                
                                # Đếm số lượng phương tiện
                                for _, _, _, _, class_id, _ in vehicles:
                                    if class_id == 1:  # car
                                        vehicle_counts['car'] += 1
                                    elif class_id == 4:  # motorbike
                                        vehicle_counts['motorbike'] += 1
                                    elif class_id == 6:  # truck
                                        vehicle_counts['truck'] += 1
                                    elif class_id == 0:  # bus
                                        vehicle_counts['bus'] += 1
                                
                                # Cập nhật số lượng phương tiện
                                self.vehicle_counts = vehicle_counts
                                
                                # Xác định trạng thái đèn giao thông
                                light_counts = {'red': 0, 'yellow': 0, 'green': 0}
                                for _, _, _, _, class_id, _ in traffic_lights:
                                    if class_id == 5:  # red-light
                                        light_counts['red'] += 1
                                    elif class_id == 7:  # yellow-light
                                        light_counts['yellow'] += 1
                                    elif class_id == 2:  # green-light
                                        light_counts['green'] += 1
                                
                                # Xác định trạng thái đèn dựa trên số lượng
                                max_count = 0
                                max_light = 'unknown'
                                for light_type, count in light_counts.items():
                                    if count > max_count:
                                        max_count = count
                                        max_light = light_type
                                
                                # Cập nhật trạng thái đèn giao thông nếu có phát hiện
                                if max_count > 0:
                                    self.traffic_light_status = max_light
                                
                                # Vẽ kết quả phát hiện lên frame
                                annotated_frame = self.global_detector.draw_detections(frame, self.global_detector.model(frame)[0])
                                
                                # Hiển thị trạng thái đèn giao thông
                                light_color = (255, 255, 255)  # Màu mặc định (trắng)
                                if self.traffic_light_status == 'red':
                                    light_color = (0, 0, 255)  # Đỏ
                                elif self.traffic_light_status == 'yellow':
                                    light_color = (0, 255, 255)  # Vàng
                                elif self.traffic_light_status == 'green':
                                    light_color = (0, 255, 0)  # Xanh
                                
                                cv2.putText(annotated_frame, f"Đèn: {self.traffic_light_status.upper()}", (10, 30), 
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, light_color, 2)
                                
                                # Giảm log thông tin phát hiện (mỗi 100 frame thay vì 30)
                                if processed_frames % 100 == 0:
                                    logger.info(f"Phát hiện: Ô tô={vehicle_counts['car']}, Xe máy={vehicle_counts['motorbike']}, "
                                                f"Xe tải={vehicle_counts['truck']}, Xe buýt={vehicle_counts['bus']}, "
                                                f"Đèn giao thông={self.traffic_light_status}")
                        else:
                            # Nếu không có detector, chỉ hiển thị frame gốc
                            annotated_frame = frame
                        
                        # Lưu frame đã xử lý với chất lượng cao hơn
                        frame_path = f"frame_{frame_count % 30}.jpg"
                        # Lưu với chất lượng cao hơn (100 thay vì mặc định 75)
                        cv2.imwrite(os.path.join(PROCESSED_FOLDER, frame_path), annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 100])
                        
                        # Tính thời gian xử lý
                        process_time = time.time() * 1000 - start_time  # ms
                        
                        processed_frames += 1
                        
                        # Giảm log để tránh làm chậm hệ thống
                        if processed_frames % 100 == 0:  # Chỉ log mỗi 100 frame được xử lý thay vì 30
                            logger.info(f"Đã xử lý {processed_frames} frames, thời gian xử lý frame hiện tại: {process_time:.1f}ms")
                    else:
                        # Nếu không xử lý frame này, vẫn cập nhật thời gian xử lý để tính toán delay
                        process_time = 0
                    
                    # Tính toán thời gian cần delay để duy trì tốc độ phát đúng
                    target_delay = (frame_interval / playback_speed) - process_time
                    
                    # Đợi để duy trì tốc độ phát chính xác
                    if target_delay > 0:
                        time.sleep(target_delay / 1000.0)  # Chuyển đổi ms sang giây
                        # Giảm log
                        if frame_count % 100 == 0 and should_process:  # Giảm từ 30 xuống 100 frame
                            logger.info(f"Frame {frame_count}: process_time={process_time:.1f}ms, delay={target_delay:.1f}ms")
                    else:
                        # Nếu xử lý quá chậm, ghi log
                        if frame_count % 100 == 0 and should_process:  # Giảm từ 30 xuống 100 frame
                            logger.info(f"Frame {frame_count}: process_time={process_time:.1f}ms, không cần delay")
                    
                    # Cập nhật thời gian frame trước đó
                    previous_frame_time = current_frame_time
                    
                    # Tăng biến đếm frame
                    frame_count += 1
                    
                except Exception as e:
                    # Giảm log lỗi
                    if frame_count % 50 == 0:  # Giảm từ 10 xuống 50 frame
                        logger.error(f"Lỗi xử lý frame {frame_count}: {str(e)}")
                    # Tạo frame báo lỗi
                    error_frame = create_empty_frame(message=f"Lỗi: {str(e)}")
                    save_frame(error_frame, f"frame_{frame_count % 30}.jpg")
                    frame_count += 1
            
            cap.release()
            logger.warning(f"Xử lý video kết thúc. Tổng số frame đã xử lý: {processed_frames}")
            
        except Exception as e:
            logger.error(f"Lỗi xử lý video: {str(e)}")
            error_frame = create_empty_frame(message=f"Lỗi: {str(e)}")
            save_frame(error_frame, "frame_error.jpg")
        finally:
            self.is_processing = False
            logger.info("Xử lý video hoàn tất")
            
            # Giải phóng bộ nhớ
            import gc
            gc.collect()
    
    def start_processing(self, video_path, boundaries=None):
        """
        Bắt đầu xử lý video trong một luồng riêng biệt
        
        Tham số:
            video_path: Đường dẫn đến file video
            boundaries: Dữ liệu biên giới (tùy chọn)
            
        Trả về:
            bool: True nếu bắt đầu xử lý thành công, False nếu không
        """
        # Kiểm tra xem video_path có tồn tại không
        if not os.path.exists(video_path):
            logger.error(f"Không thể tìm thấy file video: {video_path}")
            return False
        
        # Dừng xử lý hiện tại nếu có
        if self.is_processing:
            logger.info("Đang dừng video hiện tại trước khi bắt đầu video mới")
            self.stop_processing()
            # Thêm một khoảng thời gian nhỏ để đảm bảo tài nguyên được giải phóng
            time.sleep(0.5)
        
        # Reset dữ liệu
        logger.info(f"Bắt đầu xử lý video mới: {video_path}")
        self.current_violations = []
        self.vehicle_counts = {'car': 0, 'motorbike': 0, 'truck': 0, 'bus': 0}
        self.current_video_path = video_path
        self.current_boundaries = boundaries
        
        # Xóa các frame cũ trước khi bắt đầu video mới
        clear_processed_frames()
        
        # Đảm bảo model được tải (hoặc bắt đầu tải nếu chưa)
        if not self.model_loaded and not self.model_loading:
            self.load_model_async()
        
        # Tạo và bắt đầu thread xử lý
        self.processing_thread = threading.Thread(target=self.process_video, args=(video_path, boundaries))
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info(f"Đã bắt đầu thread xử lý video: {video_path}")
        return True
    
    def stop_processing(self):
        """
        Dừng xử lý video
        
        Trả về:
            bool: True nếu xử lý đã được dừng, False nếu không có xử lý nào đang chạy
        """
        if self.is_processing and self.processing_thread and self.processing_thread.is_alive():
            # Đặt cờ dừng xử lý
            logger.info("Đang dừng xử lý video...")
            self.is_processing = False
            
            # Đợi thread xử lý kết thúc với thời gian chờ dài hơn
            self.processing_thread.join(timeout=5)
            
            # Kiểm tra xem thread đã thực sự dừng chưa
            if self.processing_thread.is_alive():
                logger.warning("Thread xử lý video vẫn đang chạy sau khi timeout, có thể gây ra vấn đề khi tải video mới")
                # Không thể kill thread trong Python, nhưng chúng ta đã đặt cờ is_processing = False
                # để thread sẽ tự kết thúc trong lần lặp tiếp theo
            else:
                logger.info("Thread xử lý video đã dừng thành công")
            
            # Đảm bảo giải phóng tài nguyên
            self.processing_thread = None
            return True
        
        logger.info("Không có video nào đang được xử lý")
        return False
    
    def update_boundaries(self, boundaries):
        """
        Cập nhật biên giới mà không cần khởi động lại quá trình xử lý video
        
        Args:
            boundaries: Dữ liệu biên mới
            
        Returns:
            bool: True nếu biên được cập nhật thành công, False nếu không
        """
        self.current_boundaries = boundaries
        
        # Cập nhật biên trong bộ phát hiện vi phạm nếu đang hoạt động
        if self.current_detector is not None and isinstance(self.current_detector, ViolationDetector):
            try:
                self.current_detector.update_boundaries(boundaries)
                logger.info("Đã cập nhật biên trong bộ phát hiện hiện tại")
                return True
            except Exception as e:
                logger.error(f"Lỗi khi cập nhật biên: {str(e)}")
                return False
        
        return False
    
    def get_stats(self):
        """
        Lấy thống kê hiện tại
        
        Trả về:
            dict: Thống kê hiện tại (số lượng phương tiện, trạng thái đèn giao thông, số lượng vi phạm)
        """
        # Ghi log để debug
        logger.debug(f"Đang trả về thống kê: Phương tiện={self.vehicle_counts}, Đèn={self.traffic_light_status}, Vi phạm={len(self.current_violations)}")
        
        # Chuyển đổi trạng thái đèn sang tiếng Việt
        light_status_vi = "KHÔNG XÁC ĐỊNH"
        if self.traffic_light_status == 'red':
            light_status_vi = "ĐỎ"
        elif self.traffic_light_status == 'yellow':
            light_status_vi = "VÀNG"
        elif self.traffic_light_status == 'green':
            light_status_vi = "XANH"
        
        # Tạo dict mới với các giá trị đã được chuyển đổi thành kiểu dữ liệu Python chuẩn
        safe_vehicle_counts = {}
        for vehicle_type, count in self.vehicle_counts.items():
            # Chuyển đổi giá trị từ NumPy sang Python native types nếu cần
            if hasattr(count, 'item'):
                safe_vehicle_counts[vehicle_type] = count.item()
            else:
                safe_vehicle_counts[vehicle_type] = int(count) if isinstance(count, float) else count
        
        # Tính tổng số phương tiện
        total_vehicles = sum(safe_vehicle_counts.values())
        
        return {
            'vehicle_counts': safe_vehicle_counts, 
            'total_vehicles': int(total_vehicles),
            'traffic_light_status': self.traffic_light_status,
            'traffic_light_status_vi': light_status_vi,
            'violation_count': len(self.current_violations),
            'timestamp': int(time.time() * 1000)  # Thêm timestamp để tránh cache trình duyệt
        }
    
    def get_violations(self, page=1, per_page=10):
        """
        Lấy danh sách vi phạm có phân trang
        
        Tham số:
            page: Số trang (bắt đầu từ 1)
            per_page: Số lượng mục trên mỗi trang
            
        Trả về:
            dict: Danh sách vi phạm đã phân trang và metadata
        """
        try:
            # Tính toán phân trang
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            
            # Đảm bảo các chỉ số hợp lệ
            if start_idx < 0:
                start_idx = 0
            if end_idx > len(self.current_violations):
                end_idx = len(self.current_violations)
            
            # Lấy các vi phạm cho trang hiện tại
            paginated_violations = self.current_violations[start_idx:end_idx]
            
            # Tối ưu: Chỉ chuyển đổi đường dẫn ảnh thành URL khi cần thiết
            processed_violations = []
            for violation in paginated_violations:
                # Tạo bản sao nhẹ của vi phạm để không thay đổi dữ liệu gốc
                processed_violation = {
                    'id': violation.get('id', ''),
                    'timestamp': violation.get('timestamp', ''),
                    'vehicleType': violation.get('vehicleType', ''),
                    'licensePlate': violation.get('licensePlate', 'Không xác định'),
                    'violation_type': violation.get('violation_type', 'Vượt đèn đỏ'),
                    'direction': violation.get('direction', 'Không xác định')
                }
                
                # Đảm bảo confidence là kiểu dữ liệu Python có thể serialize
                if 'confidence' in violation:
                    confidence = violation['confidence']
                    if hasattr(confidence, 'item'):
                        processed_violation['confidence'] = float(confidence.item())
                    elif isinstance(confidence, (float, int)):
                        processed_violation['confidence'] = float(confidence)
                    else:
                        processed_violation['confidence'] = 0.0
                else:
                    processed_violation['confidence'] = 0.0
                
                # Chuyển đổi đường dẫn ảnh thành URL tương đối
                if 'scene_image' in violation and violation['scene_image']:
                    processed_violation['scene_image_url'] = f"/api/violations/{os.path.basename(violation['scene_image'])}"
                
                if 'vehicle_image' in violation and violation['vehicle_image']:
                    processed_violation['vehicle_image_url'] = f"/api/violations/{os.path.basename(violation['vehicle_image'])}"
                
                if 'license_plate_image' in violation and violation['license_plate_image']:
                    processed_violation['license_plate_image_url'] = f"/api/violations/{os.path.basename(violation['license_plate_image'])}"
                
                processed_violations.append(processed_violation)
            
            return {
                'violations': processed_violations,
                'total': len(self.current_violations),
                'page': page,
                'per_page': per_page,
                'total_pages': max(1, (len(self.current_violations) + per_page - 1) // per_page)
            }
        except Exception as e:
            logger.error(f"Lỗi khi lấy dữ liệu vi phạm: {str(e)}")
            return {
                'violations': [],
                'total': 0,
                'page': page,
                'per_page': per_page,
                'total_pages': 0,
                'error': str(e)
            }
    
    def add_manual_violation(self, vehicle_type, license_plate, frame):
        """
        Thêm vi phạm thủ công
        
        Args:
            vehicle_type: Loại phương tiện ("car", "motorbike", "truck", "bus")
            license_plate: Biển số xe
            frame: Khung hình vi phạm (nếu có)
            
        Returns:
            violation_id: ID của vi phạm đã tạo
        """
        try:
            # Lấy số lượng vi phạm hiện tại để tạo mã tự tăng
            violation_count = len(self.current_violations)
            # Tạo ID dạng số từ 00001 đến 99999
            violation_id = str(violation_count + 1).zfill(5)
            
            # Đảm bảo ID không bị trùng
            existing_ids = {v.get('id', '') for v in self.current_violations}
            while violation_id in existing_ids:
                violation_count += 1
                violation_id = str(violation_count + 1).zfill(5)
            
            # Lấy thời gian hiện tại
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Tạo thư mục cho vi phạm nếu chưa tồn tại
            if not os.path.exists(VIOLATIONS_FOLDER):
                os.makedirs(VIOLATIONS_FOLDER)
                
            # Lưu ảnh vi phạm
            scene_img_path = None
            if frame is not None:
                scene_img_path = os.path.join(VIOLATIONS_FOLDER, f"violation_{violation_id}_scene.jpg")
                cv2.imwrite(scene_img_path, frame)
            
            # Tạo vi phạm mới
            violation = {
                'id': violation_id,
                'timestamp': timestamp,
                'vehicleType': vehicle_type,
                'licensePlate': license_plate if license_plate else "Không xác định",
                'confidence': 1.0,  # Vi phạm thủ công có độ tin cậy cao
                'violation_type': 'Vượt đèn đỏ',
                'scene_image': scene_img_path,
                'direction': 'Thêm thủ công',
                'is_manual': True  # Đánh dấu là vi phạm thủ công
            }
            
            # Thêm vào danh sách vi phạm
            self.current_violations.append(violation)
            
            # Ghi log
            logger.info(f"Đã thêm vi phạm thủ công: ID={violation_id}, Loại phương tiện={vehicle_type}, Biển số={license_plate}")
            
            return violation_id
        except Exception as e:
            logger.error(f"Lỗi khi thêm vi phạm thủ công: {str(e)}")
            return None
            
    def remove_violation(self, violation_id):
        """
        Xóa vi phạm khỏi danh sách
        
        Args:
            violation_id: ID của vi phạm cần xóa
            
        Returns:
            bool: True nếu xóa thành công, False nếu không tìm thấy
        """
        try:
            # Tìm vi phạm trong danh sách
            for i, violation in enumerate(self.current_violations):
                if violation.get('id') == violation_id:
                    # Xóa vi phạm
                    del self.current_violations[i]
                    logger.info(f"Đã xóa vi phạm: ID={violation_id}")
                    return True
            
            logger.warning(f"Không tìm thấy vi phạm với ID={violation_id}")
            return False
        except Exception as e:
            logger.error(f"Lỗi khi xóa vi phạm: {str(e)}")
            return False 
    
    def start_processing_workers(self, num_workers=2):
        """
        Khởi động các worker cho việc xử lý frame song song
        
        Args:
            num_workers: Số lượng worker cần khởi động
        """
        self.max_workers = min(num_workers, 4)  # Giới hạn tối đa 4 worker
        
        for _ in range(self.max_workers):
            worker = threading.Thread(target=self._process_frame_worker)
            worker.daemon = True
            worker.start()
            self.processing_workers.append(worker)
            
        logger.info(f"Đã khởi động {self.max_workers} worker xử lý frame")
    
    def _process_frame_worker(self):
        """
        Worker thread xử lý các frame từ hàng đợi
        """
        while True:
            try:
                # Lấy frame từ hàng đợi
                frame, frame_idx, boundaries = self.frame_queue.get(timeout=5)
                
                # Xử lý frame
                if self.global_detector:
                    # Thực hiện xử lý frame ở đây
                    # ... 
                    
                    # Đánh dấu công việc hoàn thành
                    self.frame_queue.task_done()
            except queue.Empty:
                # Không có frame trong hàng đợi, đợi thêm
                time.sleep(0.1)
                continue
            except Exception as e:
                logger.error(f"Lỗi trong worker xử lý frame: {str(e)}")
                # Đánh dấu công việc hoàn thành để tránh block hàng đợi
                self.frame_queue.task_done()
    
    def preload_model(self):
        """
        Tải trước mô hình YOLO vào bộ nhớ nếu cần
        """
        if not self.model_loaded and not self.model_loading:
            logger.info("Đang tải trước mô hình trong nền...")
            self.load_model_async()
    
    def get_violation_by_id(self, violation_id):
        """
        Lấy thông tin chi tiết về một vi phạm dựa theo ID
        
        Args:
            violation_id: ID của vi phạm cần tìm
            
        Returns:
            dict: Thông tin chi tiết về vi phạm, hoặc None nếu không tìm thấy
        """
        try:
            # Tìm vi phạm theo ID
            for violation in self.current_violations:
                if str(violation.get('id')) == str(violation_id):
                    # Tạo bản sao để không thay đổi dữ liệu gốc
                    violation_copy = dict(violation)
                    
                    # Thêm trường status nếu chưa có
                    if 'status' not in violation_copy:
                        violation_copy['status'] = 'Đã xác nhận'
                    
                    # Kiểm tra và chuyển đổi đường dẫn ảnh thành URL đầy đủ
                    # Chỉ tạo URL nếu chưa có URL sẵn
                    if 'scene_image' in violation_copy and violation_copy['scene_image'] and 'scene_image_url' not in violation_copy:
                        scene_image_path = violation_copy['scene_image']
                        violation_copy['scene_image_url'] = f"/api/violations/{os.path.basename(scene_image_path)}"
                        logger.info(f"Đã tạo URL ảnh toàn cảnh: {violation_copy['scene_image_url']}")
                    
                    if 'vehicle_image' in violation_copy and violation_copy['vehicle_image'] and 'vehicle_image_url' not in violation_copy:
                        vehicle_image_path = violation_copy['vehicle_image']
                        violation_copy['vehicle_image_url'] = f"/api/violations/{os.path.basename(vehicle_image_path)}"
                        logger.info(f"Đã tạo URL ảnh phương tiện: {violation_copy['vehicle_image_url']}")
                    
                    if 'license_plate_image' in violation_copy and violation_copy['license_plate_image'] and 'license_plate_image_url' not in violation_copy:
                        plate_image_path = violation_copy['license_plate_image']
                        violation_copy['license_plate_image_url'] = f"/api/violations/{os.path.basename(plate_image_path)}"
                        logger.info(f"Đã tạo URL ảnh biển số: {violation_copy['license_plate_image_url']}")
                    
                    logger.info(f"Trả về thông tin vi phạm {violation_id} với URL ảnh: {violation_copy.get('scene_image_url', 'Không có')}")
                    return violation_copy
            
            # Không tìm thấy vi phạm
            logger.warning(f"Không tìm thấy vi phạm với ID: {violation_id}")
            return None
            
        except Exception as e:
            logger.error(f"Lỗi khi tìm vi phạm theo ID {violation_id}: {str(e)}")
            return None 