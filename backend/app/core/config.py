import os
from pathlib import Path

# backend/ 目录（app 的上两级）
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings:
    APP_NAME = "企业风控中台"
    APP_VERSION = "1.0.0"
    APP_ENV = os.getenv("APP_ENV", "dev")

    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'risk_control.db'}")

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-secret-change-me-32bytes-min")
    JWT_ALGORITHM = "HS256"
    JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

    # 风控评分阈值
    RISK_WARN_THRESHOLD = int(os.getenv("RISK_WARN_THRESHOLD", "60"))
    RISK_BLOCK_THRESHOLD = int(os.getenv("RISK_BLOCK_THRESHOLD", "100"))


settings = Settings()
