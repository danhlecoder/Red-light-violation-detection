"""
Setup utility for the traffic monitoring system
"""
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.core.config import (
    UPLOAD_FOLDER, PROCESSED_FOLDER, BOUNDARIES_FOLDER, VIOLATIONS_FOLDER,
    MODEL_DIR, MODEL_PATH
)

def create_directories():
    """
    Create required directories for the application
    """
    directories = [
        UPLOAD_FOLDER,
        PROCESSED_FOLDER,
        BOUNDARIES_FOLDER,
        VIOLATIONS_FOLDER,
        MODEL_DIR
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")
        else:
            print(f"Directory already exists: {directory}")
    
    # Check if model file exists
    if os.path.exists(MODEL_PATH):
        print(f"Found model file at {MODEL_PATH}")
    else:
        print(f"Model file not found at {MODEL_PATH}")
        print("Please place your YOLO model file in the model directory with name 'v5.pt'")

if __name__ == "__main__":
    create_directories()
    print("Setup complete!") 