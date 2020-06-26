from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Numeric, DateTime
from sqlalchemy.orm import relationship

from database import Base

"""
SQLite3 molels
"""

class Acti(Base):
    __tablename__ = "acti"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime)
    mets = Column(Numeric(4, 2))

class Wrist(Base):
    __tablename__ = "wrist"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime)
    mets = Column(Numeric(4, 2))

