from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import yfinance as yf
import pandas as pd
from typing import List, Dict
import os
from dotenv import load_dotenv
import logging

# Load .env file if it exists (local development)
if os.path.exists(".env"):
    load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Use Render's internal DATABASE_URL if available
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
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

async def fetch_nvidia_data():
    """
    Fetch NVIDIA financial data and major customer orders
    """
    try:
        nvda = yf.Ticker("NVDA")
        quarterly_data = nvda.quarterly_financials
        return {
            "financials": quarterly_data,
            "quarter": quarterly_data.columns[0].strftime("%Y-Q%q")
        }
    except Exception as e:
        logger.error(f"Error fetching NVIDIA data: {e}")
        return None

@app.get("/api/metrics/nvidia")
async def get_nvidia_metrics(start_date: str, end_date: str):
    db = SessionLocal()
    try:
        metrics = {
            "orders": db.query(QuarterlyMetrics).filter(
                QuarterlyMetrics.metric_type == "nvidia_orders",
                QuarterlyMetrics.quarter.between(start_date, end_date)
            ).all(),
            "breakdown": db.query(NvidiaOrdersBreakdown).filter(
                NvidiaOrdersBreakdown.quarter.between(start_date, end_date)
            ).all()
        }
        return metrics
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