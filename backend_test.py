#!/usr/bin/env python3
"""
Backend Test Suite for TikTok Downloader
Tests all API endpoints and core functionality
"""

import requests
import json
import time
import sys
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

print(f"Testing TikTok Downloader Backend at: {API_URL}")
print("=" * 60)

class TikTokDownloaderTest:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, message="", details=None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"    {message}")
        if details:
            print(f"    Details: {details}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'details': details
        })
        print()
    
    def test_basic_connectivity(self):
        """Test basic API connectivity"""
        try:
            response = self.session.get(f"{API_URL}/")
            if response.status_code == 200:
                data = response.json()
                if "Pro TikTok Downloader API" in data.get("message", ""):
                    self.log_test("Basic API Connectivity", True, "API is responding correctly")
                    return True
                else:
                    self.log_test("Basic API Connectivity", False, f"Unexpected response: {data}")
                    return False
            else:
                self.log_test("Basic API Connectivity", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Basic API Connectivity", False, f"Connection error: {str(e)}")
            return False
    
    def test_download_endpoint_validation(self):
        """Test download endpoint input validation"""
        try:
            # Test empty URLs
            response = self.session.post(f"{API_URL}/download", json={"urls": []})
            if response.status_code == 400:
                self.log_test("Download Validation - Empty URLs", True, "Correctly rejects empty URL list")
            else:
                self.log_test("Download Validation - Empty URLs", False, f"Expected 400, got {response.status_code}")
                return False
            
            # Test invalid JSON
            response = self.session.post(f"{API_URL}/download", json={})
            if response.status_code == 422:  # FastAPI validation error
                self.log_test("Download Validation - Missing URLs", True, "Correctly validates required fields")
            else:
                self.log_test("Download Validation - Missing URLs", False, f"Expected 422, got {response.status_code}")
                return False
                
            return True
        except Exception as e:
            self.log_test("Download Validation", False, f"Error: {str(e)}")
            return False
    
    def test_tiktok_download_single(self):
        """Test single TikTok video download"""
        # Using a public TikTok URL that should be accessible
        test_url = "https://www.tiktok.com/@zachking/video/6768504823336815877"
        
        try:
            # Start download
            response = self.session.post(f"{API_URL}/download", json={
                "urls": [test_url],
                "quality": "ultra_hd"
            })
            
            if response.status_code != 200:
                self.log_test("TikTok Single Download - Start", False, 
                            f"Failed to start download: HTTP {response.status_code} - {response.text}")
                return False
            
            data = response.json()
            batch_id = data.get("batch_id")
            
            if not batch_id:
                self.log_test("TikTok Single Download - Start", False, "No batch_id returned")
                return False
            
            self.log_test("TikTok Single Download - Start", True, f"Download started with batch_id: {batch_id}")
            
            # Wait and check batch status
            max_wait = 60  # 60 seconds max wait
            wait_time = 0
            
            while wait_time < max_wait:
                time.sleep(5)
                wait_time += 5
                
                try:
                    status_response = self.session.get(f"{API_URL}/batch/{batch_id}/status")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        downloads = status_data.get("downloads", [])
                        
                        if downloads:
                            download = downloads[0]
                            status = download.get("status")
                            
                            print(f"    Status after {wait_time}s: {status}")
                            
                            if status == "completed":
                                self.log_test("TikTok Single Download - Complete", True, 
                                            f"Download completed successfully. Title: {download.get('title', 'N/A')}")
                                
                                # Test file download endpoint
                                download_id = download.get("id")
                                if download_id:
                                    file_response = self.session.get(f"{API_URL}/download/{download_id}/file")
                                    if file_response.status_code == 200:
                                        self.log_test("File Download Endpoint", True, 
                                                    f"File served successfully, size: {len(file_response.content)} bytes")
                                    else:
                                        self.log_test("File Download Endpoint", False, 
                                                    f"HTTP {file_response.status_code}")
                                
                                return True
                            elif status == "failed":
                                error_msg = download.get("error_message", "Unknown error")
                                self.log_test("TikTok Single Download - Complete", False, 
                                            f"Download failed: {error_msg}")
                                return False
                    else:
                        print(f"    Status check failed: HTTP {status_response.status_code}")
                        
                except Exception as e:
                    print(f"    Status check error: {str(e)}")
            
            self.log_test("TikTok Single Download - Complete", False, 
                        f"Download did not complete within {max_wait} seconds")
            return False
            
        except Exception as e:
            self.log_test("TikTok Single Download", False, f"Error: {str(e)}")
            return False
    
    def test_download_history(self):
        """Test download history endpoint"""
        try:
            response = self.session.get(f"{API_URL}/downloads")
            if response.status_code == 200:
                downloads = response.json()
                self.log_test("Download History", True, f"Retrieved {len(downloads)} download records")
                
                # Check if we have any downloads with proper structure
                if downloads:
                    first_download = downloads[0]
                    required_fields = ['id', 'url', 'status', 'created_at']
                    missing_fields = [field for field in required_fields if field not in first_download]
                    
                    if not missing_fields:
                        self.log_test("Download Record Structure", True, "Download records have required fields")
                    else:
                        self.log_test("Download Record Structure", False, f"Missing fields: {missing_fields}")
                
                return True
            else:
                self.log_test("Download History", False, f"HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            self.log_test("Download History", False, f"Error: {str(e)}")
            return False
    
    def test_invalid_urls(self):
        """Test handling of invalid URLs"""
        invalid_urls = [
            "https://invalid-url.com/video",
            "not-a-url",
            "https://youtube.com/watch?v=invalid"  # Non-TikTok URL
        ]
        
        try:
            response = self.session.post(f"{API_URL}/download", json={
                "urls": invalid_urls
            })
            
            if response.status_code == 200:
                data = response.json()
                batch_id = data.get("batch_id")
                
                # Wait a bit and check if downloads failed appropriately
                time.sleep(10)
                
                status_response = self.session.get(f"{API_URL}/batch/{batch_id}/status")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    downloads = status_data.get("downloads", [])
                    
                    failed_count = sum(1 for d in downloads if d.get("status") == "failed")
                    
                    if failed_count > 0:
                        self.log_test("Invalid URL Handling", True, 
                                    f"{failed_count}/{len(downloads)} invalid URLs properly failed")
                    else:
                        self.log_test("Invalid URL Handling", False, 
                                    "Invalid URLs should have failed but didn't")
                else:
                    self.log_test("Invalid URL Handling", False, "Could not check batch status")
            else:
                self.log_test("Invalid URL Handling", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Invalid URL Handling", False, f"Error: {str(e)}")
    
    def test_batch_processing(self):
        """Test batch processing with multiple URLs"""
        # Using multiple test URLs (some may work, some may not)
        test_urls = [
            "https://www.tiktok.com/@zachking/video/6768504823336815877",
            "https://www.tiktok.com/@zachking/video/6829267836783619334"
        ]
        
        try:
            response = self.session.post(f"{API_URL}/download", json={
                "urls": test_urls
            })
            
            if response.status_code == 200:
                data = response.json()
                batch_id = data.get("batch_id")
                total_urls = data.get("total_urls")
                
                if total_urls == len(test_urls):
                    self.log_test("Batch Processing - Start", True, 
                                f"Batch started with {total_urls} URLs")
                    
                    # Check batch status
                    time.sleep(5)
                    status_response = self.session.get(f"{API_URL}/batch/{batch_id}/status")
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        downloads = status_data.get("downloads", [])
                        
                        if len(downloads) == len(test_urls):
                            self.log_test("Batch Processing - Tracking", True, 
                                        f"All {len(downloads)} downloads are being tracked")
                        else:
                            self.log_test("Batch Processing - Tracking", False, 
                                        f"Expected {len(test_urls)} downloads, got {len(downloads)}")
                    else:
                        self.log_test("Batch Processing - Tracking", False, 
                                    f"Could not get batch status: HTTP {status_response.status_code}")
                else:
                    self.log_test("Batch Processing - Start", False, 
                                f"Expected {len(test_urls)} URLs, got {total_urls}")
            else:
                self.log_test("Batch Processing", False, f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Batch Processing", False, f"Error: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print("Starting TikTok Downloader Backend Tests...")
        print()
        
        # Test basic connectivity first
        if not self.test_basic_connectivity():
            print("❌ Basic connectivity failed. Stopping tests.")
            return False
        
        # Test input validation
        self.test_download_endpoint_validation()
        
        # Test download history (should work even if empty)
        self.test_download_history()
        
        # Test invalid URL handling
        self.test_invalid_urls()
        
        # Test batch processing
        self.test_batch_processing()
        
        # Test actual TikTok download (most important)
        self.test_tiktok_download_single()
        
        # Print summary
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed. Check details above.")
            return False

if __name__ == "__main__":
    tester = TikTokDownloaderTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)