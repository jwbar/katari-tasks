import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-change-in-production'
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/assignment_db'
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)