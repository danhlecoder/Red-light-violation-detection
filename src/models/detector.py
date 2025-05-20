"""
Mô hình phát hiện giao thông sử dụng YOLO
"""
import cv2
import numpy as np
from ultralytics import YOLO
from shapely.geometry import Point, Polygon

from src.core.config import logger

class TrafficDetector:
    def __init__(self, model_path):
        """
        Khởi tạo bộ phát hiện giao thông với mô hình YOLO
        
        Tham số:
            model_path: Đường dẫn đến file mô hình YOLO
        """
        # Tải mô hình YOLO
        logger.info(f"Đang tải mô hình YOLO từ {model_path}")
        self.model = YOLO(model_path)
        
        # Tên các lớp trong mô hình
        self.class_names = ['bus', 'car', 'green-light', 'license-plate', 
                           'motorbike', 'red-light', 'truck', 'yellow-light']
        
        # Định nghĩa màu cụ thể cho từng lớp (định dạng BGR)
        self.colors = {
            0: (153, 102, 0),    # bus: nâu
            1: (0, 0, 255),      # car: đỏ
            2: (0, 255, 0),      # green-light: xanh lá
            3: (255, 255, 0),    # license-plate: xanh nhạt
            4: (255, 153, 51),   # motorbike: xanh nhạt
            5: (0, 0, 255),      # red-light: đỏ
            6: (128, 0, 128),    # truck: tím
            7: (0, 255, 255)     # yellow-light: vàng
        }
        
        # Ánh xạ chỉ số lớp sang loại phương tiện
        self.vehicle_classes = {
            0: 'bus',
            1: 'car',
            4: 'motorbike',
            6: 'truck'
        }
        
        # Ánh xạ chỉ số lớp sang trạng thái đèn giao thông
        self.traffic_light_classes = {
            2: 'green',
            5: 'red',
            7: 'yellow'
        }
        
        logger.info("Khởi tạo TrafficDetector thành công")
    
    def process_video(self, video_path, display=True):
        """
        Xử lý luồng video và phát hiện đối tượng
        
        Tham số:
            video_path: Đường dẫn đến file video
            display: Có hiển thị các khung hình đã xử lý hay không
        """
        # Mở video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Lỗi: Không thể mở nguồn video {video_path}")
            return
        
        # Lấy thuộc tính video
        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        logger.info(f"Độ phân giải video gốc: {original_width}x{original_height}, FPS: {fps}")
        logger.info(f"Đang thay đổi kích thước video thành 1280x720")
        
        while True:
            # Đọc khung hình từ video
            ret, frame = cap.read()
            if not ret:
                logger.info("Kết thúc luồng video")
                break
            
            # Thay đổi kích thước khung hình thành 1280x720
            frame = cv2.resize(frame, (1280, 720))
            
            # Thực hiện phát hiện đối tượng
            results = self.model(frame, conf=0.25)
            
            # Xử lý kết quả phát hiện
            processed_frame = self.draw_detections(frame, results[0])
            
            if display:
                # Hiển thị khung hình
                cv2.imshow("Traffic Detection", processed_frame)
                
                # Thoát nếu nhấn phím 'q'
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
        
        # Giải phóng tài nguyên
        cap.release()
        cv2.destroyAllWindows()
    
    def draw_detections(self, frame, results, vehicle_polygon=None):
        """
        Vẽ các hộp giới hạn và nhãn trên khung hình
        
        Tham số:
            frame: Khung hình gốc
            results: Kết quả phát hiện từ mô hình YOLO
            vehicle_polygon: Đa giác giới hạn vùng phát hiện (tùy chọn)
        
        Trả về:
            Khung hình đã chú thích với các hộp giới hạn và nhãn
        """
        # Tạo bản sao của khung hình
        annotated_frame = frame.copy()
        
        # Trích xuất kết quả phát hiện
        boxes = results.boxes.xyxy.cpu().numpy()
        scores = results.boxes.conf.cpu().numpy()
        class_ids = results.boxes.cls.cpu().numpy().astype(int)
        
        # Vẽ các hộp giới hạn và nhãn
        for box, score, class_id in zip(boxes, scores, class_ids):
            x1, y1, x2, y2 = box.astype(int)
            
            # Nếu đa giác được cung cấp, kiểm tra xem đối tượng có nằm trong vùng không
            if vehicle_polygon is not None:
                # Tính toán tâm của đối tượng
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                
                # Bỏ qua đối tượng nếu tâm không nằm trong đa giác
                if not vehicle_polygon.contains(Point(center_x, center_y)):
                    continue
            
            # Lấy màu cho lớp này
            color = self.colors[class_id]
            
            # Vẽ hộp giới hạn với độ rộng giảm (1px thay vì 2px)
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 1)
            
            # Tạo nhãn
            label = f"{self.class_names[class_id]}: {score:.2f}"
            
            # Vẽ nền cho nhãn
            text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(annotated_frame, (x1, y1 - text_size[1] - 5), (x1 + text_size[0], y1), color, -1)
            
            # Vẽ văn bản
            cv2.putText(annotated_frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return annotated_frame
    
    def detect_objects(self, frame, vehicle_polygon=None):
        """
        Phát hiện đối tượng trong khung hình và phân loại chúng
        
        Tham số:
            frame: Khung hình đầu vào
            vehicle_polygon: Đa giác giới hạn vùng phát hiện (tùy chọn)
            
        Trả về:
            vehicles: Danh sách các phương tiện đã phát hiện (x1, y1, x2, y2, class_id, score)
            traffic_lights: Danh sách các đèn giao thông đã phát hiện (x1, y1, x2, y2, class_id, score)
            license_plates: Danh sách các biển số đã phát hiện (x1, y1, x2, y2, score)
        """
        # Thực hiện phát hiện đối tượng
        results = self.model(frame, conf=0.25)
        
        # Trích xuất kết quả phát hiện
        boxes = results[0].boxes.xyxy.cpu().numpy()
        scores = results[0].boxes.conf.cpu().numpy()
        class_ids = results[0].boxes.cls.cpu().numpy().astype(int)
        
        # Phân loại đối tượng
        vehicles = []
        traffic_lights = []
        license_plates = []
        
        for box, score, class_id in zip(boxes, scores, class_ids):
            x1, y1, x2, y2 = box.astype(int)
            
            # Bỏ qua kiểm tra vùng nhận diện nếu không cần thiết
            # Nếu vehicle_polygon được cung cấp và đang trong chế độ kiểm tra vi phạm,
            # thì mới kiểm tra xem đối tượng có nằm trong vùng không
            if vehicle_polygon is not None and isinstance(vehicle_polygon, Polygon):
                # Tính toán tâm của đối tượng
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                
                # Bỏ qua đối tượng nếu tâm không nằm trong đa giác
                if not vehicle_polygon.contains(Point(center_x, center_y)):
                    # Nếu đây là phương tiện và chúng ta đang đếm tất cả các phương tiện,
                    # vẫn thêm vào danh sách vehicles để đếm
                    if class_id in [0, 1, 4, 6]:
                        vehicles.append((x1, y1, x2, y2, class_id, score))
                    continue
            
            # Vehicles: bus(0), car(1), motorbike(4), truck(6)
            if class_id in [0, 1, 4, 6]:
                vehicles.append((x1, y1, x2, y2, class_id, score))
            
            # Traffic lights: green-light(2), red-light(5), yellow-light(7)
            elif class_id in [2, 5, 7]:
                traffic_lights.append((x1, y1, x2, y2, class_id, score))
            
            # License plates: license-plate(3)
            elif class_id == 3:
                license_plates.append((x1, y1, x2, y2, score))
        
        return vehicles, traffic_lights, license_plates 