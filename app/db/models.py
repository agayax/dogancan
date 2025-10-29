from sqlalchemy import create_engine, Column, Integer, String, Boolean, JSON, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from cryptography.fernet import Fernet
import os

# --- Database Setup ---
DATABASE_URL = "sqlite:///./jules_trader.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Encryption Setup ---
# WARNING: In a production environment, this key should be loaded securely (e.g., from env variables, Vault)
# and should be consistent across application restarts.
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
fernet = Fernet(ENCRYPTION_KEY.encode())

def encrypt_data(data: str) -> str:
    return fernet.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    return fernet.decrypt(encrypted_data.encode()).decode()

# --- ORM Models ---

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    # Encrypted API credentials
    _api_key = Column("api_key", String)
    _api_secret = Column("api_secret", String)

    presets = relationship("StrategyPreset", back_populates="owner")
    paper_sessions = relationship("PaperTradingSession", back_populates="user")

    @property
    def api_key(self):
        return decrypt_data(self._api_key) if self._api_key else None

    @api_key.setter
    def api_key(self, value):
        self._api_key = encrypt_data(value)

    @property
    def api_secret(self):
        return decrypt_data(self._api_secret) if self._api_secret else None

    @api_secret.setter
    def api_secret(self, value):
        self._api_secret = encrypt_data(value)


class StrategyPreset(Base):
    __tablename__ = "strategy_presets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    config = Column(JSON, nullable=False) # e.g., {'strategy_name': 'ema_atr', 'params': {'ema_slow': 50}}

    is_public = Column(Boolean, default=False)
    is_in_marketplace = Column(Boolean, default=False)

    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="presets")

    paper_sessions = relationship("PaperTradingSession", back_populates="preset")


class PaperTradingSession(Base):
    __tablename__ = "paper_trading_sessions"
    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="paper_sessions")

    preset_id = Column(Integer, ForeignKey("strategy_presets.id"))
    preset = relationship("StrategyPreset", back_populates="paper_sessions")

    is_public = Column(Boolean, default=False) # For leaderboard visibility

    # Performance Metrics
    sharpe_ratio = Column(String)
    max_drawdown = Column(String)
    pnl_percentage = Column(String)
    resilience_score = Column(String) # From Phase 5


def get_db():
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()

def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    print("Creating database and tables...")
    create_db_and_tables()
    print("Database and tables created successfully.")
    print(f"Make sure to set the ENCRYPTION_KEY environment variable. A new one for this session is: {ENCRYPTION_KEY}")
