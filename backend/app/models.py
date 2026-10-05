from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from .db import Base

def now(): return datetime.utcnow()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(15))
    password_hash = Column(String(100), nullable=False)
    role = Column(String(10), default="CUSTOMER")
    is_verified = Column(Boolean, default=False)

class Otp(Base):
    __tablename__ = "otp_codes"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), index=True)
    purpose = Column(String(10))  # verify | login | reset
    code_hash = Column(String(100))
    expires_at = Column(DateTime)
    attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=now)

class AgeSize(Base):
    __tablename__ = "age_sizes"
    id = Column(Integer, primary_key=True)
    label = Column(String(20))
    unit = Column(String(10))  # Months | Years
    sort = Column(Integer)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, default="")
    price = Column(Integer, nullable=False)  # rupees
    category = Column(String(60), default="Dresses")
    active = Column(Boolean, default=True)
    images = Column(JSON, default=list)
    created_at = Column(DateTime, default=now)
    sizes = relationship("ProductSize", cascade="all, delete-orphan")

class ProductSize(Base):
    __tablename__ = "product_sizes"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    size_id = Column(Integer, ForeignKey("age_sizes.id"))
    stock = Column(Integer, default=0)
    size = relationship("AgeSize")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    address = Column(JSON)  # snapshot
    subtotal = Column(Integer)
    shipping = Column(Integer)
    total = Column(Integer)
    payment_status = Column(String(15), default="PENDING")  # PENDING | PAID
    order_status = Column(String(20), default="PENDING_PAYMENT")
    rzp_order_id = Column(String(60))
    rzp_payment_id = Column(String(60))
    courier = Column(String(60))
    tracking_no = Column(String(60))
    created_at = Column(DateTime, default=now)
    user = relationship("User")
    items = relationship("OrderItem", cascade="all, delete-orphan")
    history = relationship("StatusHistory", cascade="all, delete-orphan", order_by="StatusHistory.id")

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer)
    size_id = Column(Integer)
    name = Column(String(150))
    size_label = Column(String(20))
    qty = Column(Integer)
    price = Column(Integer)

class StatusHistory(Base):
    __tablename__ = "order_status_history"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    status = Column(String(20))
    note = Column(String(255), default="")
    created_at = Column(DateTime, default=now)
