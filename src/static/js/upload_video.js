/**
 * upload_video.js - Chức năng tải video lên hệ thống giám sát giao thông
 * Tác giả: Nhóm Danh Khoa
 * Ngày: 2024
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM đã sẵn sàng - Khởi tạo chức năng tải video');
    
    // Kiểm tra cấu trúc DOM
    checkDOMStructure();
    
    // Lấy tham chiếu đến nút "Tải video lên"
    const uploadButton = document.querySelector('.header-actions .btn-primary');
    if (!uploadButton) {
        console.error('Không tìm thấy nút tải video lên');
        return;
    }
    
    // Tạo phần tử input ẩn để chọn file
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'video/*';
    fileInput.style.display = 'none';
    fileInput.id = 'video-upload-input';
    document.body.appendChild(fileInput);
    
    // Tạo modal cho việc tải video lên
    createUploadModal();
    
    // Thêm sự kiện cho nút tải lên
    uploadButton.addEventListener('click', function() {
        openUploadModal();
    });
    
    // Xử lý sự kiện khi người dùng chọn file
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            const file = e.target.files[0];
            displaySelectedFile(file);
        }
    });
});

/**
 * Kiểm tra cấu trúc DOM để đảm bảo các phần tử cần thiết tồn tại
 */
function checkDOMStructure() {
    console.log('Kiểm tra cấu trúc DOM...');
    
    // Kiểm tra phần tử hiển thị số lượng phương tiện
    const vehicleStats = document.querySelector('.vehicle-stats');
    if (vehicleStats) {
        console.log('Tìm thấy phần tử .vehicle-stats');
        
        // Kiểm tra các stat-card
        const statCards = vehicleStats.querySelectorAll('.stat-card');
        console.log(`Số lượng phần tử .stat-card: ${statCards.length}`);
        
        // Kiểm tra từng loại phương tiện
        const carContainer = vehicleStats.querySelector('.icon-container.car');
        const motorcycleContainer = vehicleStats.querySelector('.icon-container.motorcycle');
        const truckContainer = vehicleStats.querySelector('.icon-container.truck');
        const busContainer = vehicleStats.querySelector('.icon-container.bus');
        
        console.log(`Phần tử .icon-container.car: ${carContainer ? 'Tìm thấy' : 'Không tìm thấy'}`);
        console.log(`Phần tử .icon-container.motorcycle: ${motorcycleContainer ? 'Tìm thấy' : 'Không tìm thấy'}`);
        console.log(`Phần tử .icon-container.truck: ${truckContainer ? 'Tìm thấy' : 'Không tìm thấy'}`);
        console.log(`Phần tử .icon-container.bus: ${busContainer ? 'Tìm thấy' : 'Không tìm thấy'}`);
    } else {
        console.error('Không tìm thấy phần tử .vehicle-stats');
    }
    
    // Kiểm tra phần tử hiển thị trạng thái đèn giao thông
    const trafficLightStatus = document.querySelector('.traffic-light-status');
    if (trafficLightStatus) {
        console.log('Tìm thấy phần tử .traffic-light-status');
        
        // Kiểm tra các đèn
        const lights = trafficLightStatus.querySelectorAll('.light');
        console.log(`Số lượng phần tử .light: ${lights.length}`);
        
        // Kiểm tra từng loại đèn
        const redLight = trafficLightStatus.querySelector('.light.red');
        const yellowLight = trafficLightStatus.querySelector('.light.yellow');
        const greenLight = trafficLightStatus.querySelector('.light.green');
        
        console.log(`Phần tử .light.red: ${redLight ? 'Tìm thấy' : 'Không tìm thấy'}`);
        console.log(`Phần tử .light.yellow: ${yellowLight ? 'Tìm thấy' : 'Không tìm thấy'}`);
        console.log(`Phần tử .light.green: ${greenLight ? 'Tìm thấy' : 'Không tìm thấy'}`);
    } else {
        console.error('Không tìm thấy phần tử .traffic-light-status');
    }
}

/**
 * Tạo modal dialog cho việc tải video lên
 */
function createUploadModal() {
    const modalHTML = `
        <div id="upload-modal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Tải video lên hệ thống</h3>
                    <button class="close-modal"><i class="fas fa-times"></i></button>
                </div>
                <div class="modal-body">                    <div class="upload-area" id="drop-zone">                        <i class="fas fa-cloud-upload-alt"></i>
                        <p>Kéo và thả video vào đây hoặc <span class="select-file-btn">chọn file</span></p>
                        <p class="file-info">Hỗ trợ: MP4, AVI, MOV (tối đa 2GB)</p>
                        <p class="file-info-note">(Video sẽ được xử lý trực tiếp trong trình duyệt)</p>
                    </div>
                    <div class="selected-file-info hidden">
                        <div class="file-preview">
                            <video id="video-preview" controls></video>
                        </div>
                        <div class="file-details">
                            <div class="file-name"><i class="fas fa-video"></i> <span id="file-name-text">video.mp4</span></div>
                            <div class="file-size"><i class="fas fa-weight"></i> <span id="file-size-text">0 MB</span></div>
                            <div class="file-duration"><i class="fas fa-clock"></i> <span id="file-duration-text">00:00</span></div>
                            <button class="btn btn-outline change-file-btn">Thay đổi video</button>
                        </div>
                    </div>
                    <div class="upload-progress hidden">
                        <div class="progress-text">Đang tải lên... <span class="progress-percent">0%</span></div>
                        <div class="progress-bar">
                            <div class="progress-fill"></div>
                        </div>
                    </div>
                    <div class="upload-result hidden">
                        <div class="success-message">
                            <i class="fas fa-check-circle"></i>
                            <p>Video đã được tải lên thành công!</p>
                        </div>
                        <div class="error-message hidden">
                            <i class="fas fa-exclamation-circle"></i>
                            <p>Có lỗi xảy ra khi tải video! Vui lòng thử lại.</p>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-outline cancel-btn">Hủy bỏ</button>
                    <button class="btn btn-primary upload-btn" disabled>Tải lên</button>
                </div>
            </div>
        </div>
    `;
    
    // Thêm modal vào DOM
    const modalContainer = document.createElement('div');
    modalContainer.innerHTML = modalHTML;
    document.body.appendChild(modalContainer.firstElementChild);
    
    // Thêm các bộ lắng nghe sự kiện cho modal
    setupModalListeners();
}

/**
 * Thiết lập các sự kiện cho modal
 */
function setupModalListeners() {
    const modal = document.getElementById('upload-modal');
    if (!modal) {
        console.error('Không tìm thấy modal');
        return;
    }
    
    const closeButton = modal.querySelector('.close-modal');
    const cancelButton = modal.querySelector('.cancel-btn');
    const uploadButton = modal.querySelector('.modal-footer .upload-btn'); // Chọn đúng nút tải lên trong modal
    const dropZone = document.getElementById('drop-zone');
    const selectFileBtn = modal.querySelector('.select-file-btn');
    const changeFileBtn = modal.querySelector('.change-file-btn');
    const fileInput = document.getElementById('video-upload-input');
    
    // Kiểm tra xem các phần tử quan trọng có tồn tại không
    if (!uploadButton) {
        console.error('Không tìm thấy nút tải lên trong modal');
    }
    
    if (!fileInput) {
        console.error('Không tìm thấy input file');
    }
    
    // Đóng modal
    closeButton.addEventListener('click', closeUploadModal);
    cancelButton.addEventListener('click', closeUploadModal);
    
    // Chọn file khi nhấp vào nút chọn file
    selectFileBtn.addEventListener('click', () => fileInput.click());
    changeFileBtn.addEventListener('click', () => fileInput.click());
    
    // Kéo và thả file
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        
        if (e.dataTransfer.files.length > 0) {
            const file = e.dataTransfer.files[0];
            if (file.type.startsWith('video/')) {
                fileInput.files = e.dataTransfer.files;
                displaySelectedFile(file);
            } else {
                showToast('Chỉ chấp nhận file video!', 'error');
            }
        }
    });    // Sự kiện tải lên
    if (uploadButton) {
        console.log('Gắn sự kiện cho nút tải lên');
        
        // Xóa tất cả các event listener cũ (nếu có)
        uploadButton.replaceWith(uploadButton.cloneNode(true));
        
        // Lấy lại nút sau khi clone
        const newUploadButton = modal.querySelector('.modal-footer .upload-btn');
        
        // Gắn sự kiện mới
        newUploadButton.addEventListener('click', function(e) {
            e.preventDefault(); // Ngăn chặn hành vi mặc định
            e.stopPropagation(); // Ngăn chặn lan truyền sự kiện
            console.log('Nút tải lên đã được nhấp');
            
            // Gọi hàm tải lên sau một khoảng thời gian ngắn để đảm bảo UI được cập nhật
            setTimeout(() => {
                uploadVideo();
            }, 10);
        });
    }
}

/**
 * Mở modal tải lên
 */
function openUploadModal() {
    const modal = document.getElementById('upload-modal');
    modal.classList.add('show');
    document.body.classList.add('modal-open');
}

/**
 * Đóng modal tải lên
 */
function closeUploadModal() {
    const modal = document.getElementById('upload-modal');
    modal.classList.remove('show');
    document.body.classList.remove('modal-open');
    
    // Reset form
    resetUploadForm();
}

/**
 * Reset form upload
 */
function resetUploadForm() {
    const fileInput = document.getElementById('video-upload-input');
    fileInput.value = '';
    
    const dropZone = document.getElementById('drop-zone');
    const selectedFileInfo = document.querySelector('.selected-file-info');
    const uploadProgress = document.querySelector('.upload-progress');
    const uploadResult = document.querySelector('.upload-result');
    const uploadButton = document.querySelector('.upload-btn');
    
    dropZone.classList.remove('hidden');
    selectedFileInfo.classList.add('hidden');
    uploadProgress.classList.add('hidden');
    uploadResult.classList.add('hidden');
    uploadButton.disabled = true;
    
    // Reset video preview
    const videoPreview = document.getElementById('video-preview');
    if (videoPreview.src) {
        URL.revokeObjectURL(videoPreview.src);
        videoPreview.src = '';
    }
}

/**
 * Hiển thị thông tin file đã chọn
 */
function displaySelectedFile(file) {
    // Kiểm tra kích thước file (tối đa 2GB)
    const maxSize = 2 * 1024 * 1024 * 1024; // 2GB
    if (file.size > maxSize) {
        showToast('File vượt quá kích thước cho phép (2GB)', 'error');
        return;
    }
    
    // Lấy các phần tử trên giao diện
    const dropZone = document.getElementById('drop-zone');
    const selectedFileInfo = document.querySelector('.selected-file-info');
    const uploadButton = document.querySelector('.upload-btn');
    const fileNameText = document.getElementById('file-name-text');
    const fileSizeText = document.getElementById('file-size-text');
    const fileDurationText = document.getElementById('file-duration-text');
    const videoPreview = document.getElementById('video-preview');
    
    // Cập nhật thông tin file
    fileNameText.textContent = file.name;
    
    // Hiển thị kích thước file
    const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
    fileSizeText.textContent = `${fileSizeMB} MB`;
    
    // Tạo URL cho xem trước video
    if (videoPreview.src) {
        URL.revokeObjectURL(videoPreview.src);
    }
    videoPreview.src = URL.createObjectURL(file);
    
    // Lấy thời lượng video
    videoPreview.onloadedmetadata = function() {
        const duration = videoPreview.duration;
        const minutes = Math.floor(duration / 60);
        const seconds = Math.floor(duration % 60);
        fileDurationText.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    };
    
    // Hiển thị khu vực thông tin file và ẩn khu vực kéo thả
    dropZone.classList.add('hidden');
    selectedFileInfo.classList.remove('hidden');
    
    // Kích hoạt nút tải lên
    uploadButton.disabled = false;
}

/**
 * Bắt đầu cập nhật video stream từ server
 */
function startVideoStream() {
    console.log('Bắt đầu cập nhật video stream');
    
    // Đánh dấu đang xử lý video
    window.isProcessingVideo = true;
    
    // Dừng cập nhật hiện tại nếu có
    if (window.videoStreamInterval) {
        clearInterval(window.videoStreamInterval);
        console.log('Đã dừng interval cũ');
    }
    
    if (window.statsInterval) {
        clearInterval(window.statsInterval);
        console.log('Đã dừng interval thống kê cũ');
    }
    
    // Đặt lại số lỗi liên tiếp và số frame thành công
    window.consecutiveErrors = 0;
    window.successfulFrames = 0;
    
    // Xóa phần tử hiển thị cũ nếu có
    const videoStream = document.querySelector('.video-stream');
    if (videoStream) {
        // Xóa canvas cũ nếu có
        const oldCanvas = videoStream.querySelector('canvas.stream-canvas');
        if (oldCanvas) {
            videoStream.removeChild(oldCanvas);
            console.log('Đã xóa canvas cũ');
        }
        
        // Xóa img cũ nếu có
        const oldImg = videoStream.querySelector('img.frame-img');
        if (oldImg) {
            videoStream.removeChild(oldImg);
            console.log('Đã xóa img cũ');
        }
        
        // Tạo img mới
        const newImg = document.createElement('img');
        newImg.className = 'frame-img';
        newImg.style.position = 'absolute';
        newImg.style.top = '50%';
        newImg.style.left = '50%';
        newImg.style.transform = 'translate(-50%, -50%)';
        newImg.style.maxWidth = '100%';
        newImg.style.maxHeight = '100%';
        newImg.style.width = 'auto';
        newImg.style.height = 'auto';
        newImg.style.zIndex = '5';
        newImg.style.objectFit = 'contain';
        newImg.style.imageRendering = 'high-quality';
        newImg.style.backfaceVisibility = 'hidden';
        newImg.style.willChange = 'transform';
        newImg.alt = 'Video stream';
    
        // Hiển thị thông báo "Đang tải..."
        newImg.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(`
            <svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
                <rect width="1280" height="720" fill="#1a1a1a"/>
                <text x="640" y="340" font-family="Arial" font-size="30" fill="white" text-anchor="middle">Đang tải video...</text>
                <text x="640" y="380" font-family="Arial" font-size="20" fill="#4CAF50" text-anchor="middle">Đang khởi tạo mô hình...</text>
            </svg>
        `);
        
        videoStream.appendChild(newImg);
        console.log('Đã tạo img mới');
    
        // Ẩn video gốc
        const originalVideo = document.getElementById('traffic-video');
        if (originalVideo) {
            originalVideo.style.display = 'none';
            console.log('Đã ẩn video gốc');
        }
    }
    
    // Cập nhật trạng thái hiển thị
    updateLiveIndicator('Đang khởi tạo...');
    
    
    // Kiểm tra server đã sẵn sàng chưa trước khi bắt đầu cập nhật frame
    function checkServerReady() {
        fetch('/api/get_stats')
            .then(response => {
                if (response.ok) {
                    return response.json();
                }
                throw new Error('Server chưa sẵn sàng');
            })
            .then(data => {
                console.log('Server đã sẵn sàng, bắt đầu cập nhật frame');
                startIntervals();
            })
            .catch(error => {
                console.log('Đang đợi server sẵn sàng...', error);
                setTimeout(checkServerReady, 1000); // Thử lại sau 1 giây
            });
    }
    
    // Bắt đầu các interval cập nhật
    function startIntervals() {
        // Cập nhật trạng thái hiển thị
        updateLiveIndicator('Đang giám sát');
        
        // Hiển thị thông báo
        showToast('Đang giám sát video', 'success');
        
        // Cập nhật frame từ server với tần suất cao hơn để tăng FPS
        console.log('Thiết lập interval mới để cập nhật frame với tốc độ tối ưu');
        window.videoStreamInterval = setInterval(updateVideoFrame, 80); // Tăng lên 12.5 FPS (từ 10 FPS)
        
        // Bắt đầu cập nhật thống kê thường xuyên hơn
        console.log('Thiết lập interval mới để cập nhật thống kê');
        window.statsInterval = setInterval(updateStats, 1000); // Cập nhật mỗi giây
        
        // Cập nhật ngay lập tức để không phải đợi interval đầu tiên
        updateStats();
    }
    
    // Đợi một chút trước khi kiểm tra server
    setTimeout(checkServerReady, 3000);
}

/**
 * Dừng cập nhật video stream
 */
function stopVideoStream() {
    console.log('Dừng cập nhật video stream');
    
    // Đánh dấu không còn xử lý video
    window.isProcessingVideo = false;
    
    // Dừng các interval
    if (window.videoStreamInterval) {
        clearInterval(window.videoStreamInterval);
        window.videoStreamInterval = null;
        console.log('Đã dừng interval cập nhật frame');
    }
    
    if (window.statsInterval) {
        clearInterval(window.statsInterval);
        window.statsInterval = null;
        console.log('Đã dừng interval cập nhật thống kê');
    }
    
    // Reset biến đếm lỗi và frame
    window.consecutiveErrors = 0;
    window.successfulFrames = 0;
    
    // Cập nhật trạng thái hiển thị
    updateLiveIndicator('Đã dừng phát video');
    
    // Gửi yêu cầu dừng xử lý video đến server
    fetch('/api/stop_processing', {
        method: 'POST'
    })
    .then(response => response.json())
    .catch(error => {
        console.error('Lỗi khi gửi yêu cầu dừng xử lý:', error);
    });
    
    // Xóa các phần tử hiển thị nếu cần
    const videoStream = document.querySelector('.video-stream');
    if (videoStream) {
        // Xóa img cũ nếu có
        const oldImg = videoStream.querySelector('img.frame-img');
        if (oldImg) {
            videoStream.removeChild(oldImg);
            console.log('Đã xóa img frame cũ');
        }
        
        // Hiển thị lại video gốc
        const originalVideo = document.getElementById('traffic-video');
        if (originalVideo) {
            originalVideo.style.display = '';
            console.log('Đã hiển thị lại video gốc');
        }
    }
}

// Thêm hàm throttle để giới hạn tần suất gọi API
function throttle(func, limit) {
    let inThrottle;
    let lastResult;
    return function(...args) {
        if (!inThrottle) {
            inThrottle = true;
            lastResult = func.apply(this, args);
            setTimeout(() => inThrottle = false, limit);
        }
        return lastResult;
    }
}

// Tạo phiên bản throttled của các hàm gọi API
const throttledUpdateVideoFrame = throttle(function() {
    // Thêm timestamp để tránh cache
    const timestamp = new Date().getTime();
    const frameUrl = `/api/get_latest_frame?t=${timestamp}`;
    
    // Giảm số lượng log để tránh làm chậm console
    const shouldLog = Math.random() < 0.0001; // Giảm log xuống còn 0.01% các lần cập nhật (từ 0.1%)
    if (shouldLog) {
        console.log(`Đang tải frame từ: ${frameUrl}`);
    }
    
    // Kiểm tra xem có đang xử lý video không
    if (!window.isProcessingVideo) {
        if (shouldLog) {
            console.log('Không có video đang được xử lý, bỏ qua cập nhật frame');
        }
        return;
    }
    
    // Lấy hoặc tạo phần tử img để hiển thị frame
    const videoStream = document.querySelector('.video-stream');
    if (!videoStream) {
        console.error('Không tìm thấy phần tử .video-stream');
        return;
    }
    
    let frameImg = videoStream.querySelector('img.frame-img');
            
    // Tạo img nếu chưa có
    if (!frameImg) {
        if (shouldLog) {
            console.log('Tạo img mới cho stream');
        }
        const newImg = document.createElement('img');
        newImg.className = 'frame-img';
        newImg.style.position = 'absolute';
        newImg.style.top = '50%';
        newImg.style.left = '50%';
        newImg.style.transform = 'translate(-50%, -50%)';
        newImg.style.maxWidth = '100%';
        newImg.style.maxHeight = '100%';
        newImg.style.width = 'auto';
        newImg.style.height = 'auto';
        newImg.style.zIndex = '5';
        newImg.style.objectFit = 'contain';
        // Thêm thuộc tính để cải thiện hiệu suất hiển thị
        newImg.style.imageRendering = 'high-quality';
        newImg.style.backfaceVisibility = 'hidden';
        newImg.style.willChange = 'transform';
        newImg.alt = 'Video stream';
        videoStream.appendChild(newImg);
        frameImg = newImg;
        
        // Ẩn video gốc
        const originalVideo = document.getElementById('traffic-video');
        if (originalVideo) {
            originalVideo.style.display = 'none';
            if (shouldLog) {
                console.log('Đã ẩn video gốc');
            }
        }
    }
    
    // Ghi lại thời điểm bắt đầu tải frame để kiểm soát tốc độ
    const requestStartTime = performance.now();
    
    try {
        // Sử dụng fetch API với priority hints để tăng độ ưu tiên
        const fetchOptions = { 
            cache: 'no-store', // Đảm bảo không sử dụng cache
            priority: 'high', // Đánh dấu request này có độ ưu tiên cao
            keepalive: true // Giữ kết nối mở để tăng tốc các request tiếp theo
        };
        
        fetch(frameUrl, fetchOptions)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.blob();
        })
        .then(blob => {
            // Tạo URL từ blob
            const objectURL = URL.createObjectURL(blob);
            
            // Cập nhật src của img
            frameImg.src = objectURL;
            
            // Giải phóng URL sau khi img đã load
            frameImg.onload = () => {
                URL.revokeObjectURL(objectURL);
                
                // Tính thời gian đã tải frame
                const loadTime = performance.now() - requestStartTime;
                
                // Giảm số lượng log để tránh làm chậm console
                if (shouldLog) {
                    console.log(`Đã tải frame trong ${loadTime.toFixed(1)}ms`);
                }
                
                // Đặt lại số lỗi liên tiếp và tăng số frame thành công
                window.consecutiveErrors = 0;
                window.successfulFrames++;
            };
        })
        .catch(error => {
            // Xử lý lỗi
            window.consecutiveErrors = (window.consecutiveErrors || 0) + 1;
            
            // Chỉ log lỗi nếu là lỗi đầu tiên hoặc theo tỷ lệ nhất định
            if (window.consecutiveErrors === 1 || window.consecutiveErrors % 50 === 0) { // Tăng từ 20 lên 50
                console.warn(`Lỗi khi tải frame (lần thứ ${window.consecutiveErrors}): ${error.message}`);
            }
            
            // Nếu có quá nhiều lỗi liên tiếp, có thể server đã dừng xử lý
            if (window.consecutiveErrors > 100) { // Tăng từ 50 lên 100 để giảm false positive
                handleFrameError('Có quá nhiều lỗi liên tiếp, có thể server đã dừng xử lý');
            }
        });
    } catch (error) {
        console.warn(`Lỗi ngoài fetch: ${error.message}`);
    }
}, 100); // Giảm khoảng thời gian giữa các lần gọi API xuống 100ms (từ 150ms) để tăng FPS

/**
 * Cập nhật frame video từ server
 */
function updateVideoFrame() {
    throttledUpdateVideoFrame();
}

// Tạo phiên bản throttled của hàm cập nhật thống kê
const throttledUpdateStats = throttle(function() {
    // Tăng tỷ lệ log để debug
    const shouldLog = Math.random() < 0.2; // Log 20% các lần cập nhật
    
    // Thêm timestamp để tránh cache
    const timestamp = new Date().getTime();
    
    try {
        fetch(`/api/get_stats?t=${timestamp}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Log dữ liệu nhận được từ API để debug
                console.log('Dữ liệu thống kê từ API:', JSON.stringify(data));
                
                // Thêm log chi tiết để kiểm tra keys trong data.vehicle_counts
                if (data && data.vehicle_counts) {
                    console.log('Keys trong vehicle_counts:', Object.keys(data.vehicle_counts));
                }
                
                try {
                    // Cập nhật số lượng phương tiện
                    if (data && data.vehicle_counts) {
                        // Log chi tiết số lượng phương tiện
                        console.log('Số lượng phương tiện:', JSON.stringify(data.vehicle_counts));
                        
                        // Tổng hợp số xe máy từ tất cả các dạng có thể
                        const motorbikesTotal = (data.vehicle_counts.motorbike || 0) + 
                                               (data.vehicle_counts.motorcycle || 0) + 
                                               (data.vehicle_counts.motorbikes || 0);
                        
                        // Cập nhật từng loại phương tiện
                        updateVehicleCount('car', data.vehicle_counts.car || 0);
                        // Cập nhật tổng số xe máy đã tổng hợp
                        updateVehicleCount('motorcycle', motorbikesTotal);
                        updateVehicleCount('truck', data.vehicle_counts.truck || 0);
                        updateVehicleCount('bus', data.vehicle_counts.bus || 0);
                        
                        // Hiển thị tổng số phương tiện trong console
                        const total = (data.vehicle_counts.car || 0) + 
                                    motorbikesTotal + 
                                    (data.vehicle_counts.truck || 0) + 
                                    (data.vehicle_counts.bus || 0);
                        console.log(`Tổng số phương tiện: ${total}`);
        } else {
                        console.warn('Không có dữ liệu vehicle_counts trong phản hồi API hoặc dữ liệu không hợp lệ');
                    }
                    
                    // Cập nhật trạng thái đèn giao thông
                    if (data && data.traffic_light_status) {
                        console.log(`Trạng thái đèn giao thông từ API: ${data.traffic_light_status}`);
                        updateTrafficLight(data.traffic_light_status);
                    } else {
                        console.warn('Không có dữ liệu traffic_light_status trong phản hồi API hoặc dữ liệu không hợp lệ');
                    }
                } catch (error) {
                    console.error('Lỗi khi xử lý dữ liệu từ API:', error);
                }
            })
            .catch(error => {
                console.error('Lỗi khi lấy thống kê:', error);
            });
    } catch (error) {
        console.error('Lỗi ngoài fetch:', error);
    }
}, 500); // Giảm xuống 500ms để cập nhật thường xuyên hơn

/**
 * Cập nhật thống kê từ server
 */
function updateStats() {
    // Gọi trực tiếp hàm throttled để cập nhật thống kê
    throttledUpdateStats();
    
    // Chỉ in log mỗi 10 lần gọi để giảm số lượng log
    if (!window.statsUpdateCounter) window.statsUpdateCounter = 0;
    window.statsUpdateCounter++;
    
    if (window.statsUpdateCounter % 10 === 0) {
        console.log(`Đã gọi hàm cập nhật thống kê ${window.statsUpdateCounter} lần`);
    }
    
    // Chỉ cập nhật danh sách vi phạm mỗi 5 lần gọi updateStats
    if (!window.violationUpdateCounter) window.violationUpdateCounter = 0;
    window.violationUpdateCounter++;
    
    if (window.violationUpdateCounter >= 5) {
        window.violationUpdateCounter = 0;
        updateViolations();
    }
}

/**
 * Cập nhật số lượng phương tiện
 */
function updateVehicleCount(type, count) {
    console.log(`Đang cập nhật số lượng ${type}: ${count}`);
    
    try {
        // Ánh xạ loại phương tiện từ API sang class CSS và tiếng Việt
        const typeMap = {
            'car': { class: 'car', text: 'Ô tô' },
            'motorbike': { class: 'motorcycle', text: 'Xe máy' },
            'motorcycle': { class: 'motorcycle', text: 'Xe máy' },
            'motorbikes': { class: 'motorcycle', text: 'Xe máy' },
            'truck': { class: 'truck', text: 'Xe tải' },
            'bus': { class: 'bus', text: 'Xe buýt' }
        };
        
        // Lấy thông tin CSS và text tương ứng
        const typeInfo = typeMap[type] || { class: type, text: type };
        
        // Tìm phần tử hiển thị số lượng dựa trên class
        const statCards = document.querySelectorAll('.stat-card');
        let updated = false;
        
        // Duyệt qua từng stat-card để tìm phần tử phù hợp
        statCards.forEach(card => {
            const iconContainer = card.querySelector('.icon-container');
            if (iconContainer && iconContainer.classList.contains(typeInfo.class)) {
                const statInfo = card.querySelector('.stat-info');
                if (statInfo) {
                    const h3Element = statInfo.querySelector('h3');
                    if (h3Element) {
                        // Cập nhật số lượng
                        h3Element.textContent = count;
                        console.log(`Đã cập nhật số lượng ${typeInfo.text}: ${count}`);
                        updated = true;
                    }
                }
            }
        });
        
        if (!updated) {
            console.warn(`Không thể cập nhật số lượng cho ${typeInfo.text} (${type})`);
        }
    } catch (error) {
        console.error(`Lỗi khi cập nhật số lượng ${type}:`, error);
    }
}

/**
 * Cập nhật trạng thái đèn giao thông
 */
function updateTrafficLight(status) {
    console.log(`Đang cập nhật trạng thái đèn giao thông: ${status}`);
    
    try {
        // Lấy tất cả các đèn giao thông
        const lightContainers = document.querySelectorAll('.traffic-light-status .light-container');
        const lights = document.querySelectorAll('.traffic-light-status .light');
        
        console.log(`Số lượng light-container: ${lightContainers.length}, số lượng light: ${lights.length}`);
        
        if (lights.length === 0) {
            console.warn('Không tìm thấy phần tử .light trong .traffic-light-status');
            return;
        }
        
        // Xóa trạng thái active của tất cả đèn
        lights.forEach(light => light.classList.remove('active'));
        
        // Nếu trạng thái là unknown, không kích hoạt đèn nào
        if (!status || status === 'unknown') {
            console.log('Trạng thái đèn không xác định, không kích hoạt đèn nào');
            return;
        }
        
        // Xác định đèn nào cần kích hoạt dựa trên trạng thái
        let activeClass = '';
        switch(status) {
            case 'red':
                activeClass = 'red';
                break;
            case 'green':
                activeClass = 'green';
                break;
            case 'yellow':
                activeClass = 'yellow';
                break;
            default:
                console.warn(`Trạng thái đèn không hợp lệ: ${status}`);
                return;
        }
        
        // Kích hoạt đèn tương ứng
        if (activeClass) {
            // Tìm đèn theo class
            let activeLight = null;
            
            // Duyệt qua từng đèn để tìm đèn phù hợp
            for (let i = 0; i < lights.length; i++) {
                if (lights[i].classList.contains(activeClass)) {
                    activeLight = lights[i];
                    break;
                }
            }
            
            if (activeLight) {
                activeLight.classList.add('active');
                console.log(`Đã kích hoạt đèn ${activeClass}`);
            } else {
                console.warn(`Không tìm thấy đèn với class ${activeClass}`);
                
                // Log tất cả các đèn để debug
                console.log(`Tìm đèn với class: .traffic-light-status .light.${activeClass}`);
                lights.forEach((light, index) => {
                    const classes = Array.from(light.classList);
                    console.log(`Đèn ${index}: classes=${classes.join(', ')}`);
                });
            }
        }
    } catch (error) {
        console.error('Lỗi khi cập nhật trạng thái đèn giao thông:', error);
    }
}

// Tạo phiên bản throttled của hàm cập nhật vi phạm
const throttledUpdateViolations = throttle(function() {
    // Giảm số lượng log để tránh làm chậm console
    const shouldLog = Math.random() < 0.01; // Chỉ log khoảng 1% các lần cập nhật
    
    // Thêm timestamp để tránh cache
    const timestamp = new Date().getTime();
    const url = `/api/get_violations?page=1&per_page=10&t=${timestamp}`;
    
    if (shouldLog) {
        console.log(`Đang lấy dữ liệu vi phạm từ: ${url}`);
    }
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                if (shouldLog) {
                    console.warn(`Lỗi khi lấy dữ liệu vi phạm: ${data.message}`);
                }
                return;
            }
            
            const violations = data.violations || [];
            const totalPages = data.total_pages || 1;
            const currentPage = data.page || 1;
            
            // Cập nhật bảng vi phạm
            const tableBody = document.getElementById('violations-table-body');
            if (!tableBody) {
                if (shouldLog) console.error('Không tìm thấy bảng vi phạm');
                return;
            }
            
            // Xóa dữ liệu cũ
            tableBody.innerHTML = '';
            
            // Thêm dữ liệu mới
            if (violations.length === 0) {
                // Nếu không có vi phạm, hiển thị thông báo
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td colspan="6" class="text-center">Chưa phát hiện vi phạm</td>
                `;
                tableBody.appendChild(row);
            } else {
                violations.forEach((violation, index) => {
                    const row = document.createElement('tr');
                    
                    // Format thời gian vi phạm
                    let timeStr = 'N/A';
                    if (violation.timestamp) {
                        try {
                            const date = new Date(violation.timestamp);
                            timeStr = date.toLocaleTimeString();
                        } catch (e) {
                            if (shouldLog) {
                                console.warn(`Lỗi khi định dạng thời gian: ${e.message}`);
                            }
                        }
                    }
                    
                    // Tạo nội dung hàng
                    row.innerHTML = `
                        <td>${(currentPage - 1) * 10 + index + 1}</td>
                        <td>${violation.vehicleType || 'N/A'}</td>
                        <td>${timeStr}</td>
                        <td>${violation.violation_type || 'Vượt đèn đỏ'}</td>
                        <td>${violation.licensePlate || 'Không xác định'}</td>
                        <td>
                            <button class="btn btn-sm btn-primary view-btn" data-bs-toggle="modal" data-bs-target="#violationModal">
                                <i class="fas fa-eye"></i> Xem
                            </button>
                            <button class="btn btn-sm btn-success download-btn">
                                <i class="fas fa-download"></i> Tải
                            </button>
                        </td>
                    `;
                    
                    // Thêm vào bảng
                    tableBody.appendChild(row);
                    
                    // Thêm sự kiện cho nút xem
                    const viewBtn = row.querySelector('.view-btn');
                    viewBtn.addEventListener('click', () => {
                        const sceneImage = violation.scene_image_url || '';
                        const vehicleImage = violation.vehicle_image_url || '';
                        const plateImage = violation.license_plate_image_url || '';
                        viewViolation(index, sceneImage, vehicleImage, plateImage);
                    });
                    
                    // Thêm sự kiện cho nút tải
                    const downloadBtn = row.querySelector('.download-btn');
                    downloadBtn.addEventListener('click', () => {
                        const sceneImage = violation.scene_image_url || '';
                        downloadViolation(index, sceneImage);
                    });
                });
            }
            
            // Cập nhật phân trang
            updatePagination(currentPage, totalPages);
            
            // Cập nhật số lượng vi phạm
            const violationCounter = document.getElementById('violation-counter');
            if (violationCounter) {
                violationCounter.textContent = data.total || 0;
            }
        })
        .catch(error => {
            if (shouldLog) {
                console.error('Lỗi khi lấy dữ liệu vi phạm:', error);
            }
        });
}, 5000); // Giới hạn gọi API mỗi 5 giây

/**
 * Cập nhật vi phạm từ server
 */
function updateViolations() {
    throttledUpdateViolations();
}

/**
 * Cập nhật phân trang
 */
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

/**
 * Xem chi tiết vi phạm
 */
function viewViolation(violationId, sceneImage, vehicleImage, plateImage) {
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
                        <h4>ID Vi phạm: ${violationId}</h4>
                        <div class="violation-images">
    `;
    
    // Thêm ảnh toàn cảnh nếu có
    if (sceneImage) {
        modalHTML += `
            <div class="violation-image-container">
                <h5>Ảnh toàn cảnh vi phạm</h5>
                <img src="${sceneImage}" alt="Ảnh toàn cảnh vi phạm" class="violation-image scene-image">
            </div>
        `;
    }
    
    // Thêm ảnh phương tiện nếu có
    if (vehicleImage) {
        modalHTML += `
            <div class="violation-image-container">
                <h5>Ảnh phương tiện vi phạm</h5>
                <img src="${vehicleImage}" alt="Ảnh phương tiện vi phạm" class="violation-image vehicle-image">
            </div>
        `;
    }
    
    // Thêm ảnh biển số nếu có
    if (plateImage) {
        modalHTML += `
            <div class="violation-image-container">
                <h5>Ảnh biển số xe</h5>
                <img src="${plateImage}" alt="Ảnh biển số xe" class="violation-image plate-image">
            </div>
        `;
    }
    
    // Đóng các thẻ
    modalHTML += `
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-primary close-btn">Đóng</button>
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
}

/**
 * Tải xuống ảnh vi phạm
 */
function downloadViolation(violationId, sceneImage) {
    if (!sceneImage) {
        showToast('Không có ảnh vi phạm để tải xuống', 'error');
        return;
    }
    
    // Tạo một thẻ a ẩn để tải xuống
    const downloadLink = document.createElement('a');
    downloadLink.href = sceneImage;
    downloadLink.download = `violation_${violationId}.jpg`;
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
    
    showToast('Đang tải xuống ảnh vi phạm', 'info');
}

/**
 * Cập nhật chỉ báo trạng thái live
 */
function updateLiveIndicator(text) {
    const liveIndicator = document.querySelector('.live-indicator');
    if (liveIndicator) {
        liveIndicator.innerHTML = `<span class="pulse"></span> ${text}`;
    }
}

/**
 * Lưu tọa độ biên lên server
 */
function saveBoundariesToServer(boundaryData) {
    // Lấy video_id từ localStorage
    const videoId = localStorage.getItem('current_video_id');
    
    // Chuẩn bị dữ liệu
    const data = {
        video_id: videoId,
        boundaries: boundaryData
    };
    
    // Update API endpoint with /api prefix
    fetch('/api/save_boundaries', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Đã lưu tọa độ biên thành công!', 'success');
        } else {
            showToast(`Lỗi: ${data.message}`, 'error');
        }
    })
    .catch(error => {
        console.error('Lỗi khi lưu tọa độ biên:', error);
        showToast('Có lỗi xảy ra khi lưu tọa độ biên', 'error');
    });
}

/**
 * Hiển thị thông báo
 */
function showToast(message, type = 'info') {
    // Kiểm tra xem đã có toast container chưa
    let toastContainer = document.querySelector('.toast-container');
    
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    
    // Tạo toast mới
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon;
    switch (type) {
        case 'success':
            icon = 'fas fa-check-circle';
            break;
        case 'error':
            icon = 'fas fa-exclamation-circle';
            break;
        case 'warning':
            icon = 'fas fa-exclamation-triangle';
            break;
        default:
            icon = 'fas fa-info-circle';
    }
    
    toast.innerHTML = `
        <i class="${icon}"></i>
        <span class="toast-message">${message}</span>
        <button class="toast-close"><i class="fas fa-times"></i></button>
    `;
    
    toastContainer.appendChild(toast);
    
    // Xử lý đóng toast
    const closeBtn = toast.querySelector('.toast-close');
    closeBtn.addEventListener('click', () => {
        toast.classList.add('toast-hiding');
        setTimeout(() => {
            toastContainer.removeChild(toast);
        }, 300);
    });
    
    // Tự động ẩn toast sau 5 giây
    setTimeout(() => {
        if (toast.parentElement) {
            toast.classList.add('toast-hiding');
            setTimeout(() => {
                if (toast.parentElement) {
                    toastContainer.removeChild(toast);
                }
            }, 300);
        }
    }, 5000);
    
    // Hiệu ứng hiển thị
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
}

/**
 * Tải video lên server
 */
function uploadVideo() {
    console.log('Bắt đầu tải video lên');
    const fileInput = document.getElementById('video-upload-input');
    if (!fileInput || !fileInput.files || !fileInput.files.length) {
        console.error('Không tìm thấy file hoặc input element');
        showToast('Vui lòng chọn video trước khi tải lên', 'error');
        return;
    }
    
    const file = fileInput.files[0];
    
    // Kiểm tra kích thước file (giới hạn 2GB)
    const maxSize = 2 * 1024 * 1024 * 1024; // 2GB
    if (file.size > maxSize) {
        console.error(`File quá lớn: ${file.size} bytes (giới hạn: ${maxSize} bytes)`);
        showToast(`File quá lớn. Kích thước tối đa là 2GB. File của bạn: ${(file.size / (1024 * 1024)).toFixed(2)}MB`, 'error');
        return;
    }
    
    // Kiểm tra loại file
    const allowedTypes = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska'];
    if (!allowedTypes.includes(file.type)) {
        console.error(`Loại file không được hỗ trợ: ${file.type}`);
        showToast(`Loại file không được hỗ trợ. Vui lòng chọn file MP4, AVI, MOV hoặc MKV.`, 'error');
        return;
    }
    
    // Lấy các phần tử trên giao diện
    const selectedFileInfo = document.querySelector('.selected-file-info');
    const uploadProgress = document.querySelector('.upload-progress');
    const uploadButton = document.querySelector('.modal-footer .upload-btn');
    const progressFill = document.querySelector('.progress-fill');
    const progressPercent = document.querySelector('.progress-percent');
    const uploadResult = document.querySelector('.upload-result');
    const successMessage = document.querySelector('.success-message');
    const errorMessage = document.querySelector('.error-message');
    const errorMessageText = document.querySelector('.error-message p');
    
    // Hiển thị phần tiến trình tải lên
    selectedFileInfo.classList.add('hidden');
    uploadProgress.classList.remove('hidden');
    uploadButton.disabled = true;
    
    // Dừng stream hiện tại nếu có và gửi yêu cầu dừng xử lý đến server
    console.log('Dừng stream hiện tại trước khi tải video mới');
    
    // Gửi yêu cầu dừng xử lý đến server trước
    fetch('/api/stop_processing', {
        method: 'POST'
    })
    .then(response => {
        console.log('Server đã nhận yêu cầu dừng xử lý video cũ');
    })
    .catch(error => {
        console.error('Lỗi khi gửi yêu cầu dừng xử lý:', error);
    })
    .finally(() => {
        // Dừng các interval ở client
        stopVideoStream();
        
        // Đợi một chút để đảm bảo server đã dừng xử lý video cũ
        setTimeout(uploadVideoToServer, 1000);
    });
    
    // Hàm tải video lên server sau khi đã dừng video cũ
    function uploadVideoToServer() {
        // Xóa phần tử hiển thị cũ
        const videoStream = document.querySelector('.video-stream');
        if (videoStream) {
            // Xóa canvas cũ nếu có
            const oldCanvas = videoStream.querySelector('canvas.stream-canvas');
            if (oldCanvas) {
                videoStream.removeChild(oldCanvas);
                console.log('Đã xóa canvas cũ');
            }
            
            // Xóa img cũ nếu có
            const oldImg = videoStream.querySelector('img.frame-img');
            if (oldImg) {
                videoStream.removeChild(oldImg);
                console.log('Đã xóa img cũ');
            }
            
            // Hiển thị lại video gốc để làm placeholder
            const originalVideo = document.getElementById('traffic-video');
            if (originalVideo) {
                originalVideo.style.display = '';
                console.log('Đã hiển thị lại video gốc');
            }
        }
        
        // Cập nhật trạng thái hiển thị
        updateLiveIndicator('Đang tải video lên...');
        
        // Tạo FormData để tải lên
        const formData = new FormData();
        formData.append('video', file);
        
        // Sử dụng AJAX để tải lên server
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/upload', true);
        
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentage = Math.round((e.loaded / e.total) * 100);
                progressFill.style.width = `${percentage}%`;
                progressPercent.textContent = `${percentage}%`;
            }
        });
        
        xhr.addEventListener('load', function() {
            uploadProgress.classList.add('hidden');
            uploadResult.classList.remove('hidden');
            
            if (xhr.status === 200) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    console.log('Phản hồi từ server:', response);
                    
                    successMessage.classList.remove('hidden');
                    errorMessage.classList.add('hidden');
                    
                    // Lưu video_id cho việc lưu biên sau này
                    if (response.video_id) {
                        localStorage.setItem('current_video_id', response.video_id);
                        console.log('Đã lưu video_id:', response.video_id);
                    }
                    
                    // Sau 2 giây, đóng modal và bắt đầu cập nhật video stream
                    setTimeout(() => {
                        closeUploadModal();
                        
                        // Hiển thị thông báo
    
                        
                        // Đợi một chút trước khi bắt đầu stream để đảm bảo server đã sẵn sàng
                        setTimeout(() => {
                            // Bắt đầu cập nhật video stream
                            startVideoStream();
                        }, 2000);
                    }, 1000);
                } catch (error) {
                    console.error('Lỗi khi phân tích phản hồi JSON:', error);
                    errorMessage.classList.remove('hidden');
                    successMessage.classList.add('hidden');
                    errorMessageText.textContent = 'Có lỗi xảy ra khi phân tích phản hồi từ máy chủ!';
                    updateLiveIndicator('Đã xảy ra lỗi khi tải video');
                }
            } else {
                console.error('Lỗi HTTP:', xhr.status, xhr.statusText);
                successMessage.classList.add('hidden');
                errorMessage.classList.remove('hidden');
                
                // Hiển thị thông báo lỗi chi tiết từ server nếu có
                try {
                    const errorResponse = JSON.parse(xhr.responseText);
                    if (errorResponse && errorResponse.error) {
                        errorMessageText.textContent = `Lỗi: ${errorResponse.error}`;
                        console.error('Lỗi từ server:', errorResponse.error);
                    } else {
                        errorMessageText.textContent = `Lỗi HTTP: ${xhr.status} ${xhr.statusText}`;
                    }
                } catch (e) {
                    errorMessageText.textContent = `Lỗi HTTP: ${xhr.status} ${xhr.statusText}`;
                }
                
                updateLiveIndicator('Đã xảy ra lỗi khi tải video');
                
                // Sau 3 giây, cho phép thử lại
                setTimeout(() => {
                    uploadResult.classList.add('hidden');
                    selectedFileInfo.classList.remove('hidden');
                    uploadButton.disabled = false;
                }, 3000);
            }
        });
        
        xhr.addEventListener('error', function(e) {
            console.error('Lỗi khi tải lên:', e);
            uploadProgress.classList.add('hidden');
            uploadResult.classList.remove('hidden');
            successMessage.classList.add('hidden');
            errorMessage.classList.remove('hidden');
            errorMessageText.textContent = 'Lỗi kết nối đến máy chủ! Vui lòng kiểm tra kết nối mạng và thử lại.';
            updateLiveIndicator('Đã xảy ra lỗi khi tải video');
            
            // Sau 3 giây, cho phép thử lại
            setTimeout(() => {
                uploadResult.classList.add('hidden');
                selectedFileInfo.classList.remove('hidden');
                uploadButton.disabled = false;
            }, 3000);
        });
        
        // Thêm xử lý timeout
        xhr.timeout = 60000; // 60 giây
        xhr.ontimeout = function() {
            console.error('Quá thời gian chờ khi tải video lên');
            uploadProgress.classList.add('hidden');
            uploadResult.classList.remove('hidden');
            successMessage.classList.add('hidden');
            errorMessage.classList.remove('hidden');
            errorMessageText.textContent = 'Quá thời gian chờ khi tải video lên. Vui lòng thử lại với file nhỏ hơn.';
            updateLiveIndicator('Đã xảy ra lỗi khi tải video');
            
            // Sau 3 giây, cho phép thử lại
            setTimeout(() => {
                uploadResult.classList.add('hidden');
                selectedFileInfo.classList.remove('hidden');
                uploadButton.disabled = false;
            }, 3000);
        };
        
        // Gửi dữ liệu
        xhr.send(formData);
        console.log('Đã gửi yêu cầu tải lên');
    }
}

// Thêm hàm xử lý lỗi frame
function handleFrameError(errorMsg) {
    console.warn(errorMsg);
    
    // Nếu không phải đang xử lý video, không cần làm gì thêm
    if (!window.isProcessingVideo) return;
    
    // Nếu có quá nhiều lỗi liên tiếp, hiển thị thông báo cho người dùng
    if (window.consecutiveErrors > 100) {
        // Hiển thị thông báo lỗi
        showToast('Đang gặp sự cố kết nối đến server, đang thử lại...', 'error');
        updateLiveIndicator('Đang kết nối lại...');
        
        // Hiển thị hình ảnh lỗi
        const videoStream = document.querySelector('.video-stream');
        if (videoStream) {
            const frameImg = videoStream.querySelector('img.frame-img');
            if (frameImg) {
                frameImg.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(`
                    <svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
                        <rect width="1280" height="720" fill="#1a1a1a"/>
                        <text x="640" y="340" font-family="Arial" font-size="30" fill="#ff5555" text-anchor="middle">Lỗi kết nối đến server</text>
                        <text x="640" y="380" font-family="Arial" font-size="20" fill="white" text-anchor="middle">Đang thử kết nối lại...</text>
                    </svg>
                `);
            }
        }
    }
}