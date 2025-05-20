// Đối tượng dữ liệu mẫu - sẽ được thay thế bằng dữ liệu thực từ backend
const mockData = {
    vehicles: {
        car: 0,
        motorcycle: 0,
        truck: 0,
        bus: 0,
    },
    trafficLight: 'yellow', // red, yellow, green
    alertZones: {
        redLightBoundary: false,
        detectionZone: false
    },
    violations: []
};

// Khởi tạo dữ liệu cho bảng
let currentPage = 1;
const itemsPerPage = 8;
let totalPages = 1;
// Lưu trữ trạng thái của các vi phạm đã xác nhận/loại trừ cục bộ
let confirmedViolations = new Set();
let rejectedViolations = new Set();

// Cache dữ liệu phía client
const clientCache = {
    stats: { data: null, timestamp: 0, ttl: 1500 }, // Cache thống kê 1.5 giây
    violations: { data: null, timestamp: 0, ttl: 4000 }, // Cache vi phạm 4 giây
    frames: { data: null, timestamp: 0, ttl: 100 }, // Cache frame 100ms
    violationDetails: { }, // Cache chi tiết vi phạm theo ID
};

// Hàm lấy dữ liệu từ cache hoặc API
async function getDataWithCache(cacheKey, apiUrl, params = {}) {
    const cache = clientCache[cacheKey];
    const now = Date.now();
    
    // Nếu có dữ liệu trong cache và chưa hết hạn, dùng dữ liệu đó
    if (cache && cache.data && (now - cache.timestamp < cache.ttl)) {
        return cache.data;
    }
    
    // Thêm timestamp để tránh cache trình duyệt
    const timestamp = new Date().getTime();
    const url = new URL(apiUrl, window.location.origin);
    
    // Thêm các tham số
    Object.keys(params).forEach(key => {
        url.searchParams.append(key, params[key]);
    });
    
    // Thêm timestamp để tránh cache
    url.searchParams.append('t', timestamp);
    
    try {
        const response = await fetch(url);
        const data = await response.json();
        
        // Lưu vào cache
        clientCache[cacheKey] = {
            data,
            timestamp: now,
            ttl: cache.ttl
        };
        
        return data;
    } catch (error) {
        console.error(`Lỗi khi lấy dữ liệu ${cacheKey}:`, error);
        // Trả về dữ liệu cũ từ cache nếu có lỗi
        return cache?.data || null;
    }
}

// Hàm khởi tạo
document.addEventListener('DOMContentLoaded', () => {
    // Khởi tạo các phần giao diện
    initVehicleStats();
    initTrafficLightStatus();
    setupEventListeners();
    initVideoPlaceholder();
    
    // Khởi tạo và cập nhật dữ liệu vi phạm
    updateViolations();
    
    // Lấy dữ liệu thống kê ban đầu
    getStats();
    
    // Thiết lập cập nhật định kỳ thông tin thống kê và vi phạm
    setInterval(getStats, 2000); // Cập nhật thống kê mỗi 2 giây
    setInterval(refreshViolationsData, 5000); // Cập nhật vi phạm mỗi 5 giây
});

// Hàm cập nhật dữ liệu vi phạm từ server nhưng vẫn giữ nguyên trạng thái UI
function refreshViolationsData() {
    // Không cập nhật UI nếu modal đang mở
    if (document.querySelector('.modal.show')) {
        return;
    }
    
    // Gọi updateViolations để lấy dữ liệu mới và áp dụng trạng thái local
    updateViolations(currentPage);
}

// Khởi tạo thống kê phương tiện với animation
function initVehicleStats() {
    // Cập nhật với animation
    updateVehicleCount('car', mockData.vehicles.car);
    
    // Thêm khoảng thời gian delay cho mỗi animation để tạo hiệu ứng lần lượt
    setTimeout(() => {
        updateVehicleCount('motorcycle', mockData.vehicles.motorcycle);
    }, 200);
    
    setTimeout(() => {
        updateVehicleCount('truck', mockData.vehicles.truck);
    }, 400);
    
    setTimeout(() => {
        updateVehicleCount('bus', mockData.vehicles.bus);
    }, 600);
}

// Cập nhật số lượng phương tiện
function updateVehicleCount(type, count) {
    try {
        // Đảm bảo count là một số
        if (count === null || count === undefined) {
            count = 0;
        } else if (typeof count !== 'number') {
            // Nếu count không phải là số, cố gắng chuyển đổi
            count = parseInt(count);
            // Nếu vẫn không thể chuyển đổi, sử dụng 0
            if (isNaN(count)) {
                console.warn(`Không thể chuyển đổi giá trị count cho ${type}:`, count);
                count = 0;
            }
        }

        const iconContainer = document.querySelector(`.icon-container.${type}`);
        if (!iconContainer) {
            console.warn(`Icon container for ${type} not found`);
            return;
        }
        
        const nextElement = iconContainer.nextElementSibling;
        if (!nextElement) {
            console.warn(`Next element sibling for ${type} icon container not found`);
            return;
        }
        
        const countElement = nextElement.querySelector('h3');
        if (!countElement) {
            console.warn(`Count element (h3) for ${type} not found`);
            return;
        }
    
    // Animation đếm số sử dụng requestAnimationFrame để làm mượt hơn
    const duration = 1500;
    const startTime = performance.now();
        const startValue = parseInt(countElement.textContent) || 0;
    
    function updateCount(currentTime) {
        const elapsedTime = currentTime - startTime;
        const progress = Math.min(elapsedTime / duration, 1);
        
        // Easing function để làm cho animation tự nhiên hơn
        const easedProgress = easeOutQuad(progress);
        const currentValue = Math.floor(startValue + easedProgress * (count - startValue));
        
        countElement.textContent = currentValue;
        
        if (progress < 1) {
            requestAnimationFrame(updateCount);
        } else {
            countElement.textContent = count;
        }
    }
    
    requestAnimationFrame(updateCount);
    } catch (error) {
        console.error(`Error updating vehicle count for ${type}:`, error);
    }
}

// Hàm easing để làm mượt animation
function easeOutQuad(t) {
    return t * (2 - t);
}

// Khởi tạo trạng thái đèn giao thông
function initTrafficLightStatus() {
    const lights = document.querySelectorAll('.light');
    lights.forEach(light => light.classList.remove('active'));
    
    const activeLight = document.querySelector(`.light.${mockData.trafficLight}`);
    if (activeLight) {
        activeLight.classList.add('active');
    }
}

// Thay đổi trạng thái đèn giao thông với animation mượt
function changeTrafficLight(color) {
    try {
        if (!color) {
            console.warn('Traffic light color not provided');
            return;
        }
        
    const lights = document.querySelectorAll('.light');
    const oldActiveLight = document.querySelector('.light.active');
    const newActiveLight = document.querySelector(`.light.${color}`);
        
        if (!newActiveLight) {
            console.warn(`Traffic light element for color ${color} not found`);
        }
    
    if (oldActiveLight) {
        // Thêm class transition cho hiệu ứng mờ dần
        oldActiveLight.classList.add('transitioning');
        
        setTimeout(() => {
            oldActiveLight.classList.remove('active');
            oldActiveLight.classList.remove('transitioning');
            
            if (newActiveLight) {
                // Thêm hiệu ứng fade in cho đèn mới
                newActiveLight.classList.add('transitioning');
                newActiveLight.classList.add('active');
                
                setTimeout(() => {
                    newActiveLight.classList.remove('transitioning');
                }, 300);
            }
        }, 300);
    } else if (newActiveLight) {
        // Nếu không có đèn nào đang active
        newActiveLight.classList.add('active');
    }
    
    mockData.trafficLight = color;
    } catch (error) {
        console.error(`Error updating traffic light to ${color}:`, error);
    }
}

// Chức năng vùng cảnh báo đã được loại bỏ

// Khởi tạo video placeholder và công cụ vẽ biên
function initVideoPlaceholder() {
    const video = document.getElementById('traffic-video');
    const videoStream = document.querySelector('.video-stream');
    let currentDrawingMode = null;
    let isDrawing = false;
    
    // Dữ liệu lưu trữ điểm vẽ biên
    const boundaryData = {
        line: [],
        vehiclePolygon: [],
        trafficLightPolygon: []
    };
    
    // Tạo canvas cho vẽ biên
    const boundaryCanvas = document.createElement('canvas');
    boundaryCanvas.className = 'boundary-canvas';
    boundaryCanvas.style.position = 'absolute';
    boundaryCanvas.style.top = '0';
    boundaryCanvas.style.left = '0';
    boundaryCanvas.style.width = '100%';
    boundaryCanvas.style.height = '100%';
    boundaryCanvas.style.pointerEvents = 'none';
    boundaryCanvas.style.zIndex = '120';
    videoStream.appendChild(boundaryCanvas);
    
    // Thêm sự kiện cho nút chỉnh sửa và menu
    const editBtn = document.querySelector('.edit-btn');
    const boundaryMenu = document.querySelector('.boundary-menu');
    const closeMenuBtn = document.querySelector('.close-menu');
    const boundaryBtns = document.querySelectorAll('.boundary-btn');
      // Mở/đóng menu
    editBtn.addEventListener('click', () => {
        boundaryMenu.classList.toggle('active');
    });
    
    closeMenuBtn.addEventListener('click', () => {
        boundaryMenu.classList.remove('active');
    });
      // Xử lý các nút vẽ biên
    boundaryBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            // Ngăn chặn sự kiện lan truyền đến videoStream
            e.stopPropagation();
            
            const type = btn.dataset.type;
            
            // Xóa active state từ tất cả các nút
            boundaryBtns.forEach(b => b.classList.remove('active'));
            
            // Tạm ẩn menu trong chế độ vẽ để không cản trở
            if (type !== 'save' && type !== 'clear') {
                setTimeout(() => {
                    boundaryMenu.classList.remove('active');
                }, 500);
            }
            
              switch(type) {
                case 'line':                    // Đánh dấu nút đang chọn
                    btn.classList.add('active');
                    currentDrawingMode = type;
                    enableDrawing();
                    break;
                    
                case 'vehicle-polygon':
                case 'traffic-light-polygon':
                    // Đánh dấu nút đang chọn
                    btn.classList.add('active');
                    currentDrawingMode = type;
                    enableDrawing();
                    break;
                    
                case 'save':
                    saveBoundaryData();
                    break;
                    
                case 'clear':
                    clearBoundaryData();
                    break;
            }
        });
    });    // Hiển thị hướng dẫn trên màn hình
    function showDrawingGuide(mode) {
        // Tạo hoặc cập nhật phần tử hướng dẫn
        let guideElement = document.querySelector('.drawing-guide');
        if (!guideElement) {
            guideElement = document.createElement('div');
            guideElement.className = 'drawing-guide';
            document.body.appendChild(guideElement);
        }
        
        // Xác định nội dung hướng dẫn dựa trên chế độ vẽ
        let guideContent = '';
        switch (mode) {
            case 'line':
                guideContent = '<i class="fas fa-info-circle"></i> Nhấp chuột để đặt điểm đầu, sau đó nhấp lần nữa để đặt điểm cuối và hoàn thành đường thẳng';
                break;
            case 'vehicle-polygon':
            case 'traffic-light-polygon':
                guideContent = '<i class="fas fa-info-circle"></i> Nhấp chuột để đặt các điểm, nhấp đúp để hoàn thành đa giác';
                break;
            default:
                return; // Không hiển thị hướng dẫn nếu không có chế độ vẽ
        }
        
        guideElement.innerHTML = guideContent;
        guideElement.classList.add('show');
        
        // Tự động ẩn sau 5 giây
        setTimeout(() => {
            guideElement.classList.remove('show');
            setTimeout(() => {
                if (guideElement.parentNode) {
                    guideElement.parentNode.removeChild(guideElement);
                }
            }, 300);
        }, 5000);
    }

    function enableDrawing() {
        // Bật chế độ vẽ
        videoStream.style.cursor = 'crosshair';
        videoStream.style.pointerEvents = 'auto';
        isDrawing = true;
        
        // Xóa các sự kiện cũ
        videoStream.removeEventListener('click', handleCanvasClick);
        videoStream.removeEventListener('dblclick', handleDoubleClick);
        videoStream.removeEventListener('mousedown', handleMouseDown);
        videoStream.removeEventListener('mousemove', handleMouseMove);
        videoStream.removeEventListener('mouseup', handleMouseUp);
        videoStream.removeEventListener('mouseleave', handleMouseLeave);
        
        // Thêm sự kiện phù hợp với mode vẽ
        if (currentDrawingMode === 'line') {
            // Với đường thẳng, dùng click để đặt 2 điểm
            videoStream.addEventListener('click', handleCanvasClick);
            videoStream.addEventListener('mouseleave', handleMouseLeave);
            
            // Reset trạng thái vẽ đường thẳng
            isDrawingLine = false;
            startPoint = null;
            boundaryData.line = [];
            
              // Hiển thị hướng dẫn cho vẽ đường thẳng
            showDrawingGuide('line');
        } else {
            // Với đa giác, dùng click để đặt từng điểm
            videoStream.addEventListener('click', handleCanvasClick);
            // Double click để đóng đa giác
            videoStream.addEventListener('dblclick', handleDoubleClick);
            
            // Hiển thị hướng dẫn cho vẽ đa giác
            showDrawingGuide(currentDrawingMode);
        }
    }    function handleDoubleClick(e) {
        // Ngăn chặn sự kiện lan truyền
        e.stopPropagation();
        
        // Xử lý sự kiện khi double-click để hoàn thành đa giác
        if (currentDrawingMode === 'vehicle-polygon' || currentDrawingMode === 'traffic-light-polygon') {
            const currentPolygon = currentDrawingMode === 'vehicle-polygon' 
                ? boundaryData.vehiclePolygon 
                : boundaryData.trafficLightPolygon;
            
            // Nếu đã có ít nhất 3 điểm thì hoàn thành đa giác
            if (currentPolygon.length >= 3) {
                // Vẽ lại với đa giác đã đóng
                drawBoundaries();
                
                // Hiển thị menu lại sau khi hoàn thành
                setTimeout(() => {
                    boundaryMenu.classList.add('active');
                    
                    // Xóa phần tử hướng dẫn nếu có
                    const guideElement = document.querySelector('.drawing-guide');
                    if (guideElement && guideElement.parentNode) {
                        guideElement.classList.remove('show');
                        setTimeout(() => {
                            guideElement.parentNode.removeChild(guideElement);
                        }, 300);
                    }
                }, 1000);
            } else {
                showToast('Cần ít nhất 3 điểm để tạo đa giác', 'error');
            }
        }
    }
      // Các biến để theo dõi vẽ đường thẳng
    let startPoint = null;
    let isDrawingLine = false;
    
    function handleMouseDown(e) {
        // Không sử dụng mousedown cho vẽ đường thẳng nữa
        // Chỉ giữ lại để tương thích với các chức năng khác
    }
    
    function handleMouseLeave(e) {
        // Vẫn giữ lại xử lý khi chuột ra khỏi vùng video cho các chức năng khác
        if (currentDrawingMode === 'line' && isDrawingLine) {
            // Không hủy thao tác vẽ đường thẳng khi chuột ra khỏi vùng video
            // Người dùng vẫn có thể quay lại để click điểm thứ hai
        }
    }
    
    function handleMouseMove(e) {
        // Chỉ giữ lại để tương thích với các chức năng khác
    }
    
    function handleMouseUp(e) {
        // Chỉ giữ lại để tương thích với các chức năng khác
    }

    function handleCanvasClick(e) {
        // Ngăn chặn sự kiện lan truyền
        e.stopPropagation();
        
        // Kiểm tra xem click có phải là trên menu hay nút edit không
        const clickedElement = e.target;
        if (clickedElement.closest('.boundary-menu') || clickedElement.closest('.edit-btn')) {
            return; // Không xử lý click nếu đang click vào menu hoặc nút edit
        }
        
        // Obter o elemento de vídeo ou imagem atual
        const videoElement = document.getElementById('traffic-video');
        const frameImg = document.querySelector('.frame-img');
            
        // Determinar o elemento de referência (vídeo ou imagem de frame)
        const referenceElement = (frameImg && window.getComputedStyle(frameImg).display !== 'none') 
            ? frameImg : videoElement;
            
        // Obter retângulo do contêiner
        const containerRect = videoStream.getBoundingClientRect();
        
        // Obter as dimensões e posição real do vídeo/imagem
        let videoRect;
        if (referenceElement) {
            videoRect = referenceElement.getBoundingClientRect();
        } else {
            // Fallback para o contêiner se não encontrar elemento de referência
            videoRect = containerRect;
        }
        
        // Calcular a posição do clique em relação ao contêiner
        const containerX = e.clientX - containerRect.left;
        const containerY = e.clientY - containerRect.top;
        
        // Verificar se o clique está dentro do vídeo/imagem
        if (containerX < videoRect.left - containerRect.left || 
            containerX > videoRect.right - containerRect.left ||
            containerY < videoRect.top - containerRect.top || 
            containerY > videoRect.bottom - containerRect.top) {
            return; // Clique fora do vídeo, ignorar
        }
        
        // Calcular a posição relativa dentro do vídeo/imagem
        const videoX = containerX - (videoRect.left - containerRect.left);
        const videoY = containerY - (videoRect.top - containerRect.top);
            
        // Calcular posição normalizada (0-1)
        const point = { 
            x: videoX / videoRect.width, 
            y: videoY / videoRect.height 
        };
        
        switch(currentDrawingMode) {
            case 'line':
                // Xử lý vẽ đường thẳng bằng cách click
                if (!isDrawingLine) {
                    // Điểm đầu tiên
                    startPoint = point;
                    isDrawingLine = true;
                    boundaryData.line = [startPoint]; // Lưu điểm đầu
                    
                    // Hiển thị thông báo cho người dùng
                    showToast('Đã đặt điểm đầu tiên. Nhấp để đặt điểm thứ hai.', 'info');
            
                    // Vẽ điểm đầu tiên
            const canvas = boundaryCanvas;
            const ctx = canvas.getContext('2d');
                    
                    // Lấy thông tin về kích thước video và offset
                    const videoElement = document.getElementById('traffic-video');
                    const frameImg = document.querySelector('.frame-img');
                    const referenceElement = (frameImg && window.getComputedStyle(frameImg).display !== 'none') 
                        ? frameImg : videoElement;
                    
                    // Obter as dimensões reais do vídeo/imagem dentro do contêiner
                    const containerWidth = videoStream.clientWidth;
                    const containerHeight = videoStream.clientHeight;
                    
                    // Calcular a escala e o deslocamento do vídeo/imagem
                    let videoWidth, videoHeight, offsetX, offsetY;
                    
                    if (referenceElement) {
                        const rect = referenceElement.getBoundingClientRect();
                        videoWidth = rect.width;
                        videoHeight = rect.height;
            
                        // Calcular o deslocamento se o vídeo estiver centralizado
                        offsetX = (containerWidth - videoWidth) / 2;
                        offsetY = (containerHeight - videoHeight) / 2;
                    } else {
                        // Fallback para o tamanho do contêiner se não encontrar o elemento
                        videoWidth = containerWidth;
                        videoHeight = containerHeight;
                        offsetX = 0;
                        offsetY = 0;
                    }
                    
                    // Đặt kích thước canvas
                    canvas.width = containerWidth;
                    canvas.height = containerHeight;
                    
                    // Vẽ điểm đầu
                    const x = startPoint.x * videoWidth + offsetX;
                    const y = startPoint.y * videoHeight + offsetY;
                    
                    ctx.beginPath();
                    ctx.fillStyle = 'red';
                    ctx.arc(x, y, 5, 0, Math.PI * 2);
                    ctx.fill();
            
                    // Hiển thị số thứ tự điểm
                    showPointIndicator(1, 'red', x, y);
                } else {
                    // Điểm thứ hai - hoàn thành đường thẳng
                    boundaryData.line.push(point); // Thêm điểm cuối
            
            // Vẽ đường thẳng hoàn chỉnh
            drawBoundaries();
                    
                    // Lấy thông tin về kích thước video và offset
                    const videoElement = document.getElementById('traffic-video');
                    const frameImg = document.querySelector('.frame-img');
                    const referenceElement = (frameImg && window.getComputedStyle(frameImg).display !== 'none') 
                        ? frameImg : videoElement;
                    
                    // Obter as dimensões reais do vídeo/imagem dentro do contêiner
                    const containerWidth = videoStream.clientWidth;
                    const containerHeight = videoStream.clientHeight;
                    
                    // Calcular a escala e o deslocamento do vídeo/imagem
                    let videoWidth, videoHeight, offsetX, offsetY;
                    
                    if (referenceElement) {
                        const rect = referenceElement.getBoundingClientRect();
                        videoWidth = rect.width;
                        videoHeight = rect.height;
                        
                        // Calcular o deslocamento se o vídeo estiver centralizado
                        offsetX = (containerWidth - videoWidth) / 2;
                        offsetY = (containerHeight - videoHeight) / 2;
                    } else {
                        // Fallback para o tamanho do contêiner se não encontrar o elemento
                        videoWidth = containerWidth;
                        videoHeight = containerHeight;
                        offsetX = 0;
                        offsetY = 0;
                    }
                    
                    // Hiển thị số thứ tự điểm
                    const x = point.x * videoWidth + offsetX;
                    const y = point.y * videoHeight + offsetY;
                    showPointIndicator(2, 'red', x, y);
            
            // Hiển thị menu lại sau khi vẽ xong đường thẳng
            setTimeout(() => {
                boundaryMenu.classList.add('active');
                
                // Xóa phần tử hướng dẫn nếu có
                const guideElement = document.querySelector('.drawing-guide');
                if (guideElement && guideElement.parentNode) {
                    guideElement.classList.remove('show');
                    setTimeout(() => {
                        guideElement.parentNode.removeChild(guideElement);
                    }, 300);
                }
            }, 300);
            
            // Reset trạng thái
                    isDrawingLine = false;
            startPoint = null;
            
            // Tắt chế độ vẽ vì đã hoàn thành vẽ đường thẳng
            disableDrawing();
                    
                    // Thông báo hoàn thành
                    showToast('Đã hoàn thành vẽ đường thẳng', 'success');
                }
                break;
                
                  case 'vehicle-polygon':
                boundaryData.vehiclePolygon.push(point);
                break;
                
            case 'traffic-light-polygon':
                boundaryData.trafficLightPolygon.push(point);
                break;
        }
        
        // Vẽ lại canvas
        if (currentDrawingMode !== 'line' || !isDrawingLine) {
        drawBoundaries();
        }
    }
    
    // Hiển thị số thứ tự điểm với hiệu ứng
    function showPointIndicator(pointNumber, color, x, y) {
        const indicator = document.createElement('div');
        indicator.className = 'point-indicator';
        
        // Posição do indicador
        indicator.style.left = `${x}px`;
        indicator.style.top = `${y}px`;
        indicator.style.backgroundColor = color;
        indicator.textContent = pointNumber;
        indicator.style.zIndex = '130'; // Garantir que está acima do canvas
        
        videoStream.appendChild(indicator);
        
        // Animation hiển thị
        setTimeout(() => {
            indicator.classList.add('show');
            
            // Tự động xóa sau 2 giây
            setTimeout(() => {
                indicator.classList.remove('show');
                setTimeout(() => {
                    if (indicator.parentNode) {
                        indicator.parentNode.removeChild(indicator);
                    }
                }, 300);
            }, 2000);
        }, 10);
    }
      function drawBoundaries() {
        const canvas = boundaryCanvas;
        const ctx = canvas.getContext('2d');
        
        // Obter o elemento de vídeo ou imagem atual
        const videoElement = document.getElementById('traffic-video');
        const frameImg = document.querySelector('.frame-img');
        
        // Determinar o elemento de referência (vídeo ou imagem de frame)
        const referenceElement = (frameImg && window.getComputedStyle(frameImg).display !== 'none') 
            ? frameImg : videoElement;
        
        // Obter as dimensões reais do vídeo/imagem dentro do contêiner
        const containerWidth = videoStream.clientWidth;
        const containerHeight = videoStream.clientHeight;
        
        // Calcular a escala e o deslocamento do vídeo/imagem
        let videoWidth, videoHeight, offsetX, offsetY;
        
        if (referenceElement) {
            const rect = referenceElement.getBoundingClientRect();
            videoWidth = rect.width;
            videoHeight = rect.height;
            
            // Calcular o deslocamento se o vídeo estiver centralizado
            offsetX = (containerWidth - videoWidth) / 2;
            offsetY = (containerHeight - videoHeight) / 2;
        } else {
            // Fallback para o tamanho do contêiner se não encontrar o elemento
            videoWidth = containerWidth;
            videoHeight = containerHeight;
            offsetX = 0;
            offsetY = 0;
        }
        
        // Definir as dimensões do canvas para corresponder ao contêiner
        canvas.width = containerWidth;
        canvas.height = containerHeight;
        
        // Limpar o canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Vẽ đường thẳng
        if (boundaryData.line.length > 0) {
            ctx.beginPath();
            ctx.strokeStyle = 'red';
            ctx.lineWidth = 3;
            
            boundaryData.line.forEach((point, index) => {
                // Converter as coordenadas relativas para absolutas, considerando o deslocamento
                const x = point.x * videoWidth + offsetX;
                const y = point.y * videoHeight + offsetY;
                
                if (index === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            
            ctx.stroke();
            
            // Vẽ điểm đầu và điểm cuối
            boundaryData.line.forEach((point) => {
                const x = point.x * videoWidth + offsetX;
                const y = point.y * videoHeight + offsetY;
                
                ctx.beginPath();
                ctx.fillStyle = 'red';
                ctx.arc(x, y, 5, 0, Math.PI * 2);
                ctx.fill();
            });
        }
        
        // Vẽ đa giác phương tiện
        if (boundaryData.vehiclePolygon.length > 0) {
            // Vẽ phần fill trước với độ trong suốt thấp
            if (boundaryData.vehiclePolygon.length >= 3) {
                ctx.beginPath();
                boundaryData.vehiclePolygon.forEach((point, index) => {
                    const x = point.x * videoWidth + offsetX;
                    const y = point.y * videoHeight + offsetY;
                    
                    if (index === 0) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }
                });
                  ctx.closePath();
                ctx.fillStyle = 'rgba(0, 0, 255, 0.05)'; // Xanh dương với độ trong suốt 5%
                ctx.fill();
            }
            
            // Vẽ đường viền
            ctx.beginPath();
            ctx.strokeStyle = 'blue';
            ctx.lineWidth = 3;
            
            boundaryData.vehiclePolygon.forEach((point, index) => {
                const x = point.x * videoWidth + offsetX;
                const y = point.y * videoHeight + offsetY;
                
                if (index === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            
            if (boundaryData.vehiclePolygon.length >= 3) {
                ctx.closePath();
            }
            
            ctx.stroke();
            
            // Vẽ các điểm
            boundaryData.vehiclePolygon.forEach((point) => {
                const x = point.x * videoWidth + offsetX;
                const y = point.y * videoHeight + offsetY;
                
                ctx.beginPath();
                ctx.fillStyle = 'blue';
                ctx.arc(x, y, 5, 0, Math.PI * 2);
                ctx.fill();
                
                // Thêm viền trắng cho điểm dễ nhìn hơn
                ctx.beginPath();
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 2;
                ctx.arc(x, y, 6, 0, Math.PI * 2);
                ctx.stroke();
            });
        }
        
        // Vẽ đa giác đèn giao thông
        if (boundaryData.trafficLightPolygon.length > 0) {
            // Vẽ phần fill trước với độ trong suốt thấp
            if (boundaryData.trafficLightPolygon.length >= 3) {
                ctx.beginPath();
                boundaryData.trafficLightPolygon.forEach((point, index) => {
                    const x = point.x * videoWidth + offsetX;
                    const y = point.y * videoHeight + offsetY;
                    
                    if (index === 0) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }
                });
                  ctx.closePath();
                ctx.fillStyle = 'rgba(0, 255, 0, 0.05)'; // Xanh lục với độ trong suốt 5%
                ctx.fill();
            }
            
            // Vẽ đường viền
            ctx.beginPath();
            ctx.strokeStyle = 'green';
            ctx.lineWidth = 3;
            
            boundaryData.trafficLightPolygon.forEach((point, index) => {
                const x = point.x * videoWidth + offsetX;
                const y = point.y * videoHeight + offsetY;
                
                if (index === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            
            if (boundaryData.trafficLightPolygon.length >= 3) {
                ctx.closePath();
            }
            
            ctx.stroke();
            
            // Vẽ các điểm
            boundaryData.trafficLightPolygon.forEach((point) => {
                const x = point.x * videoWidth + offsetX;
                const y = point.y * videoHeight + offsetY;
                
                ctx.beginPath();
                ctx.fillStyle = 'green';
                ctx.arc(x, y, 5, 0, Math.PI * 2);
                ctx.fill();
                
                // Thêm viền trắng cho điểm dễ nhìn hơn
                ctx.beginPath();
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 2;
                ctx.arc(x, y, 6, 0, Math.PI * 2);
                ctx.stroke();
            });
        }
    }    function saveBoundaryData() {
        // Kiểm tra xem đã vẽ biên nào chưa
        const hasLine = boundaryData.line.length > 0;
        const hasVehiclePolygon = boundaryData.vehiclePolygon.length >= 3;
        const hasTrafficLightPolygon = boundaryData.trafficLightPolygon.length >= 3;
        
        if (!hasLine && !hasVehiclePolygon && !hasTrafficLightPolygon) {
            showToast('Không có biên nào để lưu. Vui lòng vẽ biên trước.', 'error');
            return;
        }
        
        // Gửi dữ liệu biên lên server
        if (typeof saveBoundariesToServer === 'function') {
            saveBoundariesToServer(boundaryData);
        } else {
            // Fallback nếu chưa có hàm saveBoundariesToServer
            console.log('Boundary data saved:', JSON.stringify(boundaryData));
        
        // Hiển thị thông tin chi tiết về biên đã lưu
        let savedInfo = [];
        if (hasLine) savedInfo.push('1 đường thẳng');
        if (hasVehiclePolygon) savedInfo.push('1 đa giác phương tiện');
        if (hasTrafficLightPolygon) savedInfo.push('1 đa giác đèn giao thông');
        
        const infoText = `Đã lưu: ${savedInfo.join(', ')}`;
        showToast(infoText, 'success');
        }
        
        // Đóng menu
        boundaryMenu.classList.remove('active');
        
        // Tắt chế độ vẽ
        disableDrawing();
    }      function clearBoundaryData() {
        // Kiểm tra xem có biên nào để xóa không
        const hasAnyBoundary = 
            boundaryData.line.length > 0 || 
            boundaryData.vehiclePolygon.length > 0 || 
            boundaryData.trafficLightPolygon.length > 0;
        
        if (!hasAnyBoundary) {
            showToast('Không có tọa độ biên nào để xóa', 'info');
            return;
        }
        
        // Hiển thị hộp xác nhận
        showConfirmDialog(
            'Xác nhận xóa', 
            'Bạn có chắc chắn muốn xóa tất cả tọa độ biên đã vẽ?', 
            () => {
                // Callback khi xác nhận xóa
                // Xóa dữ liệu
                boundaryData.line = [];
                boundaryData.vehiclePolygon = [];
                boundaryData.trafficLightPolygon = [];
                
                // Xóa canvas
                const ctx = boundaryCanvas.getContext('2d');
                ctx.clearRect(0, 0, boundaryCanvas.width, boundaryCanvas.height);
                
                // Gửi yêu cầu xóa biên đến server
                const videoId = localStorage.getItem('current_video_id');
                if (videoId) {
                    // Gửi dữ liệu biên trống lên server
                    fetch('/api/save_boundaries', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            video_id: videoId,
                            boundaries: boundaryData
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            showToast('Đã xóa tất cả tọa độ biên!', 'info');
                        } else {
                            showToast(`Lỗi khi xóa biên: ${data.message}`, 'error');
                        }
                    })
                    .catch(error => {
                        console.error('Lỗi khi gửi yêu cầu xóa biên:', error);
                        showToast('Có lỗi xảy ra khi xóa biên trên server', 'error');
                    });
                } else {
                // Hiển thị thông báo
                showToast('Đã xóa tất cả tọa độ biên!', 'info');
                }
                
                // Đóng menu
                boundaryMenu.classList.remove('active');
                
                // Tắt chế độ vẽ
                disableDrawing();
            }
        );
    }function disableDrawing() {
        isDrawing = false;
        videoStream.style.cursor = 'default';
        
        // Quan trọng: Phục hồi pointer-events để không gian video vẫn tiếp tục cho phép người dùng click vào nút edit
        videoStream.style.pointerEvents = '';
        
        // Xóa các sự kiện
        videoStream.removeEventListener('click', handleCanvasClick);
        videoStream.removeEventListener('dblclick', handleDoubleClick);
        videoStream.removeEventListener('mousedown', handleMouseDown);
        videoStream.removeEventListener('mousemove', handleMouseMove);
        videoStream.removeEventListener('mouseup', handleMouseUp);
        videoStream.removeEventListener('mouseleave', handleMouseLeave);
        
        // Xóa active state từ tất cả các nút
        boundaryBtns.forEach(btn => btn.classList.remove('active'));
        currentDrawingMode = null;
    }
    
    // Cập nhật kích thước canvas khi cửa sổ thay đổi
    window.addEventListener('resize', () => {
        if (boundaryCanvas) {
            drawBoundaries();
        }
    });
    
    // Thêm placeholder cho video
    if (video) {
        // Trong môi trường thực, video sẽ được thay thế bằng luồng video thực từ camera
        video.poster = "https://via.placeholder.com/800x450/111827/FFFFFF?text=Camera+Giao+Thông";
        
        // Mô phỏng video luồng giám sát bằng cách thay thế bằng video mẫu
        // Trong một ứng dụng thực tế, bạn sẽ thay thế đây bằng stream từ camera
        const videoUrls = [
            "https://assets.mixkit.co/videos/preview/mixkit-traffic-at-a-junction-in-a-big-city-13389-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-traffic-and-buildings-in-a-city-9241-large.mp4",
            "https://assets.mixkit.co/videos/preview/mixkit-cars-heading-to-the-big-city-9117-large.mp4"
        ];
        
        // Chọn ngẫu nhiên một video
        const randomVideo = videoUrls[Math.floor(Math.random() * videoUrls.length)];
        video.src = randomVideo;
    }
}

// Hiển thị thông báo
function showToast(message, type = 'info') {
    // Tạo phần tử toast
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas ${type === 'info' ? 'fa-info-circle' : type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
        </div>
        <div class="toast-message">${message}</div>
    `;
    
    // Thêm toast vào body
    document.body.appendChild(toast);
    
    // Hiệu ứng hiển thị
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // Tự động ẩn sau 3 giây
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 300);
    }, 3000);
}

// Hiển thị hộp thoại xác nhận
function showConfirmDialog(title, message, confirmCallback, isHTML = false) {
    // Kiểm tra xem đã có dialog nào đang mở không
    const existingDialog = document.querySelector('.confirm-dialog-overlay');
    if (existingDialog) {
        document.body.removeChild(existingDialog);
    }
    
    // Tạo overlay cho dialog
    const overlay = document.createElement('div');
    overlay.className = 'confirm-dialog-overlay';
    
    // Tạo nội dung dialog
    let messageContent;
    if (isHTML) {
        messageContent = message;
    } else {
        messageContent = `<p>${message}</p>`;
    }
    
    const dialogHTML = `
        <div class="confirm-dialog">
            <div class="confirm-dialog-header">
                <h3>${title}</h3>
                <button class="dialog-close"><i class="fas fa-times"></i></button>
            </div>
            <div class="confirm-dialog-body">
                ${messageContent}
            </div>
            <div class="confirm-dialog-footer">
                <button class="btn btn-secondary dialog-cancel">Hủy</button>
                <button class="btn btn-danger dialog-confirm">Xác nhận</button>
            </div>
        </div>
    `;
    
    overlay.innerHTML = dialogHTML;
    document.body.appendChild(overlay);
    
    // Animation hiển thị
    setTimeout(() => {
        overlay.classList.add('active');
        document.querySelector('.confirm-dialog').classList.add('active');
    }, 10);
    
    // Xử lý sự kiện đóng
    const closeDialog = () => {
        overlay.classList.remove('active');
        document.querySelector('.confirm-dialog').classList.remove('active');
        setTimeout(() => {
            document.body.removeChild(overlay);
        }, 300);
    };
    
    // Gắn sự kiện cho các nút
    document.querySelector('.dialog-close').addEventListener('click', closeDialog);
    document.querySelector('.dialog-cancel').addEventListener('click', closeDialog);
    
    document.querySelector('.dialog-confirm').addEventListener('click', () => {
        closeDialog();
        if (typeof confirmCallback === 'function') {
            confirmCallback();
        }
    });
    
    // Đóng dialog khi click vào overlay
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeDialog();
        }
    });
}

// Cập nhật bảng vi phạm từ API
async function updateViolations(page = 1) {
    // Cập nhật trang hiện tại
    currentPage = page;
    
    try {
        // Sử dụng cache để giảm số lượng requests đến server
        const data = await getDataWithCache('violations', '/api/get_violations', {
            page: page,
            per_page: itemsPerPage
        });
        
        if (!data || !data.success) {
            console.warn(`Lỗi khi lấy dữ liệu vi phạm: ${data?.message || 'Không có dữ liệu'}`);
                return;
            }
            
            const violations = data.violations || [];
            const totalPages = data.total_pages || 1;
            
            // Cập nhật biến toàn cục
            window.totalPages = totalPages;
            
        // Lấy phần tử container cards vi phạm
        const violationsGrid = document.getElementById('violations-grid');
        if (!violationsGrid) {
            console.error('Không tìm thấy container vi phạm');
                return;
            }
            
        // Tìm phần tử hiển thị khi không có dữ liệu
        const noViolationsDiv = violationsGrid.querySelector('.no-violations');
        const totalViolationsCount = document.getElementById('total-violations');
        const confirmedViolationsCount = document.getElementById('confirmed-violations');
        
        // Xóa tất cả cards vi phạm trước đó, giữ lại thông báo "không có vi phạm"
        const oldCards = violationsGrid.querySelectorAll('.violation-card');
        oldCards.forEach(card => card.remove());
        
        // Áp dụng trạng thái vi phạm đã lưu ở client
        const processedViolations = violations.map(violation => {
            // Cache chi tiết vi phạm cho xem sau này mà không cần gọi API
            clientCache.violationDetails[violation.id] = violation;
            
            // Áp dụng trạng thái local nếu có
            if (confirmedViolations.has(violation.id)) {
                violation.status = 'Đã xác nhận';
            } else if (rejectedViolations.has(violation.id)) {
                violation.status = 'Đã loại trừ';
            }
            return violation;
        });
        
        // Đếm số vi phạm theo trạng thái
        let confirmedCount = 0;
        let rejectedCount = 0;
        let pendingCount = 0;
        
        // Đếm từ dữ liệu vi phạm hiện tại
        processedViolations.forEach(violation => {
            if ((violation.status && violation.status.toLowerCase() === 'đã xác nhận') || 
                confirmedViolations.has(violation.id)) {
                confirmedCount++;
            } else if ((violation.status && violation.status.toLowerCase() === 'đã loại trừ') || 
                       rejectedViolations.has(violation.id)) {
                rejectedCount++;
            } else {
                pendingCount++;
            }
        });
        
        // Bổ sung đếm từ danh sách lưu local (cho các vi phạm không hiển thị trong trang hiện tại)
        // Tính tổng số vi phạm từ server
        const totalServerViolations = data.total || violations.length;
        
        // Cập nhật số lượng vi phạm đang chờ = tổng - đã xác nhận - đã loại trừ
        pendingCount = totalServerViolations - confirmedViolations.size - rejectedViolations.size;
        
        // Đảm bảo không âm
        pendingCount = Math.max(0, pendingCount);
        
        // Cập nhật hiển thị số lượng
        if (totalViolationsCount) {
            totalViolationsCount.textContent = pendingCount;
        }
        
        // Cập nhật số vi phạm đã xác nhận
        if (confirmedViolationsCount) {
            confirmedViolationsCount.textContent = confirmedViolations.size;
        }
        
        // Hiển thị vi phạm
        renderViolationCards(processedViolations, violationsGrid, noViolationsDiv);
        
        // Cập nhật phân trang
        updatePagination(currentPage, totalPages);
        
        // Áp dụng bộ lọc hiện tại nếu có
        if (window.currentFilter && window.currentFilter !== 'all') {
            filterViolations(window.currentFilter);
        }
        
        // Log để debug
        console.debug(`Đã cập nhật ${violations.length} vi phạm`);
    } catch (error) {
        console.error('Lỗi khi lấy dữ liệu vi phạm:', error);
        // Hiển thị thông báo lỗi cho người dùng
        showToast('Không thể tải dữ liệu vi phạm', 'error');
    }
}

// Tách riêng hàm hiển thị vi phạm để dễ quản lý
function renderViolationCards(violations, container, noViolationsDiv) {
            // Thêm dữ liệu mới
            if (violations.length === 0) {
                // Nếu không có vi phạm, hiển thị thông báo
        if (noViolationsDiv) {
                    noViolationsDiv.style.display = 'flex';
        } else {
            // Tạo nội dung "không có vi phạm" nếu chưa có
            const newNoViolations = document.createElement('div');
            newNoViolations.className = 'no-violations';
            newNoViolations.innerHTML = `
                <i class="fas fa-info-circle"></i>
                <p>Không có dữ liệu vi phạm</p>
            `;
            container.appendChild(newNoViolations);
                }
            } else {
        // Ẩn thông báo "không có vi phạm" nếu có
        if (noViolationsDiv) {
                    noViolationsDiv.style.display = 'none';
                }
                
                violations.forEach((violation, index) => {
            // Format và xử lý dữ liệu ở client
            const formattedViolation = formatViolationData(violation);
            
            // Tạo card vi phạm
            const card = createViolationCard(formattedViolation);
            
            // Thêm card vào grid
            container.appendChild(card);
        });
    }
}

// Hàm định dạng dữ liệu vi phạm ở client
function formatViolationData(violation) {
                    // Format thời gian vi phạm
                    let timeStr = 'N/A';
                    if (violation.timestamp) {
                        try {
                            // Chuyển đổi timestamp thành thời gian hiển thị
                            const date = new Date(violation.timestamp);
                            timeStr = date.toLocaleTimeString('vi-VN', {
                                hour: '2-digit', 
                                minute: '2-digit', 
                                second: '2-digit',
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric'
                            });
                        } catch (e) {
                            console.warn(`Lỗi khi định dạng thời gian: ${e.message}`);
                            timeStr = violation.timestamp; // Hiển thị timestamp gốc nếu có lỗi
                        }
                    }
                    
                    // Format mã vi phạm: 5 chữ số với số 0 ở đầu nếu cần
    let violationId;
    if (violation.id) {
        // Nếu ID đã là dạng số 5 chữ số, hiển thị như vậy
        if (/^\d{1,5}$/.test(violation.id)) {
            violationId = violation.id.toString().padStart(5, '0');
        } else {
            // Nếu ID không phải dạng số hoặc quá dài, sử dụng ID như được cấp
            violationId = violation.id.toString().substring(0, 5).padStart(5, '0');
        }
    } else {
        violationId = '00000';
    }
    
    // Xác định biểu tượng phương tiện
    let vehicleIcon = 'fa-car';
    switch (violation.vehicleType?.toLowerCase()) {
        case 'motorcycle':
        case 'motorbike':
            vehicleIcon = 'fa-motorcycle';
            break;
        case 'truck':
            vehicleIcon = 'fa-truck';
            break;
        case 'bus':
            vehicleIcon = 'fa-bus';
            break;
    }
    
    // Xác định trạng thái vi phạm
    const status = violation.status || 'Đang chờ';
    let statusClass = 'pending';
    let statusIcon = 'fa-clock';
    
    switch (status.toLowerCase()) {
        case 'đã xác nhận':
            statusClass = 'confirmed';
            statusIcon = 'fa-check-circle';
            break;
        case 'đã loại trừ':
            statusClass = 'rejected';
            statusIcon = 'fa-ban';
            break;
        case 'chờ xác minh':
        case 'đang chờ':
        default:
            statusClass = 'pending';
            statusIcon = 'fa-clock';
            break;
    }
    
    return {
        ...violation,
        formattedTime: timeStr,
        formattedId: violationId,
        vehicleIcon,
        statusClass,
        statusIcon,
        statusText: status
    };
}

// Hàm tạo card vi phạm
function createViolationCard(violation) {
    const card = document.createElement('div');
    card.className = `violation-card status-${violation.statusClass}`;
    
    // Lấy hình ảnh vi phạm (ưu tiên ảnh toàn cảnh)
    const imageUrl = violation.scene_image_url || violation.vehicle_image_url || violation.license_plate_image_url || '';
    
    // Tạo nội dung card
    card.innerHTML = `
        <div class="violation-card-header">
            <span class="violation-id">${violation.formattedId}</span>
            <span class="violation-time">${violation.formattedTime}</span>
        </div>
        ${imageUrl ? `<img src="${imageUrl}" alt="Ảnh vi phạm" class="violation-thumbnail">` : ''}
        <div class="violation-info">
            <div class="vehicle-type">
                <i class="fas ${violation.vehicleIcon}"></i>
                <span>${violation.vehicleType || 'Không xác định'}</span>
            </div>
            <div class="license-plate">
                <strong>Biển số:</strong> ${violation.licensePlate || 'Chưa xác định'}
            </div>
            <div class="violation-type">
                <strong>Vi phạm:</strong> ${violation.violation_type || 'Vượt đèn đỏ'}
            </div>
            <div class="violation-status ${violation.statusClass}">
                <i class="fas ${violation.statusIcon}"></i>
                <span>${violation.statusText}</span>
            </div>
        </div>
        <div class="violation-card-footer">
            <div class="violation-actions">
                <button class="btn-action" title="Xem chi tiết"><i class="fas fa-eye"></i></button>
                <button class="btn-action" title="Tải xuống ảnh"><i class="fas fa-download"></i></button>
            </div>
        </div>
    `;
                    
                    // Thêm sự kiện cho nút xem chi tiết
    const viewBtn = card.querySelector('.btn-action:first-child');
                    viewBtn.addEventListener('click', () => {
                        viewViolationDetails(violation);
                    });
                    
                    // Thêm sự kiện cho nút tải xuống
    const downloadBtn = card.querySelector('.btn-action:last-child');
                    downloadBtn.addEventListener('click', () => {
                        downloadViolationImage(violation);
                    });
    
    // Thêm sự kiện click cho thumbnail để xem chi tiết
    const thumbnail = card.querySelector('.violation-thumbnail');
    if (thumbnail) {
        thumbnail.addEventListener('click', () => {
            viewViolationDetails(violation);
        });
    }
    
    return card;
}

// Xem chi tiết vi phạm - Sử dụng dữ liệu từ cache khi có thể
function viewViolationDetails(violation) {
    const violationId = violation.id;
    
    // Kiểm tra xem có dữ liệu chi tiết trong cache không
    // Nếu có thì sử dụng cache thay vì gọi API
    if (clientCache.violationDetails && clientCache.violationDetails[violationId]) {
        const cachedViolation = clientCache.violationDetails[violationId];
        renderViolationDetails(cachedViolation);
    } else {
        renderViolationDetails(violation);
    }
}

// Hàm hiển thị chi tiết vi phạm
function renderViolationDetails(violation) {
    // Sử dụng hàm định dạng dữ liệu
    const formattedViolation = formatViolationData(violation);
    
    // Xử lý đường dẫn ảnh
    const sceneImageUrl = violation.scene_image || violation.scene_image_url || '';
    const vehicleImageUrl = violation.vehicle_image || violation.vehicle_image_url || '';
    const licensePlateImageUrl = violation.license_plate_image || violation.license_plate_image_url || '';

    // Tạo modal xem chi tiết vi phạm
    let modalHTML = `
        <div id="violation-modal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Chi tiết vi phạm</h3>
                    <button class="close-modal"><i class="fas fa-times"></i></button>
                </div>
                <div class="modal-body">
                    <div class="violation-details">
                        <div class="violation-info">
                            <p><strong>Mã vi phạm:</strong> ${formattedViolation.formattedId}</p>
                            <p><strong>Thời gian:</strong> ${formattedViolation.formattedTime}</p>
                            <p><strong>Loại phương tiện:</strong> ${violation.vehicleType || 'Không xác định'}</p>
                            <p><strong>Loại vi phạm:</strong> ${violation.violation_type || 'Vượt đèn đỏ'}</p>
                            <p><strong>Biển số xe:</strong> ${violation.licensePlate || 'Không xác định'}</p>
                            <p><strong>Trạng thái:</strong> ${formattedViolation.statusText}</p>
                            <p><strong>Độ tin cậy:</strong> ${Math.round((violation.confidence || 0) * 100)}%</p>
                        </div>
                        <div class="violation-images">
    `;
    
    // Thêm ảnh cảnh vi phạm nếu có
    if (sceneImageUrl) {
        modalHTML += `
            <div class="violation-image-container">
                <h4>Ảnh toàn cảnh vi phạm</h4>
                <img src="${sceneImageUrl}" alt="Ảnh toàn cảnh vi phạm" class="violation-image scene-image">
            </div>
        `;
    }
    
    // Thêm ảnh phương tiện nếu có
    if (vehicleImageUrl) {
        modalHTML += `
            <div class="violation-image-container">
                <h4>Ảnh phương tiện vi phạm</h4>
                <img src="${vehicleImageUrl}" alt="Ảnh phương tiện vi phạm" class="violation-image vehicle-image">
            </div>
        `;
    }
    
    // Thêm ảnh biển số nếu có
    if (licensePlateImageUrl) {
        modalHTML += `
            <div class="violation-image-container">
                <h4>Ảnh biển số xe</h4>
                <img src="${licensePlateImageUrl}" alt="Ảnh biển số xe" class="violation-image license-plate-image">
            </div>
        `;
    }
    
    // Đóng các thẻ và thêm nút xác nhận/loại trừ
    modalHTML += `
                        </div>
                    </div>
                </div>
                <div class="modal-footer violation-actions">
                    <button class="btn btn-danger reject-violation">Loại trừ vi phạm</button>
                    <button class="btn btn-primary confirm-violation">Xác nhận vi phạm</button>
                </div>
            </div>
        </div>
    `;
    
    // Thêm modal vào DOM
    const modalContainer = document.createElement('div');
    modalContainer.innerHTML = modalHTML;
    document.body.appendChild(modalContainer.firstElementChild);
    
    // Hiển thị modal
    const modal = document.getElementById('violation-modal');
    modal.classList.add('show');
    
    // Thêm sự kiện đóng modal
    const closeButtons = modal.querySelectorAll('.close-modal, .close-btn');
    closeButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            modal.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(modal);
            }, 300);
        });
    });

    // Thêm sự kiện click cho ảnh toàn cảnh để phóng to
    const sceneImage = modal.querySelector('.scene-image');
    if (sceneImage) {
        sceneImage.addEventListener('click', function() {
            showImageFullscreen(this.src);
        });
    }

    // Thêm sự kiện click cho ảnh phương tiện để phóng to
    const vehicleImage = modal.querySelector('.vehicle-image');
    if (vehicleImage) {
        vehicleImage.addEventListener('click', function() {
            showImageFullscreen(this.src);
        });
    }

    // Thêm sự kiện click cho ảnh biển số để phóng to
    const licensePlateImage = modal.querySelector('.license-plate-image');
    if (licensePlateImage) {
        licensePlateImage.addEventListener('click', function() {
            showImageFullscreen(this.src);
        });
    }

    // Thêm sự kiện cho nút xác nhận vi phạm
    const confirmBtn = modal.querySelector('.confirm-violation');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', function() {
            // Xử lý xác nhận vi phạm
            confirmViolation(violation.id);
            
            // Cập nhật trạng thái cho UI ngay lập tức
            violation.status = 'Đã xác nhận';
            
            // Tìm card liên quan đến vi phạm này và cập nhật UI
            updateViolationCardStatus(violation.id, 'confirmed', 'Đã xác nhận');
            
            // Đóng modal sau khi xác nhận
            modal.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(modal);
            }, 300);
        });
    }

    // Thêm sự kiện cho nút loại trừ vi phạm
    const rejectBtn = modal.querySelector('.reject-violation');
    if (rejectBtn) {
        rejectBtn.addEventListener('click', function() {
            // Xử lý loại trừ vi phạm
            rejectViolation(violation.id);
            
            // Cập nhật trạng thái cho UI ngay lập tức
            violation.status = 'Đã loại trừ';
            
            // Tìm card liên quan đến vi phạm này và cập nhật UI
            updateViolationCardStatus(violation.id, 'rejected', 'Đã loại trừ');
            
            // Đóng modal sau khi loại trừ
            modal.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(modal);
            }, 300);
        });
    }
}

// Xác nhận vi phạm
function confirmViolation(violationId) {
    // Thêm vi phạm vào danh sách đã xác nhận cục bộ
    confirmedViolations.add(violationId);
    
    // Xóa khỏi danh sách loại trừ (nếu có)
    rejectedViolations.delete(violationId);
    
    // Cập nhật ngay số lượng trong UI
    updateViolationCounters();

    // Gửi yêu cầu API để xác nhận vi phạm
    fetch('/api/confirm_violation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            violation_id: violationId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Hiển thị thông báo xác nhận
            showToast('Đã xác nhận vi phạm', 'success');
            
            // Không cập nhật dữ liệu từ server trong 5 giây để tránh mất trạng thái UI
        } else {
            showToast(`Lỗi: ${data.message}`, 'error');
            // Nếu lỗi, loại bỏ khỏi danh sách đã xác nhận
            confirmedViolations.delete(violationId);
            // Cập nhật lại bộ đếm
            updateViolationCounters();
        }
    })
    .catch(error => {
        console.error('Lỗi khi xác nhận vi phạm:', error);
        showToast('Đã xảy ra lỗi khi xác nhận vi phạm', 'error');
        // Nếu lỗi, loại bỏ khỏi danh sách đã xác nhận
        confirmedViolations.delete(violationId);
        // Cập nhật lại bộ đếm
        updateViolationCounters();
    });
}

// Loại trừ vi phạm
function rejectViolation(violationId) {
    // Thêm vi phạm vào danh sách đã loại trừ cục bộ
    rejectedViolations.add(violationId);
    
    // Xóa khỏi danh sách đã xác nhận (nếu có)
    confirmedViolations.delete(violationId);
    
    // Cập nhật ngay số lượng trong UI
    updateViolationCounters();
    
    // Gửi yêu cầu API để loại trừ vi phạm
    fetch('/api/reject_violation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            violation_id: violationId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Hiển thị thông báo loại trừ
            showToast('Đã loại trừ vi phạm', 'info');
            
            // Không cập nhật dữ liệu từ server trong 5 giây để tránh mất trạng thái UI
        } else {
            showToast(`Lỗi: ${data.message}`, 'error');
            // Nếu lỗi, loại bỏ khỏi danh sách đã loại trừ
            rejectedViolations.delete(violationId);
            // Cập nhật lại bộ đếm
            updateViolationCounters();
        }
    })
    .catch(error => {
        console.error('Lỗi khi loại trừ vi phạm:', error);
        showToast('Đã xảy ra lỗi khi loại trừ vi phạm', 'error');
        // Nếu lỗi, loại bỏ khỏi danh sách đã loại trừ
        rejectedViolations.delete(violationId);
        // Cập nhật lại bộ đếm
        updateViolationCounters();
    });
}



// Tải xuống ảnh vi phạm
function downloadViolationImage(violation) {
    // Ưu tiên ảnh toàn cảnh vi phạm
    const sceneImage = violation.scene_image || violation.scene_image_url;
    const vehicleImage = violation.vehicle_image || violation.vehicle_image_url;
    const licensePlateImage = violation.license_plate_image || violation.license_plate_image_url;
    
    const imageUrl = sceneImage || vehicleImage || licensePlateImage;
    
    if (!imageUrl) {
        showToast('Không có ảnh vi phạm để tải xuống', 'error');
        return;
    }
    
    // Hiển thị ảnh trước khi tải xuống
    showImageFullscreen(imageUrl);
    
    // Format mã vi phạm để đặt tên file
    let violationId;
    if (violation.id) {
        // Nếu ID đã là dạng số 5 chữ số, hiển thị như vậy
        if (/^\d{1,5}$/.test(violation.id)) {
            violationId = violation.id.toString().padStart(5, '0');
        } else {
            // Nếu ID không phải dạng số hoặc quá dài, sử dụng ID như được cấp
            violationId = violation.id.toString().substring(0, 5).padStart(5, '0');
        }
    } else {
        violationId = '00000';
    }
    
    // Tạo một thẻ a ẩn để tải xuống
    const downloadLink = document.createElement('a');
    downloadLink.href = imageUrl;
    downloadLink.download = `violation_${violationId}.jpg`;
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
    
    showToast('Đang tải xuống ảnh vi phạm', 'info');
}

// Cập nhật phân trang
function updatePagination(currentPage, totalPages) {
    const paginationInfo = document.querySelector('.pagination-info');
    if (paginationInfo) {
        paginationInfo.textContent = `Trang ${currentPage}/${totalPages}`;
    }
    
    const prevBtn = document.querySelector('.pagination-btn.prev');
    const nextBtn = document.querySelector('.pagination-btn.next');
    
    if (prevBtn) {
        prevBtn.disabled = currentPage === 1;
        prevBtn.style.opacity = currentPage === 1 ? '0.5' : '1';
    }
    
    if (nextBtn) {
        nextBtn.disabled = currentPage === totalPages;
        nextBtn.style.opacity = currentPage === totalPages ? '0.5' : '1';
    }
}

// Thiết lập các xử lý sự kiện
function setupEventListeners() {
    // Nút xuất CSV
    const csvBtn = document.querySelector('.btn-export:nth-child(1)');
    if (csvBtn) {
        csvBtn.addEventListener('click', () => {
            showToast('Đang xuất dữ liệu ra CSV...', 'info');
        });
    }
    
    // Nút xuất PDF
    const pdfBtn = document.querySelector('.btn-export:nth-child(2)');
    if (pdfBtn) {
        pdfBtn.addEventListener('click', () => {
            showToast('Đang xuất dữ liệu ra PDF...', 'success');
        });
    }
    
    // Thêm sự kiện cho các nút lọc vi phạm
    const pendingFilter = document.getElementById('pending-violations-filter');
    const confirmedFilter = document.getElementById('confirmed-violations-filter');
    
    // Biến lưu trạng thái bộ lọc hiện tại
    window.currentFilter = 'all'; // 'all', 'pending', 'confirmed'
    
    if (pendingFilter) {
        pendingFilter.addEventListener('click', () => {
            filterViolations('pending');
            
            // Cập nhật trạng thái active cho cards
            pendingFilter.classList.toggle('active');
            if (confirmedFilter) confirmedFilter.classList.remove('active');
            
            // Hiển thị thông báo
            if (pendingFilter.classList.contains('active')) {
                showToast('Hiển thị vi phạm đang chờ xác nhận', 'info');
                window.currentFilter = 'pending';
            } else {
                showToast('Hiển thị tất cả vi phạm', 'info');
                window.currentFilter = 'all';
            }
        });
    }
    
    if (confirmedFilter) {
        confirmedFilter.addEventListener('click', () => {
            filterViolations('confirmed');
            
            // Cập nhật trạng thái active cho cards
            confirmedFilter.classList.toggle('active');
            if (pendingFilter) pendingFilter.classList.remove('active');
            
            // Hiển thị thông báo
            if (confirmedFilter.classList.contains('active')) {
                showToast('Hiển thị vi phạm đã xác nhận', 'success');
                window.currentFilter = 'confirmed';
            } else {
                showToast('Hiển thị tất cả vi phạm', 'info');
                window.currentFilter = 'all';
            }
        });
    }
    
    // Nút tìm kiếm
    const searchBtn = document.querySelector('.btn-search');
    const searchInput = document.querySelector('.search-bar input');
    
    if (searchBtn && searchInput) {
        searchBtn.addEventListener('click', () => {
            const searchTerm = searchInput.value.trim();
            if (searchTerm) {
                showToast(`Đang tìm kiếm: "${searchTerm}"`, 'info');
                // Thực hiện tìm kiếm (có thể thêm API tìm kiếm trong tương lai)
            } else {
                showToast('Vui lòng nhập từ khóa tìm kiếm', 'error');
            }
        });
        
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                searchBtn.click();
            }
        });
    }
    
    // Nút phân trang
    const prevBtn = document.querySelector('.pagination-btn.prev');
    const nextBtn = document.querySelector('.pagination-btn.next');
    
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                updateViolations(currentPage);
                // Đưa trang lên đầu phần vi phạm khi nhấp vào prev
                document.querySelector('.violations-section').scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            if (currentPage < window.totalPages) {
                currentPage++;
                updateViolations(currentPage);
                // Đưa trang lên đầu phần vi phạm khi nhấp vào next
                document.querySelector('.violations-section').scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
    
    // Mô phỏng đèn giao thông thay đổi
    setTimeout(() => {
        simulateTrafficLights();
    }, 5000);
}

// Hàm simulateTrafficLights đã được định nghĩa trước đó

// Lấy dữ liệu thống kê từ API
async function getStats() {
    try {
        // Sử dụng cache để giảm số lượng requests đến server
        const data = await getDataWithCache('stats', '/api/get_stats');
        
        if (!data) return;
        
            // Cập nhật số lượng phương tiện
            const vehicleCounts = data.vehicle_counts || {};
            
            if (vehicleCounts.car !== undefined) updateVehicleCount('car', vehicleCounts.car);
            if (vehicleCounts.motorbike !== undefined) updateVehicleCount('motorcycle', vehicleCounts.motorbike);
            if (vehicleCounts.truck !== undefined) updateVehicleCount('truck', vehicleCounts.truck);
            if (vehicleCounts.bus !== undefined) updateVehicleCount('bus', vehicleCounts.bus);
            
            // Cập nhật trạng thái đèn giao thông
            if (data.traffic_light_status) {
                changeTrafficLight(data.traffic_light_status);
            }
    } catch (error) {
            console.error('Lỗi khi lấy dữ liệu thống kê:', error);
    }
}

// Hàm cập nhật trạng thái card vi phạm trong giao diện
function updateViolationCardStatus(violationId, newStatusClass, newStatusText) {
    // Cập nhật số lượng vi phạm trong giao diện
    updateViolationCounters();

    // Định dạng ID vi phạm để tìm kiếm
    let formattedId;
    if (/^\d{1,5}$/.test(violationId)) {
        formattedId = violationId.toString().padStart(5, '0');
    } else {
        formattedId = violationId.toString().substring(0, 5).padStart(5, '0');
    }
    
    // Tìm card vi phạm trong giao diện
    const cards = document.querySelectorAll('.violation-card');
    let targetCard = null;
    
    cards.forEach(card => {
        const idElement = card.querySelector('.violation-id');
        if (idElement && idElement.textContent === formattedId) {
            targetCard = card;
        }
    });
    
    if (!targetCard) {
        console.warn(`Không tìm thấy card vi phạm ID: ${formattedId}`);
        return;
    }
    
    // Xác định icon tương ứng với trạng thái mới
    let statusIcon = 'fa-clock';
    switch (newStatusClass) {
        case 'confirmed':
            statusIcon = 'fa-check-circle';
            break;
        case 'rejected':
            statusIcon = 'fa-ban';
            break;
        default:
            statusIcon = 'fa-clock';
            break;
    }
    
    // Cập nhật class cho card
    targetCard.className = `violation-card status-${newStatusClass}`;
    
    // Ẩn card nếu không khớp với bộ lọc hiện tại
    if (window.currentFilter === 'pending' && newStatusClass === 'confirmed') {
        targetCard.style.display = 'none';
    } else if (window.currentFilter === 'confirmed' && newStatusClass !== 'confirmed') {
        targetCard.style.display = 'none';
    }
    
    // Cập nhật phần tử hiển thị trạng thái
    const statusElement = targetCard.querySelector('.violation-status');
    if (statusElement) {
        statusElement.className = `violation-status ${newStatusClass}`;
        statusElement.innerHTML = `<i class="fas ${statusIcon}"></i><span>${newStatusText}</span>`;
    } else {
        // Nếu không tìm thấy phần tử, thêm mới vào
        const infoDiv = targetCard.querySelector('.violation-info');
        if (infoDiv) {
            const newStatusDiv = document.createElement('div');
            newStatusDiv.className = `violation-status ${newStatusClass}`;
            newStatusDiv.innerHTML = `<i class="fas ${statusIcon}"></i><span>${newStatusText}</span>`;
            infoDiv.appendChild(newStatusDiv);
        }
    }
}

// Hiển thị ảnh phóng to toàn màn hình
function showImageFullscreen(imageUrl) {
    // Tạo overlay cho ảnh phóng to
    const overlay = document.createElement('div');
    overlay.className = 'fullscreen-overlay';
    
    // Tạo container cho ảnh
    const imageContainer = document.createElement('div');
    imageContainer.className = 'fullscreen-image-container';
    
    // Tạo phần tử ảnh
    const image = document.createElement('img');
    image.src = imageUrl;
    image.className = 'fullscreen-image';
    image.alt = 'Ảnh vi phạm phóng to';
    
    // Tạo nút đóng
    const closeBtn = document.createElement('button');
    closeBtn.className = 'fullscreen-close-btn';
    closeBtn.innerHTML = '<i class="fas fa-times"></i>';
    
    // Thêm các phần tử vào container
    imageContainer.appendChild(image);
    imageContainer.appendChild(closeBtn);
    overlay.appendChild(imageContainer);
    document.body.appendChild(overlay);
    
    // Animation hiển thị
    setTimeout(() => {
        overlay.classList.add('active');
        imageContainer.classList.add('active');
    }, 10);
    
    // Xử lý sự kiện đóng
    const closeImage = () => {
        overlay.classList.remove('active');
        imageContainer.classList.remove('active');
        setTimeout(() => {
            document.body.removeChild(overlay);
        }, 300);
    };
    
    // Gắn sự kiện đóng
    closeBtn.addEventListener('click', closeImage);
    
    // Đóng khi click vào overlay
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            closeImage();
        }
    });
    
    // Đóng khi nhấn ESC
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeImage();
        }
    });
}

// Mô phỏng đèn giao thông thay đổi
function simulateTrafficLights() {
    const lightSequence = ['yellow'];
    let currentIndex = 0;
    
    const interval = setInterval(() => {
        currentIndex = (currentIndex + 1) % lightSequence.length;
        changeTrafficLight(lightSequence[currentIndex]);
    }, 5000); // Thay đổi mỗi 5 giây
    
    // Dừng mô phỏng sau 1 phút
    setTimeout(() => {
        clearInterval(interval);
    }, 60000);
}

// Hàm lọc vi phạm theo trạng thái
function filterViolations(status) {
    const violationCards = document.querySelectorAll('.violation-card');
    
    // Nếu không có card nào, thoát khỏi hàm
    if (!violationCards.length) return;
    
    // Lấy phần tử "Không có vi phạm"
    const noViolationsDiv = document.querySelector('.no-violations');
    
    // Đếm số vi phạm hiển thị
    let visibleCount = 0;
    
    violationCards.forEach(card => {
        // Xác định trạng thái của card
        const isConfirmed = card.classList.contains('status-confirmed');
        const isPending = card.classList.contains('status-pending') || 
                         (!card.classList.contains('status-confirmed') && 
                          !card.classList.contains('status-rejected'));
        const isRejected = card.classList.contains('status-rejected');
        
        if (status === 'all') {
            // Hiển thị tất cả card
            card.style.display = 'block';
            visibleCount++;
        } else if (status === 'pending' && isPending) {
            // Chỉ hiển thị card đang chờ
            card.style.display = 'block';
            visibleCount++;
        } else if (status === 'confirmed' && isConfirmed) {
            // Chỉ hiển thị card đã xác nhận
            card.style.display = 'block';
            visibleCount++;
        } else {
            // Ẩn card không phù hợp
            card.style.display = 'none';
        }
    });
    
    // Hiển thị thông báo "Không có vi phạm" nếu không có card nào được hiển thị
    if (noViolationsDiv) {
        if (visibleCount === 0) {
            noViolationsDiv.style.display = 'flex';
            
            // Cập nhật nội dung thông báo tùy theo bộ lọc
            const infoText = noViolationsDiv.querySelector('p');
            if (infoText) {
                if (status === 'pending') {
                    infoText.textContent = 'Không có vi phạm đang chờ xác nhận';
                } else if (status === 'confirmed') {
                    infoText.textContent = 'Không có vi phạm đã xác nhận';
                } else {
                    infoText.textContent = 'Không có dữ liệu vi phạm';
                }
            }
        } else {
            noViolationsDiv.style.display = 'none';
        }
    }
}

// Hàm cập nhật bộ đếm vi phạm trong UI
function updateViolationCounters() {
    const totalViolationsCount = document.getElementById('total-violations');
    const confirmedViolationsCount = document.getElementById('confirmed-violations');
    
    // Lấy dữ liệu tổng số vi phạm từ cache hoặc server
    let totalViolations = 0;
    
    if (clientCache.violations && clientCache.violations.data && 
        clientCache.violations.data.total !== undefined) {
        // Sử dụng dữ liệu từ cache
        totalViolations = clientCache.violations.data.total;
    } else {
        // Fallback: đếm số lượng card hiện tại + số lượng trong bộ đếm hiện tại
        const pendingElement = document.getElementById('total-violations');
        totalViolations = pendingElement ? parseInt(pendingElement.textContent) || 0 : 0;
        const confirmedElement = document.getElementById('confirmed-violations');
        const confirmedNumber = confirmedElement ? parseInt(confirmedElement.textContent) || 0 : 0;
        
        totalViolations += confirmedNumber;
    }
    
    // Tính toán số vi phạm đang chờ
    const pendingCount = Math.max(0, totalViolations - confirmedViolations.size - rejectedViolations.size);
    
    // Cập nhật UI
    if (totalViolationsCount) {
        totalViolationsCount.textContent = pendingCount;
    }
    
    if (confirmedViolationsCount) {
        confirmedViolationsCount.textContent = confirmedViolations.size;
    }
}

