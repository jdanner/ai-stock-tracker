from fastapi import FastAPI, HTTPException, BackgroundTasks
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import yfinance as yf
import pandas as pd
from typing import List, Dict
import os
from dotenv import load_dotenv
import logging
from fastapi.middleware.cors import CORSMiddleware

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Load environment variables
load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
logger.info(f"Database URL present: {bool(DATABASE_URL)}")

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set")
    DATABASE_URL = "sqlite:///./test.db"  # Fallback for development
    logger.info("Using fallback database")

# Add PostgreSQL driver prefix if not present
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    logger.info("Updated database URL to use postgresql:// prefix")

# Create database engine
try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Database engine created successfully")
except Exception as e:
    logger.error(f"Failed to create database engine: {e}")
    raise

Base = declarative_base()

class QuarterlyMetrics(Base):
    __tablename__ = "quarterly_metrics"
    
    id = Column(Integer, primary_key=True)
    quarter = Column(String)  # Format: 2023Q1
    metric_type = Column(String)  # venture_investment, nvidia_orders
    value = Column(Float)
    source = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class NvidiaOrdersBreakdown(Base):
    __tablename__ = "nvidia_orders_breakdown"
    
    id = Column(Integer, primary_key=True)
    quarter = Column(String)
    company = Column(String)
    order_value = Column(Float)
    percentage_of_total = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

async def fetch_nvidia_quarterly_data():
    """Fetch NVIDIA's quarterly financial data"""
    try:
        nvda = yf.Ticker("NVDA")
        quarterly_revenue = nvda.quarterly_financials.loc['Total Revenue']
        
        data = []
        for date, value in quarterly_revenue.items():
            quarter = f"{date.year}Q{(date.month-1)//3 + 1}"
            data.append({
                "quarter": quarter,
                "metric_type": "nvidia_revenue",
                "value": float(value),
                "source": "yfinance"
            })
        return data
    except Exception as e:
        logger.error(f"Error fetching NVIDIA data: {e}")
        return None

async def store_quarterly_data(data: List[Dict]):
    """Store quarterly data in database"""
    db = SessionLocal()
    try:
        for item in data:
            metric = QuarterlyMetrics(
                quarter=item["quarter"],
                metric_type=item["metric_type"],
                value=item["value"],
                source=item["source"]
            )
            db.add(metric)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"Error storing data: {e}")
        db.rollback()
        return False
    finally:
        db.close()

@app.post("/api/data/refresh")
async def refresh_data(background_tasks: BackgroundTasks):
    """Refresh all data sources"""
    try:
        # Fetch NVIDIA data
        nvidia_data = await fetch_nvidia_quarterly_data()
        if nvidia_data:
            await store_quarterly_data(nvidia_data)
            return {"status": "success", "message": "Data refresh initiated"}
        else:
            raise HTTPException(status_code=500, message="Failed to fetch NVIDIA data")
    except Exception as e:
        logger.error(f"Error in refresh_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics/nvidia")
async def get_nvidia_metrics(start_date: str, end_date: str):
    """Get NVIDIA metrics between quarters"""
    db = SessionLocal()
    try:
        metrics = db.query(QuarterlyMetrics).filter(
            QuarterlyMetrics.metric_type == "nvidia_revenue",
            QuarterlyMetrics.quarter.between(start_date, end_date)
        ).order_by(desc(QuarterlyMetrics.quarter)).all()
        
        return {
            "revenue": [
                {
                    "quarter": m.quarter,
                    "value": m.value,
                    "source": m.source
                } for m in metrics
            ]
        }
    finally:
        db.close()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    try:
        logger.info(f"Attempting to connect to database...")
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as session:
            session.execute("SELECT 1")
        logger.info("Successfully connected to database and created tables")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise 

@app.get("/")
async def root():
    return {
        "status": "online",
        "endpoints": {
            "health": "/health",
            "nvidia_metrics": "/api/metrics/nvidia?start_date=2023Q1&end_date=2024Q1"
        }
    } 

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
) 