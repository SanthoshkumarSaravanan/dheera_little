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
    UPI_ID: str = ""          # your UPI ID, e.g. dheeralittles@okhdfcbank
    UPI_NAME: str = "Dheera Littles"
    SMS_PROVIDER: str = ""    # msg91 | fast2sms (empty = no SMS)
    SMS_API_KEY: str = ""
    MSG91_TEMPLATE_ID: str = ""
    SHIPPING_FLAT: int = 60
    FREE_SHIPPING_ABOVE: int = 999

settings = Settings()
