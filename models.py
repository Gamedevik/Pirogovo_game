from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float
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
    
    # Связи
    territories = relationship("Territory", back_populates="owner")
    buildings = relationship("BuildingOnMap", back_populates="owner")
    queue = relationship("GameQueue", back_populates="user")


class Territory(Base):
    """Игровая территория (из KML)"""
    __tablename__ = "territories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    faction = Column(String, nullable=False)
    color = Column(String, default="#666666")
    population = Column(Integer, default=100)
    center_lat = Column(Float, nullable=True)
    center_lon = Column(Float, nullable=True)
    
    # Ресурсы территории
    wood = Column(Integer, default=50)
    food = Column(Integer, default=50)
    gold = Column(Integer, default=20)
    stone = Column(Integer, default=10)
    
    # Владелец (может быть None — нейтральная)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    owner = relationship("User", back_populates="territories")
    buildings = relationship("BuildingOnMap", back_populates="territory")


class BuildingOnMap(Base):
    """Здание на карте"""
    __tablename__ = "buildings_on_map"
    
    id = Column(Integer, primary_key=True, index=True)
    territory_id = Column(Integer, ForeignKey("territories.id"), nullable=False)
    type = Column(String, nullable=False)  # farm, mine, sawmill, house, barracks
    level = Column(Integer, default=1)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    constructed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    territory = relationship("Territory", back_populates="buildings")
    owner = relationship("User", back_populates="buildings")


class GameQueue(Base):
    """Очередь действий"""
    __tablename__ = "game_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    territory_id = Column(Integer, ForeignKey("territories.id"), nullable=False)
    action_type = Column(String, nullable=False)  # build, upgrade, attack, train
    target_id = Column(Integer, nullable=True)  # ID здания или юнита
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=False)
    completed = Column(Boolean, default=False)
    
    # Связи
    user = relationship("User", back_populates="queue")