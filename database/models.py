from sqlalchemy import create_engine, Column, Integer, String, Float, TIMESTAMP, ForeignKey, BigInteger, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DB_URL = "postgresql+psycopg2://sdn:123@localhost/sdn_controller"

Base = declarative_base()
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)

class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    ip_address = Column(String)
    mac_address = Column(String)
    type = Column(String)
    status = Column(String)
    last_seen = Column(TIMESTAMP, default=datetime.utcnow)

class ServerMetrics(Base):
    __tablename__ = "server_metrics"
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    storage_usage = Column(Float)
    io_read = Column(BigInteger)
    io_write = Column(BigInteger)
    net_rx = Column(BigInteger)
    net_tx = Column(BigInteger)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)

class Log(Base):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"))
    log_text = Column(Text)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow)

def save_metrics(device_id, data):
    session = SessionLocal()
    try:
        metric = ServerMetrics(
            device_id=device_id,
            cpu_usage=data['cpu_usage'],
            memory_usage=data['memory_usage'],
            storage_usage=data['storage_usage'],
            io_read=data['io_read'],
            io_write=data['io_write'],
            net_rx=data['net_rx'],
            net_tx=data['net_tx']
        )
        session.add(metric)
        session.commit()
    except Exception as e:
        print(f"[DB] Failed to save metrics: {e}")
        session.rollback()
    finally:
        session.close()

Base.metadata.create_all(engine)
