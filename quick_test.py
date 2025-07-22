#!/usr/bin/env python3
"""
Quick TikTok Download Test
"""

import requests
import json
import time
from pathlib import Path

# Get backend URL from frontend .env file
def get_backend_url():
    env_file = Path("/app/frontend/.env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    return "http://localhost:8001"

BASE_URL = get_backend_url()
API_URL = f"{BASE_URL}/api"

print(f"Testing single TikTok download at: {API_URL}")

# Test with a simple TikTok URL
test_url = "https://www.tiktok.com/@zachking/video/6768504823336815877"

try:
    # Start download
    response = requests.post(f"{API_URL}/download", json={
        "urls": [test_url],
        "quality": "ultra_hd"
    })
    
    if response.status_code != 200:
        print(f"❌ Failed to start download: HTTP {response.status_code} - {response.text}")
        exit(1)
    
    data = response.json()
    batch_id = data.get("batch_id")
    print(f"✅ Download started with batch_id: {batch_id}")
    
    # Wait and check status
    for i in range(12):  # 60 seconds total
        time.sleep(5)
        
        status_response = requests.get(f"{API_URL}/batch/{batch_id}/status")
        if status_response.status_code == 200:
            status_data = status_response.json()
            downloads = status_data.get("downloads", [])
            
            if downloads:
                download = downloads[0]
                status = download.get("status")
                
                print(f"Status after {(i+1)*5}s: {status}")
                
                if status == "completed":
                    print(f"✅ Download completed successfully!")
                    print(f"   Title: {download.get('title', 'N/A')}")
                    print(f"   File: {download.get('filename', 'N/A')}")
                    print(f"   Size: {download.get('file_size', 0)} bytes")
                    exit(0)
                elif status == "failed":
                    error_msg = download.get("error_message", "Unknown error")
                    print(f"❌ Download failed: {error_msg}")
                    exit(1)
        else:
            print(f"Status check failed: HTTP {status_response.status_code}")
    
    print("❌ Download did not complete within 60 seconds")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    exit(1)