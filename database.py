from sqlalchemy import create_engine, Column, Integer, Float, String
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. MySQL 연결 설정 (비밀번호 admin1234, DB이름 upm_db 기준)
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@localhost:3306/upmdecode"

# 2. 엔진 및 세션 설정
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. 모델 베이스 (경고 메시지 안 나오게 수정됨)
Base = declarative_base()

# 4. 테이블 모양 정의
class PCRecord(Base):
    __tablename__ = "pc_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    pc_id = Column(String(50))
    cpu_usage = Column(Float)
    gpu_temp = Column(Float)

# 5. 테이블 생성 함수
def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ MySQL 연결 및 테이블 생성 성공!")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

# 직접 실행할 때만 작동
if __name__ == "__main__":
    init_db()