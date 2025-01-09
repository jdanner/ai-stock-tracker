from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
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

async def fetch_nvidia_data():
    """Fetch NVIDIA's key financial metrics"""
    try:
        nvda = yf.Ticker("NVDA")
        financials = nvda.quarterly_financials
        
        data = []
        for date in financials.columns:
            try:
                quarter = f"{date.year}Q{(date.month-1)//3 + 1}"
                metrics = {
                    'quarter': quarter,
                    'revenue': float(financials.loc['Total Revenue', date]),
                    'net_income': float(financials.loc['Net Income', date]),
                    'gross_margin': float(financials.loc['Gross Profit', date]) / float(financials.loc['Total Revenue', date]) * 100
                }
                data.append(metrics)
            except Exception as e:
                logger.error(f"Error processing quarter {quarter}: {e}")
                continue
                
        return sorted(data, key=lambda x: x['quarter'], reverse=True)
    except Exception as e:
        logger.error(f"Error fetching NVIDIA data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch NVIDIA data: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def root(request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/nvidia")
async def get_nvidia_metrics():
    """Get latest NVIDIA metrics"""
    try:
        data = await fetch_nvidia_data()
        return {
            "status": "success",
            "data": data[:8],  # Last 8 quarters
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