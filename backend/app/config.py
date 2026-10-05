from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://dheera:dheera@db:5432/dheera"
    JWT_SECRET: str = "change-me"
    COOKIE_SECURE: bool = False  # set true when serving over HTTPS
    ADMIN_EMAIL: str = "admin@dheeralittles.com"
    ADMIN_PASSWORD: str = "Admin@12345"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = ""
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    SHIPPING_FLAT: int = 60
    FREE_SHIPPING_ABOVE: int = 999

settings = Settings()
