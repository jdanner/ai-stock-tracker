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
    metric_type = Column(String)  # venture_investment, cloud_workload, nvidia_orders
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

# Data collection functions
async def fetch_venture_data():
    """
    Fetch VC investment data from CB Insights/PitchBook
    Requires API key and subscription
    """
    try:
        # Example using CB Insights API
        headers = {"Authorization": f"Bearer {os.getenv('CBINSIGHTS_API_KEY')}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.cbinsights.com/v1/market-data/ai-investments",
                headers=headers
            )
            return response.json()
    except Exception as e:
        print(f"Error fetching venture data: {e}")
        return None

async def fetch_cloud_metrics():
    """
    Aggregate cloud provider AI workload data
    """
    metrics = {
        "azure": await fetch_azure_metrics(),
        "gcp": await fetch_gcp_metrics(),
        "aws": await fetch_aws_metrics()
    }
    return metrics

async def fetch_nvidia_data():
    """
    Fetch NVIDIA financial data and major customer orders
    """
    try:
        # Get NVIDIA stock data using yfinance
        nvda = yf.Ticker("NVDA")
        quarterly_data = nvda.quarterly_financials
        
        # Get Mag7 order data from SEC filings (would need separate scraper)
        mag7_orders = await fetch_mag7_orders()
        
        return {
            "financials": quarterly_data,
            "mag7_orders": mag7_orders
        }
    except Exception as e:
        print(f"Error fetching NVIDIA data: {e}")
        return None

# API endpoints
@app.get("/api/metrics/venture")
async def get_venture_metrics(start_date: str, end_date: str):
    db = SessionLocal()
    try:
        metrics = db.query(QuarterlyMetrics).filter(
            QuarterlyMetrics.metric_type == "venture_investment",
            QuarterlyMetrics.quarter.between(start_date, end_date)
        ).all()
        return metrics
    finally:
        db.close()

@app.get("/api/metrics/cloud")
async def get_cloud_metrics(start_date: str, end_date: str):
    db = SessionLocal()
    try:
        metrics = db.query(QuarterlyMetrics).filter(
            QuarterlyMetrics.metric_type == "cloud_workload",
            QuarterlyMetrics.quarter.between(start_date, end_date)
        ).all()
        return metrics
    finally:
        db.close()

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

# Data update scheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job("cron", day=1)
async def update_all_metrics():
    """
    Monthly update of all metrics
    """
    venture_data = await fetch_venture_data()
    cloud_data = await fetch_cloud_metrics()
    nvidia_data = await fetch_nvidia_data()
    
    db = SessionLocal()
    try:
        # Update database with new metrics
        # Implementation depends on data format from APIs
        pass
    finally:
        db.close()

scheduler.start()

# Add health check endpoint for Render
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database tables
@app.on_event("startup")
async def startup_event():
    try:
        logger.info(f"Attempting to connect to database...")
        Base.metadata.create_all(bind=engine)
        # Test the connection
        with SessionLocal() as session:
            session.execute("SELECT 1")
        logger.info("Successfully connected to database and created tables")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise 