"""
Traffic violation detection module
"""
import cv2
import numpy as np
from datetime import datetime
from shapely.geometry import Point, Polygon, LineString
import uuid
import os
import traceback
import math

from src.core.config import logger, FRAME_WIDTH, FRAME_HEIGHT, VIOLATIONS_FOLDER

class ViolationDetector:
    def __init__(self, traffic_detector, boundaries):
        """
        Initialize violation detector based on drawn boundaries
        
        Args:
            traffic_detector: Initialized TrafficDetector object
            boundaries: Boundary data (line, vehiclePolygon, trafficLightPolygon)
        """
        self.detector = traffic_detector
        self.boundaries = boundaries
        
        # Standard dimensions for processing
        self.frame_width = FRAME_WIDTH
        self.frame_height = FRAME_HEIGHT
        
        # Convert boundary data to Shapely objects
        self.line = None
        self.vehicle_polygon = None
        self.traffic_light_polygon = None
        
        if 'line' in boundaries and len(boundaries['line']) >= 2:
            points = [(p['x'] * self.frame_width, p['y'] * self.frame_height) for p in boundaries['line']]
            # Log tọa độ vạch dừng để kiểm tra
            logger.info(f"KHỞI TẠO: Tọa độ vạch dừng gốc: {points}")
            
            # Đảm bảo vạch dừng được định nghĩa từ trái sang phải
            if points[0][0] > points[1][0]:
                points = [points[1], points[0]]
                logger.info(f"KHỞI TẠO: Đã đổi chiều vạch dừng: {points}")
            
            self.line = LineString(points)
        
        if 'vehiclePolygon' in boundaries and len(boundaries['vehiclePolygon']) >= 3:
            points = [(p['x'] * self.frame_width, p['y'] * self.frame_height) for p in boundaries['vehiclePolygon']]
            self.vehicle_polygon = Polygon(points)
            logger.info(f"KHỞI TẠO: Tọa độ đa giác phương tiện: {points}")
        
        if 'trafficLightPolygon' in boundaries and len(boundaries['trafficLightPolygon']) >= 3:
            points = [(p['x'] * self.frame_width, p['y'] * self.frame_height) for p in boundaries['trafficLightPolygon']]
            self.traffic_light_polygon = Polygon(points)
            logger.info(f"KHỞI TẠO: Tọa độ đa giác đèn giao thông: {points}")
        
        # Store state
        self.current_light_status = 'unknown'  # unknown, red, yellow, green
        self.tracked_vehicles = {}  # {id: {position_history, crossed_line, vehicle_type}}
        self.next_vehicle_id = 1
        self.violations = []  # List of violations
        
        # Vehicle counts
        self.vehicle_counts = {
            'car': 0,
            'motorbike': 0,
            'truck': 0,
            'bus': 0
        }
        
        logger.info("ViolationDetector initialized successfully")
    
    def process_frame(self, frame):
        """
        Process frame and detect violations
        
        Args:
            frame: Input frame
            
        Returns:
            annotated_frame: Annotated frame
            vehicle_counts: Vehicle counts by type
            current_light_status: Current traffic light status
            new_violations: New violations detected in this frame
        """
        # Ensure frame has the correct dimensions to match boundary coordinates
        current_height, current_width = frame.shape[:2]
        if current_width != self.frame_width or current_height != self.frame_height:
            frame = cv2.resize(frame, (self.frame_width, self.frame_height))
        
        # Create a copy of the frame
        annotated_frame = frame.copy()
        
        # Perform object detection on the entire frame
        results = self.detector.model(frame, conf=0.25)
        
        # Extract detection results
        boxes = results[0].boxes.xyxy.cpu().numpy()
        scores = results[0].boxes.conf.cpu().numpy()
        class_ids = results[0].boxes.cls.cpu().numpy().astype(int)
        
        # Create lists of filtered objects
        filtered_vehicles = []
        filtered_traffic_lights = []
        filtered_license_plates = []
        
        # Đếm tất cả các phương tiện trong frame, không chỉ trong vùng được vẽ
        all_vehicles = []
        
        # Filter objects based on position in detection zones and count all vehicles
        for box, score, class_id in zip(boxes, scores, class_ids):
            x1, y1, x2, y2 = box.astype(int)
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            center_point = Point(center_x, center_y)
            
            # Đếm tất cả phương tiện trong frame
            if class_id in [0, 1, 4, 6]:  # bus, car, motorbike, truck
                all_vehicles.append((x1, y1, x2, y2, class_id, score))
            
            # Kiểm tra nếu đối tượng nằm trong vùng phát hiện
            in_detection_zone = False
            
            # Check vehicle_polygon (blue)
            if self.vehicle_polygon and self.vehicle_polygon.contains(center_point):
                in_detection_zone = True
            
            # Check traffic_light_polygon (green)
            if not in_detection_zone and self.traffic_light_polygon and self.traffic_light_polygon.contains(center_point):
                in_detection_zone = True
            
            # Skip object if not in detection zone
            if not in_detection_zone:
                continue
            
            # Classify object into appropriate list
            if class_id in [0, 1, 4, 6]:  # bus, car, motorbike, truck
                filtered_vehicles.append((x1, y1, x2, y2, class_id, score))
            elif class_id in [2, 5, 7]:  # green-light, red-light, yellow-light
                filtered_traffic_lights.append((x1, y1, x2, y2, class_id, score))
            elif class_id == 3:  # license-plate
                filtered_license_plates.append((x1, y1, x2, y2, score))
        
        # Update traffic light status
        self.update_traffic_light_status(filtered_traffic_lights)
        
        # Draw defined boundaries
        self.draw_boundaries(annotated_frame)
        
        # Track vehicles and detect violations - only use filtered vehicles
        new_violations = self.track_vehicles_and_detect_violations(filtered_vehicles, annotated_frame)
        
        # Draw detection results
        annotated_frame = self.draw_results(annotated_frame, filtered_vehicles, filtered_traffic_lights, filtered_license_plates)
        
        # Cập nhật số lượng phương tiện dựa trên tất cả phương tiện phát hiện được
        self.update_vehicle_counts(all_vehicles)
        
        return annotated_frame, self.vehicle_counts, self.current_light_status, new_violations
    
    def update_traffic_light_status(self, traffic_lights):
        """
        Update traffic light status based on detected lights
        
        Args:
            traffic_lights: List of detected traffic lights
        """
        # If no traffic lights detected, keep previous status
        if not traffic_lights:
            # Nếu không phát hiện đèn, giữ nguyên trạng thái trước đó thay vì đặt thành unknown
            return
        
        # Count each type of light
        light_counts = {
            'red': 0,
            'yellow': 0,
            'green': 0
        }
        
        # Debug log
        light_classes = []
        
        for light in traffic_lights:
            _, _, _, _, class_id, score = light
            light_classes.append((class_id, score))
            
            # Sửa lại mapping class_id với trạng thái đèn
            if class_id == 5:  # red-light
                light_counts['red'] += 1
            elif class_id == 7:  # yellow-light
                light_counts['yellow'] += 1
            elif class_id == 2:  # green-light
                light_counts['green'] += 1
        
        # Log để debug
        logger.debug(f"Phát hiện đèn giao thông: {light_classes}, counts: {light_counts}")
        
        # Determine light status based on counts
        max_count = 0
        max_light = 'unknown'
        
        for light_type, count in light_counts.items():
            if count > max_count:
                max_count = count
                max_light = light_type
        
        # Update light status
        if max_count > 0:
            # Chỉ cập nhật nếu có sự thay đổi để tránh nhấp nháy
            if self.current_light_status != max_light:
                logger.info(f"Trạng thái đèn giao thông thay đổi từ {self.current_light_status} thành {max_light}")
                self.current_light_status = max_light
    
    def track_vehicles_and_detect_violations(self, vehicles, frame):
        """
        Theo dõi phương tiện và phát hiện vi phạm
        
        Args:
            vehicles: Danh sách các phương tiện được phát hiện
            frame: Khung hình hiện tại
            
        Returns:
            new_violations: Danh sách vi phạm mới phát hiện trong khung hình này
        """
        try:
            new_violations = []
            
            # Nếu không có đường thẳng hoặc không có vùng phát hiện phương tiện, không thể phát hiện vi phạm
            if not self.line or not self.vehicle_polygon:
                return new_violations
            
            # Đảm bảo trạng thái đèn là đỏ trước khi phát hiện vi phạm
            if self.current_light_status != 'red':
                # Chỉ theo dõi, không phát hiện vi phạm khi đèn không phải màu đỏ
                self.update_vehicle_tracking(vehicles, frame)
                return new_violations
            
            # Lấy kích thước khung hình để tỉ lệ
            frame_height, frame_width = frame.shape[:2]
            
            # Lấy danh sách biển số xe được phát hiện trong frame hiện tại
            _, _, license_plates = self.detector.detect_objects(frame)
            
            # Tạo một bản sao của frame để vẽ thông tin vi phạm
            violation_frame = frame.copy()
            
            # Lấy tọa độ của vạch dừng
            try:
                line_coords = list(self.line.coords)
                if len(line_coords) < 2:
                    logger.error("Tọa độ vạch dừng không hợp lệ")
                    return new_violations
                    
                # In ra tọa độ thô của vạch dừng để kiểm tra
                logger.info(f"Tọa độ vạch dừng gốc (chưa xử lý): {line_coords}")
                
                # Đảm bảo tọa độ nằm trong giới hạn của frame
                line_start_x = max(0, min(int(line_coords[0][0]), frame_width - 1))
                line_start_y = max(0, min(int(line_coords[0][1]), frame_height - 1))
                line_end_x = max(0, min(int(line_coords[1][0]), frame_width - 1))
                line_end_y = max(0, min(int(line_coords[1][1]), frame_height - 1))
                
                # In ra tọa độ đã xử lý để kiểm tra
                logger.info(f"Tọa độ vạch dừng sau khi xử lý: ({line_start_x}, {line_start_y}) -> ({line_end_x}, {line_end_y})")
                
                line_start = (line_start_x, line_start_y)
                line_end = (line_end_x, line_end_y)
                
                # Vẽ vạch dừng lên frame để kiểm tra trực quan
                cv2.line(violation_frame, line_start, line_end, (0, 0, 255), 3)
                
                # Vẽ thêm vạch biên an toàn để kiểm tra
                clear_violation_margin = 15  # 15 pixel
                if line_start_y == line_end_y:  # Vạch ngang
                    safe_line_y = line_start_y + clear_violation_margin
                    cv2.line(violation_frame, (line_start_x, safe_line_y), (line_end_x, safe_line_y), (255, 0, 0), 1)
            except Exception as e:
                logger.error(f"Lỗi khi xử lý tọa độ vạch dừng: {str(e)}")
                return new_violations
            
            # Xác định hướng của vạch (ngang hay dọc)
            is_horizontal = abs(line_coords[0][1] - line_coords[1][1]) < abs(line_coords[0][0] - line_coords[1][0])
            
            # Chỉ phát hiện vi phạm trên vạch ngang
            if not is_horizontal:
                logger.info("Chỉ phát hiện vi phạm trên vạch ngang, bỏ qua vạch dọc")
                return new_violations
            
            # Lấy vị trí của vạch (tọa độ y cho vạch ngang)
            line_pos = min(line_coords[0][1], line_coords[1][1])
            
            # Log tọa độ vạch dừng
            logger.info(f"Vạch dừng ngang có tọa độ y = {line_pos}")
            
            # Theo dõi phương tiện hiện tại
            current_vehicles = {}
            
            # Sử dụng set để lưu ID của phương tiện đã được kiểm tra vi phạm
            checked_violation_ids = set()
            
            # PHẦN 1: PHÁT HIỆN VI PHẠM TRỰC TIẾP - kiểm tra tất cả phương tiện trong frame hiện tại
            # Kiểm tra từng phương tiện xem có vượt qua vạch không
            for vehicle in vehicles:
                try:
                    x1, y1, x2, y2, class_id, score = vehicle
                    
                    # Tính toán tâm của phương tiện
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    
                    # Kiểm tra điều kiện vi phạm:
                    # 1. Trạng thái đèn là đỏ (đã kiểm tra ở trên)
                    # 2. Phương tiện trong vùng giám sát (kiểm tra bằng vehicle_polygon)
                    # 3. Phần DƯỚI của phương tiện (y2) đã vượt qua vạch dừng ngang - phương tiện đã hoàn toàn vượt qua vạch
                    
                    # Kiểm tra phương tiện có nằm trong vùng giám sát không
                    vehicle_center_point = Point(center_x, center_y)
                    vehicle_in_monitoring_area = self.vehicle_polygon.contains(vehicle_center_point)
                    
                    # Chiều tăng của tọa độ y đi từ trên xuống dưới trong hệ tọa độ ảnh
                    # Vì vậy, một phương tiện vi phạm khi y2 (tọa độ đáy bounding box) <= line_pos (tọa độ y của vạch đỏ)
                    # Đây là điều kiện đơn giản nhất, không cần thêm biên an toàn vì đã kiểm tra rõ ràng cạnh dưới
                    violation_detected = y2 <= line_pos
                    
                    # Tính khoảng cách từ đáy xe (y2) đến vạch dừng (line_pos) để dễ debug
                    distance_to_line = line_pos - y2
                    
                    # Vẽ bounding box và điểm đáy của box lên frame để kiểm tra trực quan
                    cv2.rectangle(violation_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 255), 2)  # Box màu vàng
                    cv2.line(violation_frame, (int(x1), int(y2)), (int(x2), int(y2)), (0, 0, 255), 2)  # Đáy box màu đỏ
                    cv2.putText(violation_frame, f"y2={int(y2)}, line={int(line_pos)}", (int(x1), int(y2 + 15)), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                    
                    
                    # Lưu ảnh debug để kiểm tra trực quan
                    debug_img_path = os.path.join(VIOLATIONS_FOLDER, f"debug_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg")
                    cv2.imwrite(debug_img_path, violation_frame)
                    
                    # Debug log để kiểm tra tọa độ chi tiết
                    logger.info(f"KIỂM TRA VI PHẠM: Xe tại ({center_x}, {center_y}), y1={y1}, y2={y2}, line_pos={line_pos}, distance_to_line={distance_to_line}")
                    logger.debug(f"Xe: y1={y1}, y2={y2}, line_pos={line_pos}, violation_detected={violation_detected}")
                    
                    # Nếu thỏa mãn tất cả điều kiện, ghi nhận vi phạm
                    if vehicle_in_monitoring_area and violation_detected:
                        logger.info(f"⚠️ VI PHẠM RÕ RÀNG: Xe tại ({center_x}, {center_y}), phần đuôi y2={y2} nằm phía trên vạch tại {line_pos}, khoảng cách={distance_to_line}px")
                        # Kiểm tra xem phương tiện này đã được kiểm tra trong tracked_vehicles chưa
                        already_checked = False
                        for vehicle_id, vehicle_data in self.tracked_vehicles.items():
                            if vehicle_id in checked_violation_ids:
                                continue
                                
                            if vehicle_data.get('current_bbox'):
                                v_x1, v_y1, v_x2, v_y2 = vehicle_data['current_bbox']
                                # Kiểm tra xem có phải cùng một phương tiện không
                                if self.is_same_vehicle((x1, y1, x2, y2), (v_x1, v_y1, v_x2, v_y2)):
                                    already_checked = True
                                    checked_violation_ids.add(vehicle_id)
                                    
                                    # Nếu phương tiện chưa được đánh dấu vi phạm, đánh dấu vi phạm
                                    if not vehicle_data.get('crossed_line', False):
                                        vehicle_data['crossed_line'] = True
                                        self.record_violation(vehicle, license_plates, center_x, center_y, 
                                                            "", violation_frame, line_start, 
                                                            line_end, new_violations)
                                    break
                        
                        # Nếu không tìm thấy trong tracked_vehicles hoặc không được đánh dấu vi phạm
                        if not already_checked:
                            # Tạo vi phạm mới
                            self.record_violation(vehicle, license_plates, center_x, center_y, 
                                                "", violation_frame, line_start, 
                                                line_end, new_violations)
                except Exception as e:
                    logger.error(f"Lỗi khi xử lý phương tiện: {str(e)}")
            
            # PHẦN 2: THEO DÕI PHƯƠNG TIỆN QUA CÁC FRAME
            self.update_vehicle_tracking(vehicles, frame)
            
            return new_violations
        except Exception as e:
            logger.error(f"Lỗi trong track_vehicles_and_detect_violations: {str(e)}")
            logger.error(traceback.format_exc())
            return []
    
    def update_vehicle_tracking(self, vehicles, frame=None):
        """
        Cập nhật thông tin theo dõi phương tiện
        
        Args:
            vehicles: Danh sách các phương tiện được phát hiện
            frame: Khung hình hiện tại (nếu cần chụp ảnh vi phạm)
        """
        current_vehicles = {}
        
        for vehicle in vehicles:
            x1, y1, x2, y2, class_id, score = vehicle
            
            # Tính toán tâm của phương tiện
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            
            # Tìm phương tiện gần nhất trong danh sách đang theo dõi
            min_distance = float('inf')
            closest_id = None
            
            for vehicle_id, vehicle_data in self.tracked_vehicles.items():
                if len(vehicle_data['position_history']) == 0:
                    continue
                    
                last_pos = vehicle_data['position_history'][-1]
                distance = ((center_x - last_pos[0]) ** 2 + (center_y - last_pos[1]) ** 2) ** 0.5
                
                if distance < min_distance and distance < 100:  # Ngưỡng khoảng cách
                    min_distance = distance
                    closest_id = vehicle_id
            
            # Nếu tìm thấy phương tiện gần nhất, cập nhật vị trí
            if closest_id is not None:
                vehicle_data = self.tracked_vehicles[closest_id]
                
                # Lưu vị trí cũ trước khi cập nhật
                old_bbox = vehicle_data.get('current_bbox', None)
                old_pos = vehicle_data['position_history'][-1] if vehicle_data['position_history'] else None
                
                # Cập nhật lịch sử vị trí và bounding box hiện tại
                vehicle_data['position_history'].append((center_x, center_y))
                vehicle_data['current_bbox'] = (x1, y1, x2, y2)
                
                # Nếu đèn đỏ, kiểm tra vi phạm vượt đèn đỏ
                if self.current_light_status == 'red' and not vehicle_data.get('crossed_line', False):
                    # Kiểm tra xem vạch dừng có tồn tại và là vạch ngang không
                    if self.line:
                        line_coords = list(self.line.coords)
                        # Xác định hướng của vạch (ngang hay dọc)
                        is_horizontal = abs(line_coords[0][1] - line_coords[1][1]) < abs(line_coords[0][0] - line_coords[1][0])
                        
                        # Chỉ kiểm tra vi phạm trên vạch ngang
                        if is_horizontal:
                            # Lấy vị trí của vạch ngang - lấy giá trị y nhỏ nhất trong trường hợp vạch không hoàn toàn ngang
                            line_pos = min(line_coords[0][1], line_coords[1][1])
                            
                            # Lấy vị trí y2 trước đó của phương tiện (nếu có)
                            old_y2 = vehicle_data.get('old_y2', None)
                            
                            # Đảm bảo tọa độ đáy của phương tiện (y2) <= tọa độ vạch dừng (line_pos)
                            # là điều kiện đủ để xác định vi phạm
                            violation_detected = y2 <= line_pos
                            
                            # Debug log để kiểm tra tọa độ chi tiết
                            logger.debug(f"Tracking - Xe (ID: {closest_id}): y1={y1}, y2={y2}, old_y2={old_y2}, line_pos={line_pos}, violation={violation_detected}")
                            
                            # Phương tiện vi phạm khi:
                            # 1. Phần đuôi xe hiện tại đã vượt qua vạch (y2 <= line_pos)
                            # 2. Phần đuôi xe trước đó chưa vượt qua vạch (old_y2 > line_pos hoặc old_y2 là None)
                            just_crossed = violation_detected and (old_y2 is None or old_y2 > line_pos)
                            
                            if just_crossed:
                                vehicle_data['crossed_line'] = True
                                logger.info(f"Phương tiện (ID: {closest_id}) vừa vượt qua vạch ngang khi đèn đỏ")
                                logger.info(f"📏 Chi tiết: đuôi xe y2={y2} nằm phía trên vạch tại {line_pos}, khoảng cách={line_pos-y2}px")
                                
                                # Xác định điểm đầu và cuối của vạch dừng
                                line_start = (int(line_coords[0][0]), int(line_coords[0][1]))
                                line_end = (int(line_coords[1][0]), int(line_coords[1][1]))
                                
                                # Chụp ảnh vi phạm ngay lập tức
                                try:
                                    vehicle_tuple = (x1, y1, x2, y2, class_id, score)
                                    frame_height, frame_width = frame.shape[:2]
                                    _, _, license_plates = self.detector.detect_objects(frame)
                                    self.record_violation(vehicle_tuple, license_plates, center_x, center_y, 
                                                       "", frame.copy(), line_start, line_end, 
                                                       [])  # Không cần thêm vào new_violations ở đây
                                except Exception as e:
                                    logger.error(f"Lỗi khi ghi nhận vi phạm tự động: {str(e)}")
                            elif violation_detected:
                                # Đã qua vạch nhưng không phải vừa mới qua
                                vehicle_data['crossed_line'] = True
                            
                            # Lưu vị trí y2 hiện tại cho lần kiểm tra tiếp theo
                            vehicle_data['old_y2'] = y2
                
                current_vehicles[closest_id] = vehicle_data
            else:
                # Tạo ID mới cho phương tiện chưa được theo dõi
                vehicle_type = self.detector.vehicle_classes[class_id]
                
                new_vehicle = {
                    'position_history': [(center_x, center_y)],
                    'crossed_line': False,
                    'vehicle_type': vehicle_type,
                    'current_bbox': (x1, y1, x2, y2),
                    'first_seen': datetime.now().timestamp()
                }
                
                current_vehicles[self.next_vehicle_id] = new_vehicle
                self.next_vehicle_id += 1
        
        # Xóa các phương tiện đã theo dõi quá lâu (có thể đã rời khỏi khung hình)
        current_time = datetime.now().timestamp()
        vehicles_to_keep = {}
        max_tracking_time = 30  # 30 giây
        
        for vehicle_id, vehicle_data in current_vehicles.items():
            if 'first_seen' not in vehicle_data:
                vehicle_data['first_seen'] = current_time
            
            if current_time - vehicle_data['first_seen'] < max_tracking_time:
                vehicles_to_keep[vehicle_id] = vehicle_data
        
        # Cập nhật danh sách phương tiện đang theo dõi
        self.tracked_vehicles = vehicles_to_keep
    
    def is_same_vehicle(self, bbox1, bbox2, iou_threshold=0.5):
        """
        Kiểm tra xem hai bounding box có phải là cùng một phương tiện không
        
        Args:
            bbox1, bbox2: Bounding boxes (x1, y1, x2, y2)
            iou_threshold: Ngưỡng IoU để xác định là cùng một phương tiện
            
        Returns:
            bool: True nếu là cùng một phương tiện
        """
        # Kiểm tra nhanh trước bằng khoảng cách trung tâm
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        center1_x, center1_y = (x1_1 + x2_1) / 2, (y1_1 + y2_1) / 2
        center2_x, center2_y = (x1_2 + x2_2) / 2, (y1_2 + y2_2) / 2
        
        # Tính khoảng cách giữa các tâm
        center_distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5
        
        # Nếu khoảng cách quá lớn, không phải cùng một phương tiện
        max_distance = 300  # Ngưỡng khoảng cách tối đa
        if center_distance > max_distance:
            return False
        
        # Tính IoU (Intersection over Union)
        # Tìm tọa độ của phần giao nhau
        xx1 = max(x1_1, x1_2)
        yy1 = max(y1_1, y1_2)
        xx2 = min(x2_1, x2_2)
        yy2 = min(y2_1, y2_2)
        
        # Tính diện tích giao nhau
        w = max(0, xx2 - xx1)
        h = max(0, yy2 - yy1)
        intersection = w * h
        
        # Tính diện tích của từng bbox
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        # Tính IoU
        iou = intersection / float(area1 + area2 - intersection)
        
        return iou >= iou_threshold or center_distance < 50  # Thỏa mãn một trong hai điều kiện
    
    def record_violation(self, vehicle, license_plates, center_x, center_y, vehicle_direction, 
                       violation_frame, line_start, line_end, new_violations):
        """
        Record a violation when vehicle crosses the line on red light
        
        Args:
            vehicle: Vehicle that violated (bbox, class, confidence)
            license_plates: Detected license plates
            center_x, center_y: Center of vehicle
            vehicle_direction: Direction of vehicle movement
            violation_frame: Frame where violation occurred
            line_start, line_end: Start and end points of the line
            new_violations: List to append new violations to
        """
        try:
            x1, y1, x2, y2, class_id, score = vehicle
            
            # Lấy kích thước frame
            if violation_frame is None:
                logger.error("violation_frame là None")
                return
                
            frame_height, frame_width = violation_frame.shape[:2]
            
            # Lấy số lượng vi phạm hiện tại để tạo mã tự tăng
            violation_count = len(self.violations)
            # Tạo ID dạng số từ 00001 đến 99999
            violation_id = str(violation_count + 1).zfill(5)
            
            # Đảm bảo ID không bị trùng
            existing_ids = {v.get('id', '') for v in self.violations}
            while violation_id in existing_ids:
                violation_count += 1
                violation_id = str(violation_count + 1).zfill(5)
            
            # Đảm bảo thư mục lưu vi phạm tồn tại
            try:
                if not os.path.exists(VIOLATIONS_FOLDER):
                    os.makedirs(VIOLATIONS_FOLDER, exist_ok=True)
                    logger.info(f"Đã tạo thư mục lưu vi phạm: {VIOLATIONS_FOLDER}")
            except Exception as e:
                logger.error(f"Không thể tạo thư mục lưu vi phạm: {str(e)}")
                # Tiếp tục xử lý mà không lưu ảnh
            
            # Lấy thời gian hiện tại
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
            time_for_display = current_time.strftime("%H:%M:%S %d/%m/%Y")  # Format thời gian hiển thị
            
            # Xác định loại phương tiện
            if class_id in self.detector.vehicle_classes:
                vehicle_type = self.detector.vehicle_classes[class_id]
            else:
                vehicle_type = "Unknown"
            
            # Xác định loại vi phạm (mặc định là vượt đèn đỏ)
            violation_type = "Vượt đèn đỏ"
            
            # Tìm biển số xe gần nhất
            license_plate_text = "Không xác định"
            license_plate_bbox = None
            license_plate_img_path = None
            
            if license_plates:
                # Tìm biển số gần nhất với phương tiện
                closest_distance = float('inf')
                closest_lp = None
                
                for lp in license_plates:
                    lp_x1, lp_y1, lp_x2, lp_y2, lp_score = lp
                    lp_center_x = (lp_x1 + lp_x2) / 2
                    lp_center_y = (lp_y1 + lp_y2) / 2
                    
                    # Tính khoảng cách từ tâm biển số đến tâm phương tiện
                    distance = math.sqrt((lp_center_x - center_x) ** 2 + (lp_center_y - center_y) ** 2)
                    
                    # Kiểm tra biển số có thuộc phương tiện không 
                    # (nằm trong hoặc gần với bounding box của phương tiện)
                    is_inside_vehicle = (lp_x1 >= x1 - 20 and lp_x2 <= x2 + 20 and 
                                       lp_y1 >= y1 - 20 and lp_y2 <= y2 + 20)
                    
                    if is_inside_vehicle and distance < closest_distance:
                        closest_distance = distance
                        closest_lp = lp
                
                if closest_lp:
                    # Lưu thông tin biển số
                    lp_x1, lp_y1, lp_x2, lp_y2, lp_score = closest_lp
                    license_plate_bbox = (lp_x1, lp_y1, lp_x2, lp_y2)
                    
                    # Cắt ảnh biển số
                    try:
                        # Kiểm tra tọa độ hợp lệ
                        if (lp_y1 >= 0 and lp_y2 > lp_y1 and lp_x1 >= 0 and lp_x2 > lp_x1 and 
                            lp_y2 <= frame_height and lp_x2 <= frame_width):
                            license_plate_img = violation_frame[int(lp_y1):int(lp_y2), int(lp_x1):int(lp_x2)]
                            license_plate_img_path = os.path.join(VIOLATIONS_FOLDER, f"violation_{violation_id}_plate.jpg")
                            cv2.imwrite(license_plate_img_path, license_plate_img)
                            license_plate_text = "Xem ảnh biển số"
                        else:
                            logger.warning(f"Tọa độ biển số không hợp lệ: ({lp_x1}, {lp_y1}, {lp_x2}, {lp_y2}), kích thước frame: {violation_frame.shape}")
                    except Exception as e:
                        logger.error(f"Lỗi khi lưu ảnh biển số: {str(e)}")
                        license_plate_img_path = None
            
            # Cắt ảnh phương tiện vi phạm
            vehicle_img_path = None
            try:
                # Kiểm tra tọa độ hợp lệ
                if (y1 >= 0 and y2 > y1 and x1 >= 0 and x2 > x1 and 
                    y2 <= frame_height and x2 <= frame_width):
                    vehicle_img = violation_frame[int(y1):int(y2), int(x1):int(x2)]
                    vehicle_img_path = os.path.join(VIOLATIONS_FOLDER, f"violation_{violation_id}_vehicle.jpg")
                    cv2.imwrite(vehicle_img_path, vehicle_img)
                else:
                    logger.warning(f"Tọa độ phương tiện không hợp lệ: ({x1}, {y1}, {x2}, {y2}), kích thước frame: {violation_frame.shape}")
            except Exception as e:
                logger.error(f"Lỗi khi lưu ảnh phương tiện: {str(e)}")
                vehicle_img_path = None
            
            # Tạo một bản sao của frame để vẽ thông tin vi phạm
            # Sử dụng frame gốc không có đa giác
            violation_frame_clean = violation_frame.copy()
            
            # Vẽ đường thẳng đỏ - vạch dừng
            try:
                # Đảm bảo tọa độ nằm trong giới hạn của frame
                line_start_x = max(0, min(int(line_start[0]), frame_width - 1))
                line_start_y = max(0, min(int(line_start[1]), frame_height - 1))
                line_end_x = max(0, min(int(line_end[0]), frame_width - 1))
                line_end_y = max(0, min(int(line_end[1]), frame_height - 1))
                
                # Vẽ đường thẳng đỏ 2px
                cv2.line(violation_frame_clean, (line_start_x, line_start_y), (line_end_x, line_end_y), (0, 0, 255), 2)
            except Exception as e:
                logger.error(f"Lỗi khi vẽ đường thẳng vạch dừng: {str(e)}")
            
            # Vẽ hộp giới hạn màu đỏ quanh phương tiện vi phạm với nhãn VI PHẠM
            try:
                # Đảm bảo tọa độ nằm trong giới hạn của frame
                x1_safe = max(0, min(int(x1), frame_width - 1))
                y1_safe = max(0, min(int(y1), frame_height - 1))
                x2_safe = max(0, min(int(x2), frame_width - 1))
                y2_safe = max(0, min(int(y2), frame_height - 1))
                
                # Vẽ box màu đỏ 2px
                cv2.rectangle(violation_frame_clean, (x1_safe, y1_safe), (x2_safe, y2_safe), (0, 0, 255), 2)
                
                # Thêm nhãn "VI PHẠM" phía trên bounding box
                label = "VIOLATE"
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 0.7
                thickness = 2
                text_size = cv2.getTextSize(label, font, font_scale, thickness)[0]
                
                # Vẽ nền đen cho nhãn
                cv2.rectangle(violation_frame_clean,
                             (x1_safe, y1_safe - text_size[1] - 5),
                             (x1_safe + text_size[0], y1_safe),
                             (0, 0, 0), -1)
                
                # Vẽ text nhãn màu đỏ
                cv2.putText(violation_frame_clean, label,
                           (x1_safe, y1_safe - 5),
                           font, font_scale, (0, 0, 255), thickness)
            except Exception as e:
                logger.error(f"Lỗi khi vẽ hộp giới hạn phương tiện: {str(e)}")
            
            # Hiển thị thời gian ở góc dưới cùng bên trái
            try:
                # Vẽ thời gian ở góc dưới bên trái với font size rõ ràng hơn
                font_scale = 0.7  # Tăng font size
                thickness = 1
                font = cv2.FONT_HERSHEY_SIMPLEX
                
                # Tính toán kích thước text
                text_size = cv2.getTextSize(time_for_display, font, font_scale, thickness)[0]
                
                # Vị trí text: cách lề trái 10px, cách lề dưới 25px
                text_x = 10
                text_y = frame_height - 25
                
                # Vẽ nền đen mờ để text dễ đọc hơn
                cv2.rectangle(violation_frame_clean, 
                             (text_x - 5, text_y - text_size[1] - 5),
                             (text_x + text_size[0] + 5, text_y + 5),
                             (0, 0, 0), -1)
                
                # Vẽ text với màu trắng
                cv2.putText(violation_frame_clean, time_for_display, (text_x, text_y), 
                           font, font_scale, (255, 255, 255), thickness)
            except Exception as e:
                logger.error(f"Lỗi khi vẽ thông tin thời gian: {str(e)}")
            
            # Lưu ảnh toàn cảnh vi phạm
            scene_img_path = None
            try:
                scene_img_path = os.path.join(VIOLATIONS_FOLDER, f"violation_{violation_id}_scene.jpg")
                cv2.imwrite(scene_img_path, violation_frame_clean)
            except Exception as e:
                logger.error(f"Lỗi khi lưu ảnh toàn cảnh vi phạm: {str(e)}")
                scene_img_path = None
            
            # Chuyển đổi các giá trị số từ NumPy sang Python native
            confidence = float(score) if hasattr(score, 'item') else score
            
            # Tạo bản ghi vi phạm mới
            violation = {
                'id': violation_id,
                'timestamp': timestamp,
                'vehicleType': vehicle_type,
                'licensePlate': license_plate_text,
                'confidence': confidence,
                'violation_type': violation_type,
                'direction': vehicle_direction,
                'scene_image': scene_img_path,
                'vehicle_image': vehicle_img_path,
                'license_plate_image': license_plate_img_path
            }
            
            # Thêm vi phạm vào danh sách
            self.violations.append(violation)
            new_violations.append(violation)
            
            logger.info(f"Đã ghi nhận vi phạm: ID={violation_id}, Loại={vehicle_type}, Biển số={license_plate_text}")
            
            # Trả về ID của vi phạm mới
            return violation_id
            
        except Exception as e:
            logger.error(f"Lỗi khi ghi nhận vi phạm: {str(e)}")
            return None
    
    def check_line_crossing(self, position_history, frame_width, frame_height, current_bbox=None):
        """
        Check if vehicle has crossed the line
        
        Args:
            position_history: Position history of vehicle
            frame_width: Width of current frame
            frame_height: Height of current frame
            current_bbox: Current bounding box (x1, y1, x2, y2) if available
            
        Returns:
            bool: True if vehicle has crossed the line
        """
        if len(position_history) < 2:
            return False
        
        # Lấy tọa độ của vạch
        line_coords = list(self.line.coords)
        
        # Xác định hướng của vạch (ngang hay dọc)
        is_horizontal = abs(line_coords[0][1] - line_coords[1][1]) < abs(line_coords[0][0] - line_coords[1][0])
        
        # Chỉ phát hiện vi phạm trên vạch ngang
        if not is_horizontal:
            return False
        
        # Lấy vị trí của vạch (tọa độ y cho vạch ngang) - lấy giá trị y nhỏ nhất trong trường hợp vạch không hoàn toàn ngang
        line_pos = min(line_coords[0][1], line_coords[1][1])
        
        # Sử dụng bounding box nếu có
        if current_bbox is not None:
            x1, y1, x2, y2 = current_bbox
            
            # Phương tiện vi phạm khi phần đuôi xe (y2) nằm phía trên vạch đỏ
            # Trong hệ tọa độ ảnh, y tăng từ trên xuống dưới
            # Vì vậy y2 <= line_pos nghĩa là phần đuôi xe nằm phía trên vạch đỏ, tức là đã vi phạm
            return y2 <= line_pos
            
        # Nếu không có bounding box, sử dụng vị trí tâm (phương pháp cũ)
        last_pos = position_history[-1]
        
        # Kiểm tra vị trí tâm đã vượt qua vạch chưa
        if last_pos[1] > line_pos:
            return True
            
        return False
    
    def draw_boundaries(self, frame):
        """
        Vẽ các đường biên đã định nghĩa lên khung hình
        
        Tham số:
            frame: Khung hình để vẽ lên
        """
        try:
            # Kiểm tra kích thước khung hình để đảm bảo tính nhất quán
            frame_height, frame_width = frame.shape[:2]
            scale_x = frame_width / self.frame_width
            scale_y = frame_height / self.frame_height
            
            # Draw line
            if self.line:
                try:
                    coords = list(self.line.coords)
                    # Đảm bảo tọa độ nằm trong giới hạn của frame
                    x1 = max(0, min(int(coords[0][0] * scale_x), frame_width - 1))
                    y1 = max(0, min(int(coords[0][1] * scale_y), frame_height - 1))
                    x2 = max(0, min(int(coords[1][0] * scale_x), frame_width - 1))
                    y2 = max(0, min(int(coords[1][1] * scale_y), frame_height - 1))
                    
                    cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                except Exception as e:
                    logger.error(f"Lỗi khi vẽ đường thẳng: {str(e)}")
            
            # Không vẽ các đa giác nữa theo yêu cầu
        except Exception as e:
            logger.error(f"Lỗi khi vẽ biên: {str(e)}")
    
    def draw_results(self, frame, vehicles, traffic_lights, license_plates):
        """
        Vẽ kết quả phát hiện lên khung hình
        
        Tham số:
            frame: Khung hình gốc
            vehicles: Danh sách các phương tiện đã phát hiện
            traffic_lights: Danh sách các đèn giao thông đã phát hiện
            license_plates: Danh sách các biển số đã phát hiện
            
        Trả về:
            Khung hình đã chú thích
        """
        try:
            # Tạo bản sao của khung hình
            annotated_frame = frame.copy()
            frame_height, frame_width = annotated_frame.shape[:2]
            
            # Vẽ phương tiện
            for x1, y1, x2, y2, class_id, score in vehicles:
                try:
                    # Đảm bảo tọa độ nằm trong giới hạn của frame
                    x1 = max(0, min(int(x1), frame_width - 1))
                    y1 = max(0, min(int(y1), frame_height - 1))
                    x2 = max(0, min(int(x2), frame_width - 1))
                    y2 = max(0, min(int(y2), frame_height - 1))
                    
                    # Bỏ qua nếu bounding box quá nhỏ
                    if x2 - x1 < 3 or y2 - y1 < 3:
                        continue
                    
                    # Lấy màu và tên lớp
                    color = self.detector.colors[class_id]
                    class_name = self.detector.class_names[class_id]
                    
                    # Vẽ hộp giới hạn
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 1)
                    
                    # Tạo nhãn
                    label = f"{class_name}: {score:.2f}"
                    
                    # Vẽ nền cho nhãn
                    text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    label_y1 = max(0, y1 - text_size[1] - 5)
                    label_x2 = min(x1 + text_size[0], frame_width - 1)
                    cv2.rectangle(annotated_frame, (x1, label_y1), (label_x2, y1), color, -1)
                    
                    # Vẽ văn bản
                    cv2.putText(annotated_frame, label, (x1, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                except Exception as e:
                    logger.error(f"Lỗi khi vẽ phương tiện: {str(e)}")
            
            # Vẽ đèn giao thông trong vùng đã định nghĩa
            for x1, y1, x2, y2, class_id, score in traffic_lights:
                try:
                    # Đảm bảo tọa độ nằm trong giới hạn của frame
                    x1 = max(0, min(int(x1), frame_width - 1))
                    y1 = max(0, min(int(y1), frame_height - 1))
                    x2 = max(0, min(int(x2), frame_width - 1))
                    y2 = max(0, min(int(y2), frame_height - 1))
                    
                    # Bỏ qua nếu bounding box quá nhỏ
                    if x2 - x1 < 3 or y2 - y1 < 3:
                        continue
                    
                    # Lấy màu và tên lớp
                    color = self.detector.colors[class_id]
                    class_name = self.detector.class_names[class_id]
                    
                    # Vẽ hộp giới hạn
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 1)
                    
                    # Tạo nhãn
                    label = f"{class_name}: {score:.2f}"
                    
                    # Vẽ nền cho nhãn
                    text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    label_y1 = max(0, y1 - text_size[1] - 5)
                    label_x2 = min(x1 + text_size[0], frame_width - 1)
                    cv2.rectangle(annotated_frame, (x1, label_y1), (label_x2, y1), color, -1)
                    
                    # Vẽ văn bản
                    cv2.putText(annotated_frame, label, (x1, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                except Exception as e:
                    logger.error(f"Lỗi khi vẽ đèn giao thông: {str(e)}")
            
            # Vẽ biển số xe
            for x1, y1, x2, y2, score in license_plates:
                try:
                    # Đảm bảo tọa độ nằm trong giới hạn của frame
                    x1 = max(0, min(int(x1), frame_width - 1))
                    y1 = max(0, min(int(y1), frame_height - 1))
                    x2 = max(0, min(int(x2), frame_width - 1))
                    y2 = max(0, min(int(y2), frame_height - 1))
                    
                    # Bỏ qua nếu bounding box quá nhỏ
                    if x2 - x1 < 3 or y2 - y1 < 3:
                        continue
                    
                    # Vẽ hộp giới hạn
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (255, 255, 0), 1)
                    
                    # Tạo nhãn
                    label = f"license-plate: {score:.2f}"
                    
                    # Vẽ nền cho nhãn
                    text_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                    label_y1 = max(0, y1 - text_size[1] - 5)
                    label_x2 = min(x1 + text_size[0], frame_width - 1)
                    cv2.rectangle(annotated_frame, (x1, label_y1), (label_x2, y1), (255, 255, 0), -1)
                    
                    # Vẽ văn bản
                    cv2.putText(annotated_frame, label, (x1, max(15, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
                except Exception as e:
                    logger.error(f"Lỗi khi vẽ biển số: {str(e)}")
            
            # Vẽ các đường biên đã định nghĩa
            self.draw_boundaries(annotated_frame)
            
            return annotated_frame
        except Exception as e:
            logger.error(f"Lỗi khi vẽ kết quả phát hiện: {str(e)}")
            return frame  # Trả về frame gốc nếu có lỗi

    def update_boundaries(self, boundaries):
        """
        Cập nhật tọa độ biên cho bộ phát hiện
        
        Tham số:
            boundaries: Dữ liệu biên mới (line, vehiclePolygon, trafficLightPolygon)
        """
        self.boundaries = boundaries
        
        # Cập nhật các đối tượng Shapely
        self.line = None
        self.vehicle_polygon = None
        self.traffic_light_polygon = None
        
        if 'line' in boundaries and len(boundaries['line']) >= 2:
            points = [(p['x'] * self.frame_width, p['y'] * self.frame_height) for p in boundaries['line']]
            # Log tọa độ vạch dừng để kiểm tra
            logger.info(f"KHỞI TẠO: Tọa độ vạch dừng gốc: {points}")
            
            # Đảm bảo vạch dừng được định nghĩa từ trái sang phải
            if points[0][0] > points[1][0]:
                points = [points[1], points[0]]
                logger.info(f"KHỞI TẠO: Đã đổi chiều vạch dừng: {points}")
            
            self.line = LineString(points)
        
        if 'vehiclePolygon' in boundaries and len(boundaries['vehiclePolygon']) >= 3:
            points = [(p['x'] * self.frame_width, p['y'] * self.frame_height) for p in boundaries['vehiclePolygon']]
            self.vehicle_polygon = Polygon(points)
            logger.info(f"KHỞI TẠO: Tọa độ đa giác phương tiện: {points}")
        
        if 'trafficLightPolygon' in boundaries and len(boundaries['trafficLightPolygon']) >= 3:
            points = [(p['x'] * self.frame_width, p['y'] * self.frame_height) for p in boundaries['trafficLightPolygon']]
            self.traffic_light_polygon = Polygon(points)
            logger.info(f"KHỞI TẠO: Tọa độ đa giác đèn giao thông: {points}")
    
    def get_light_status_vietnamese(self):
        """
        Lấy trạng thái đèn giao thông bằng tiếng Việt
        
        Returns:
            str: Trạng thái đèn giao thông bằng tiếng Việt
        """
        if self.current_light_status == 'red':
            return "ĐỎ"
        elif self.current_light_status == 'yellow':
            return "VÀNG"
        elif self.current_light_status == 'green':
            return "XANH"
        else:
            return "KHÔNG XÁC ĐỊNH"
    
    def get_light_status_color(self):
        """
        Lấy màu tương ứng với trạng thái đèn giao thông
        
        Returns:
            tuple: Màu BGR tương ứng với trạng thái đèn giao thông
        """
        if self.current_light_status == 'red':
            return (0, 0, 255)  # Đỏ
        elif self.current_light_status == 'yellow':
            return (0, 255, 255)  # Vàng
        elif self.current_light_status == 'green':
            return (0, 255, 0)  # Xanh
        else:
            return (255, 255, 255)  # Trắng 

    def update_vehicle_counts(self, vehicles):
        """
        Cập nhật số lượng phương tiện dựa trên phát hiện
        
        Args:
            vehicles: Danh sách các phương tiện phát hiện được
        """
        # Reset counts
        vehicle_counts = {
            'car': 0,
            'motorbike': 0,
            'truck': 0,
            'bus': 0
        }
        
        # Count by type
        for _, _, _, _, class_id, _ in vehicles:
            if class_id == 1:  # car
                vehicle_counts['car'] += 1
            elif class_id == 4:  # motorbike
                vehicle_counts['motorbike'] += 1
            elif class_id == 6:  # truck
                vehicle_counts['truck'] += 1
            elif class_id == 0:  # bus
                vehicle_counts['bus'] += 1
        
        # Log để debug
        logger.debug(f"Số lượng phương tiện được đếm: {vehicle_counts}")
        
        # Cập nhật số lượng phương tiện
        self.vehicle_counts = vehicle_counts 