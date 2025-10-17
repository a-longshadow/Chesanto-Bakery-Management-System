/**
 * Profile Photo Upload and Drag-to-Fit
 * Simple implementation - no third-party libraries
 */

class ProfilePhotoUploader {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;
        
        this.fileInput = this.container.querySelector('input[type="file"]');
        this.preview = this.container.querySelector('.photo-preview');
        this.image = this.container.querySelector('.photo-preview__image');
        this.placeholder = this.container.querySelector('.photo-preview__placeholder');
        this.removeBtn = this.container.querySelector('.photo-preview__remove');
        
        this.isDragging = false;
        this.startX = 0;
        this.startY = 0;
        
        // Initialize from existing values (important for editing existing photos)
        const centerXInput = document.getElementById('photo_center_x');
        const centerYInput = document.getElementById('photo_center_y');
        this.currentX = centerXInput ? parseFloat(centerXInput.value) : 50;
        this.currentY = centerYInput ? parseFloat(centerYInput.value) : 50;
        
        this.init();
    }
    
    init() {
        // File input change
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Remove button
        if (this.removeBtn) {
            this.removeBtn.addEventListener('click', () => this.removePhoto());
        }
        
        // Drag to reposition
        this.image.addEventListener('mousedown', (e) => this.startDrag(e));
        document.addEventListener('mousemove', (e) => this.drag(e));
        document.addEventListener('mouseup', () => this.endDrag());
        
        // Touch support
        this.image.addEventListener('touchstart', (e) => this.startDrag(e));
        document.addEventListener('touchmove', (e) => this.drag(e));
        document.addEventListener('touchend', () => this.endDrag());
    }
    
    handleFileSelect(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // Validate file type
        if (!file.type.match('image/(jpeg|jpg|png)')) {
            alert('Please select a JPG or PNG image');
            this.fileInput.value = '';
            return;
        }
        
        // Validate file size (5MB max)
        if (file.size > 5 * 1024 * 1024) {
            alert('Image must be less than 5MB');
            this.fileInput.value = '';
            return;
        }
        
        // Load and display image
        const reader = new FileReader();
        reader.onload = (e) => {
            this.image.src = e.target.result;
            this.image.style.display = 'block';
            if (this.placeholder) this.placeholder.style.display = 'none';
            if (this.removeBtn) this.removeBtn.style.display = 'block';
            
            // Reset position to center
            this.currentX = 50;
            this.currentY = 50;
            this.updateImagePosition();
        };
        reader.readAsDataURL(file);
    }
    
    removePhoto() {
        this.fileInput.value = '';
        this.image.src = '';
        this.image.style.display = 'none';
        if (this.placeholder) this.placeholder.style.display = 'flex';
        if (this.removeBtn) this.removeBtn.style.display = 'none';
        
        // Reset hidden inputs
        document.getElementById('photo_center_x').value = '50.00';
        document.getElementById('photo_center_y').value = '50.00';
    }
    
    startDrag(e) {
        if (!this.image.src) return;
        
        e.preventDefault();
        this.isDragging = true;
        this.image.style.cursor = 'grabbing';
        
        const clientX = e.type === 'touchstart' ? e.touches[0].clientX : e.clientX;
        const clientY = e.type === 'touchstart' ? e.touches[0].clientY : e.clientY;
        
        this.startX = clientX;
        this.startY = clientY;
    }
    
    drag(e) {
        if (!this.isDragging) return;
        
        e.preventDefault();
        
        const clientX = e.type === 'touchmove' ? e.touches[0].clientX : e.clientX;
        const clientY = e.type === 'touchmove' ? e.touches[0].clientY : e.clientY;
        
        const deltaX = clientX - this.startX;
        const deltaY = clientY - this.startY;
        
        // Convert pixel movement to percentage
        const previewWidth = this.preview.offsetWidth;
        const previewHeight = this.preview.offsetHeight;
        
        const percentX = (deltaX / previewWidth) * 100;
        const percentY = (deltaY / previewHeight) * 100;
        
        // Update position (constrain to 0-100%)
        this.currentX = Math.max(0, Math.min(100, this.currentX + percentX));
        this.currentY = Math.max(0, Math.min(100, this.currentY + percentY));
        
        this.updateImagePosition();
        
        this.startX = clientX;
        this.startY = clientY;
    }
    
    endDrag() {
        if (!this.isDragging) return;
        
        this.isDragging = false;
        this.image.style.cursor = 'grab';
        
        // Update hidden form inputs
        document.getElementById('photo_center_x').value = this.currentX.toFixed(2);
        document.getElementById('photo_center_y').value = this.currentY.toFixed(2);
    }
    
    updateImagePosition() {
        this.image.style.objectPosition = `${this.currentX}% ${this.currentY}%`;
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('profile-photo-container')) {
        new ProfilePhotoUploader('profile-photo-container');
    }
});
