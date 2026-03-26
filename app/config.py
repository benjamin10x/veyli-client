import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-key")
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001/api/v1")
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "15"))
    JWT_STORAGE_MODE = os.getenv("JWT_STORAGE_MODE", "session")
