import os
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    Numeric,
    DateTime,
    ForeignKey,
    Enum,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:12345@localhost:3306/accessibility_auditor"
)

try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    # Test connection
    with engine.connect() as conn:
        print("Database connected successfully!")
except Exception as e:
    print(f"Warning: Primary database connection failed ({e}). Falling back to SQLite.")
    sqlite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "accessibility_auditor.db"))
    DATABASE_URL = f"sqlite:///{sqlite_path}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    websites = relationship("Website", back_populates="user", cascade="all, delete-orphan")


class Website(Base):
    __tablename__ = "websites"

    website_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    website_name = Column(String(150), nullable=False)
    website_url = Column(String(2048), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="websites")
    scans = relationship("Scan", back_populates="website", cascade="all, delete-orphan")


class Scan(Base):
    __tablename__ = "scans"

    scan_id = Column(Integer, primary_key=True, autoincrement=True)
    website_id = Column(Integer, ForeignKey("websites.website_id", ondelete="CASCADE"), nullable=False)
    scan_status = Column(
        Enum("pending", "running", "completed", "failed", name="scan_status_enum"),
        default="pending"
    )
    accessibility_score = Column(Numeric(5, 2), nullable=True)
    total_issues = Column(Integer, default=0)
    critical_issues = Column(Integer, default=0)
    serious_issues = Column(Integer, default=0)
    moderate_issues = Column(Integer, default=0)
    minor_issues = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    website = relationship("Website", back_populates="scans")
    issues = relationship("AccessibilityIssue", back_populates="scan", cascade="all, delete-orphan")


class AccessibilityIssue(Base):
    __tablename__ = "accessibility_issues"

    issue_id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(Integer, ForeignKey("scans.scan_id", ondelete="CASCADE"), nullable=False)
    rule_code = Column(String(100), nullable=True)
    issue_title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(
        Enum("critical", "serious", "moderate", "minor", name="severity_enum"),
        default="moderate"
    )
    element_selector = Column(String(1000), nullable=True)
    element_html = Column(Text, nullable=True)
    page_url = Column(String(2048), nullable=True)
    recommendation = Column(Text, nullable=True)
    wcag_reference = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    scan = relationship("Scan", back_populates="issues")


class ScanHistory(Base):
    __tablename__ = "scan_history"

    history_id = Column(Integer, primary_key=True, autoincrement=True)
    website_id = Column(Integer, ForeignKey("websites.website_id", ondelete="CASCADE"), nullable=False)
    scan_id = Column(Integer, ForeignKey("scans.scan_id", ondelete="CASCADE"), nullable=False)
    accessibility_score = Column(Numeric(5, 2), nullable=True)
    total_issues = Column(Integer, default=0)
    scanned_at = Column(DateTime, default=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Ensure database tables exist and default seed user is created."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user = db.query(User).first()
        if not user:
            default_user = User(
                full_name="Default Auditor",
                email="admin@accessai.local",
                password_hash="demo_hash"
            )
            db.add(default_user)
            db.commit()
            print("Default auditor user created.")