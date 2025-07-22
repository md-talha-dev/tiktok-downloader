from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import yt_dlp
import asyncio
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
import base64


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create downloads directory
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Create the main app without a prefix
app = FastAPI(title="Pro TikTok Downloader")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Thread pool for background downloads
executor = ThreadPoolExecutor(max_workers=3)

# Define Models
class DownloadRequest(BaseModel):
    urls: List[str]
    quality: Optional[str] = "ultra_hd"
    
class DownloadStatus(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    status: str  # "pending", "downloading", "completed", "failed"
    filename: Optional[str] = None
    file_size: Optional[int] = None
    title: Optional[str] = None
    duration: Optional[float] = None
    thumbnail: Optional[str] = None  # base64 encoded
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class BatchDownloadResponse(BaseModel):
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    total_urls: int
    message: str

def get_ydl_opts(output_path: str):
    """Get yt-dlp options for ultra HD download without watermarks"""
    return {
        'format': 'bestvideo[height>=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'writethumbnail': True,
        'writeinfojson': True,
        'postprocessors': [
            {
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            },
            {
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False,
            }
        ],
        'merge_output_format': 'mp4',
        'restrictfilenames': True,
        'noplaylist': True,
        'extract_flat': False,
        'ignoreerrors': False,
        'no_warnings': False,
    }

def download_single_video(url: str, download_id: str):
    """Download a single TikTok video"""
    try:
        # Update status to downloading
        asyncio.create_task(update_download_status(download_id, "downloading"))
        
        output_filename = f"{download_id}.%(ext)s"
        output_path = DOWNLOADS_DIR / output_filename
        
        ydl_opts = get_ydl_opts(str(output_path))
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info first
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
            # Download the video
            ydl.download([url])
            
            # Find the downloaded file
            downloaded_files = list(DOWNLOADS_DIR.glob(f"{download_id}.*"))
            video_file = None
            for file in downloaded_files:
                if file.suffix in ['.mp4', '.webm', '.mkv']:
                    video_file = file
                    break
            
            if not video_file:
                raise Exception("Downloaded video file not found")
            
            # Get file size
            file_size = video_file.stat().st_size
            
            # Try to get thumbnail and convert to base64
            thumbnail_base64 = None
            thumbnail_files = list(DOWNLOADS_DIR.glob(f"{download_id}.webp")) + list(DOWNLOADS_DIR.glob(f"{download_id}.jpg"))
            if thumbnail_files:
                try:
                    with open(thumbnail_files[0], 'rb') as f:
                        thumbnail_base64 = base64.b64encode(f.read()).decode('utf-8')
                    # Clean up thumbnail file
                    thumbnail_files[0].unlink()
                except Exception as e:
                    logging.warning(f"Could not process thumbnail: {e}")
            
            # Update status to completed
            asyncio.create_task(update_download_status(
                download_id, 
                "completed", 
                filename=video_file.name,
                file_size=file_size,
                title=title,
                duration=duration,
                thumbnail=thumbnail_base64
            ))
            
            # Clean up info json file
            info_files = list(DOWNLOADS_DIR.glob(f"{download_id}.info.json"))
            for info_file in info_files:
                info_file.unlink()
                
    except Exception as e:
        logging.error(f"Download failed for {url}: {str(e)}")
        asyncio.create_task(update_download_status(download_id, "failed", error_message=str(e)))

async def update_download_status(download_id: str, status: str, **kwargs):
    """Update download status in database"""
    update_data = {"status": status}
    if status == "completed":
        update_data["completed_at"] = datetime.utcnow()
    
    for key, value in kwargs.items():
        if value is not None:
            update_data[key] = value
    
    await db.downloads.update_one(
        {"id": download_id},
        {"$set": update_data}
    )

@api_router.post("/download", response_model=BatchDownloadResponse)
async def download_videos(request: DownloadRequest, background_tasks: BackgroundTasks):
    """Start downloading TikTok videos"""
    if not request.urls:
        raise HTTPException(status_code=400, detail="No URLs provided")
    
    batch_id = str(uuid.uuid4())
    download_tasks = []
    
    # Create download records for each URL
    for url in request.urls:
        download_id = str(uuid.uuid4())
        download_record = DownloadStatus(
            id=download_id,
            url=url,
            status="pending"
        )
        
        # Insert into database
        await db.downloads.insert_one(download_record.dict())
        
        # Add background task
        background_tasks.add_task(download_single_video, url, download_id)
        download_tasks.append(download_id)
    
    # Store batch info
    await db.batches.insert_one({
        "batch_id": batch_id,
        "download_ids": download_tasks,
        "created_at": datetime.utcnow(),
        "total_urls": len(request.urls)
    })
    
    return BatchDownloadResponse(
        batch_id=batch_id,
        total_urls=len(request.urls),
        message=f"Started downloading {len(request.urls)} videos"
    )

@api_router.get("/download/{download_id}/status", response_model=DownloadStatus)
async def get_download_status(download_id: str):
    """Get download status"""
    download = await db.downloads.find_one({"id": download_id})
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    
    return DownloadStatus(**download)

@api_router.get("/batch/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """Get status of all downloads in a batch"""
    batch = await db.batches.find_one({"batch_id": batch_id})
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    # Get status of all downloads in batch
    downloads = await db.downloads.find(
        {"id": {"$in": batch["download_ids"]}}
    ).to_list(None)
    
    status_counts = {}
    for download in downloads:
        status = download["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return {
        "batch_id": batch_id,
        "total_urls": batch["total_urls"],
        "status_counts": status_counts,
        "downloads": [DownloadStatus(**download) for download in downloads]
    }

@api_router.get("/download/{download_id}/file")
async def download_file(download_id: str):
    """Download the video file"""
    download = await db.downloads.find_one({"id": download_id})
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    
    if download["status"] != "completed":
        raise HTTPException(status_code=400, detail="Download not completed yet")
    
    file_path = DOWNLOADS_DIR / download["filename"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=download["filename"],
        media_type='video/mp4'
    )

@api_router.get("/downloads")
async def get_all_downloads():
    """Get all download records"""
    downloads = await db.downloads.find().sort("created_at", -1).to_list(50)
    return [DownloadStatus(**download) for download in downloads]

@api_router.delete("/download/{download_id}")
async def delete_download(download_id: str):
    """Delete a download record and file"""
    download = await db.downloads.find_one({"id": download_id})
    if not download:
        raise HTTPException(status_code=404, detail="Download not found")
    
    # Delete file if exists
    if download.get("filename"):
        file_path = DOWNLOADS_DIR / download["filename"]
        if file_path.exists():
            file_path.unlink()
    
    # Delete from database
    await db.downloads.delete_one({"id": download_id})
    
    return {"message": "Download deleted successfully"}

@api_router.get("/")
async def root():
    return {"message": "Pro TikTok Downloader API", "version": "1.0"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()