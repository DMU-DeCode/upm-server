from sqlalchemy import create_all, Column, Integer, Float, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# mysql://사용자명:비밀번호@주소:포트/DB이름
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:admin1234@localhost:3306/upm_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. DB 테이블 모양 만들기 (엑셀의 칸 만들기)
class PCRecord(Base):
    __tablename__ = "pc_logs"
    id = Column(Integer, primary_key=True, index=True)
    pc_id = Column(String(50))
    cpu_usage = Column(Float)
    gpu_temp = Column(Float)