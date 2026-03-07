import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_key")


    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///database.db"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False