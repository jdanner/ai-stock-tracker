from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
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

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Set up templates
templates = Jinja2Templates(directory="templates")

# Database setup
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class NvidiaMetrics(Base):
    __tablename__ = "nvidia_metrics"
    id = Column(Integer, primary_key=True)
    quarter = Column(String)
    revenue = Column(Float)
    net_income = Column(Float)
    gross_margin = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

def calculate_growth_rates(data: List[Dict]) -> List[Dict]:
    """Calculate QoQ and YoY growth rates for metrics"""
    # Sort data chronologically
    sorted_data = sorted(data, key=lambda x: (int(x['quarter'][:4]), int(x['quarter'][5])))
    
    for i, quarter in enumerate(sorted_data):
        # Initialize growth rates
        quarter['revenue_qoq'] = None
        quarter['revenue_yoy'] = None
        
        # Calculate QoQ growth rate
        if i > 0:
            prev_revenue = sorted_data[i-1]['revenue']
            if prev_revenue != 0:
                quarter['revenue_qoq'] = ((quarter['revenue'] - prev_revenue) / prev_revenue) * 100
        
        # Calculate YoY growth rate (4 quarters ago)
        if i >= 4:
            year_ago_revenue = sorted_data[i-4]['revenue']
            if year_ago_revenue != 0:
                quarter['revenue_yoy'] = ((quarter['revenue'] - year_ago_revenue) / year_ago_revenue) * 100
    
    return sorted_data

async def fetch_nvidia_data():
    """Fetch NVIDIA's key financial metrics"""
    try:
        # NVIDIA quarterly revenue data from official earnings releases and 10-Q filings
        real_data = [
            {
                'quarter': '2025Q3', 'revenue': 35082000000, 
                'net_income': 9243000000, 'gross_margin': 74.0,
                'customer_concentration': 36  # 12%+12%+12%
            },
            {
                'quarter': '2025Q2', 'revenue': 30040000000,
                'net_income': 6188000000, 'gross_margin': 70.1,
                'customer_concentration': 45  # 11%+11%+11%+12%
            },
            {
                'quarter': '2025Q1', 'revenue': 26044000000,
                'net_income': 2043000000, 'gross_margin': 64.6,
                'customer_concentration': 45  # 11%+11%+11%+12%
            },
            {
                'quarter': '2024Q4', 'revenue': 22103000000,
                'net_income': 1410000000, 'gross_margin': 63.3,
                'customer_concentration': 0  # Need to find
            },
            {
                'quarter': '2024Q3', 'revenue': 18120000000,
                'net_income': 1336000000, 'gross_margin': 62.7,
                'customer_concentration': 19  # One customer
            },
            {
                'quarter': '2024Q2', 'revenue': 13507000000,
                'net_income': 1618000000, 'gross_margin': 64.8,
                'customer_concentration': 18  # One customer
            },
            {
                'quarter': '2024Q1', 'revenue': 7192000000,
                'net_income': 1912000000, 'gross_margin': 65.5,
                'customer_concentration': 14  # One customer
            },
            {
                'quarter': '2023Q4', 'revenue': 6051000000,
                'net_income': 1788000000, 'gross_margin': 65.4,
                'customer_concentration': 13  # One customer
            }
        ]
        
        # Calculate growth rates
        data_with_growth = calculate_growth_rates(real_data)
        return sorted(data_with_growth, key=lambda x: x['quarter'], reverse=True)
    except Exception as e:
        logger.error(f"Error fetching NVIDIA data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch NVIDIA data: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/nvidia")
async def get_nvidia_metrics():
    """Get latest NVIDIA metrics"""
    try:
        data = await fetch_nvidia_data()
        return {
            "status": "success",
            "data": data,
            "updated_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in get_nvidia_metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Create tables on startup"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise 