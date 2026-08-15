"""DB 엔진/세션 설정 및 마이그레이션.

- SQLAlchemy 엔진, 세션 팩토리(SessionLocal), Base 정의
- FastAPI 의존성 주입용 get_db()
- 서버 시작 시 실행되는 테이블 생성/컬럼 마이그레이션(init_db)
"""

from sqlalchemy import create_engine, text, inspect as sa_inspect
from sqlalchemy.orm import declarative_base, sessionmaker

# [DB 설정 및 엔진 생성]
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:1234@localhost:3306/upm_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# [DB 세션 관리 함수 (Dependency Injection)]
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_gpu_column():
    """기존 gpuTemp 컬럼 → gpuUsage 컬럼으로 마이그레이션한다."""
    try:
        inspector = sa_inspect(engine)
        if inspector.has_table("telemetry_logs"):
            cols = [c["name"] for c in inspector.get_columns("telemetry_logs")]
            with engine.begin() as conn:
                if "gpuTemp" in cols and "gpuUsage" not in cols:
                    conn.execute(text("ALTER TABLE telemetry_logs CHANGE gpuTemp gpuUsage FLOAT"))
                    print("✅ DB 마이그레이션 완료: gpuTemp → gpuUsage")
                elif "gpuUsage" not in cols:
                    conn.execute(text("ALTER TABLE telemetry_logs ADD COLUMN gpuUsage FLOAT"))
                    print("✅ DB 컬럼 추가: gpuUsage")
    except Exception as e:
        print(f"⚠️ DB 마이그레이션 오류: {e}")


def init_db():
    """서버 실행 시 테이블 자동 생성 + gpu 컬럼 마이그레이션을 수행한다."""
    # models 안에 정의된 테이블들이 Base.metadata에 등록되도록 import 시점을 여기서 보장
    import models  # noqa: F401  (테이블 등록 트리거용)

    Base.metadata.create_all(bind=engine)
    migrate_gpu_column()
