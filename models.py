from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # "user" или "admin"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связь с деревней
    village = relationship("Village", back_populates="user", uselist=False)


class Village(Base):
    __tablename__ = "villages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String, nullable=False)
    wood = Column(Integer, default=100)
    food = Column(Integer, default=100)
    gold = Column(Integer, default=50)
    population = Column(Integer, default=10)
    x = Column(Integer, default=0)  # координаты на карте
    y = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связь с пользователем
    user = relationship("User", back_populates="village")
    # Связь со зданиями
    buildings = relationship("Building", back_populates="village")


class Building(Base):
    __tablename__ = "buildings"
    
    id = Column(Integer, primary_key=True, index=True)
    village_id = Column(Integer, ForeignKey("villages.id"), nullable=False)
    type = Column(String, nullable=False)  # "farm", "lumbermill", "mine", "barracks"
    level = Column(Integer, default=1)
    construction_start = Column(DateTime(timezone=True), nullable=True)
    construction_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связь с деревней
    village = relationship("Village", back_populates="buildings")