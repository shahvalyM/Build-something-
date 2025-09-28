# SQLAlchemy model for the leaked_passwords table in PostgreSQL.
from sqlalchemy import Column, Text, Integer
from database import Base

class LeakedPassword(Base):
    __tablename__ = "leaked_passwords"
    sha1 = Column(Text, primary_key=True, index=True)
    count = Column(Integer, default=0)
