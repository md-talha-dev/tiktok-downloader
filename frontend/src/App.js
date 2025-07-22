import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const App = () => {
  const [urls, setUrls] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [currentBatch, setCurrentBatch] = useState(null);
  const [downloads, setDownloads] = useState([]);
  const [allDownloads, setAllDownloads] = useState([]);

  // Fetch all downloads on component mount
  useEffect(() => {
    fetchAllDownloads();
  }, []);

  // Poll batch status if there's an active batch
  useEffect(() => {
    let interval;
    if (currentBatch) {
      interval = setInterval(() => {
        fetchBatchStatus();
      }, 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [currentBatch]);

  const fetchAllDownloads = async () => {
    try {
      const response = await axios.get(`${API}/downloads`);
      setAllDownloads(response.data);
    } catch (error) {
      console.error("Error fetching downloads:", error);
    }
  };

  const fetchBatchStatus = async () => {
    if (!currentBatch) return;
    
    try {
      const response = await axios.get(`${API}/batch/${currentBatch}/status`);
      setDownloads(response.data.downloads);
      
      // Check if all downloads are completed or failed
      const pendingCount = response.data.status_counts.pending || 0;
      const downloadingCount = response.data.status_counts.downloading || 0;
      
      if (pendingCount === 0 && downloadingCount === 0) {
        setCurrentBatch(null);
        setIsLoading(false);
        fetchAllDownloads(); // Refresh the full list
      }
    } catch (error) {
      console.error("Error fetching batch status:", error);
    }
  };

  const handleDownload = async () => {
    if (!urls.trim()) {
      alert("Please enter at least one TikTok URL");
      return;
    }

    const urlList = urls.split('\n')
      .map(url => url.trim())
      .filter(url => url && url.includes('tiktok.com'));

    if (urlList.length === 0) {
      alert("Please enter valid TikTok URLs");
      return;
    }

    setIsLoading(true);
    
    try {
      const response = await axios.post(`${API}/download`, {
        urls: urlList,
        quality: "ultra_hd"
      });
      
      setCurrentBatch(response.data.batch_id);
      setUrls(""); // Clear input
    } catch (error) {
      console.error("Error starting download:", error);
      alert("Failed to start download: " + (error.response?.data?.detail || error.message));
      setIsLoading(false);
    }
  };

  const downloadFile = async (downloadId, filename) => {
    try {
      const response = await axios.get(`${API}/download/${downloadId}/file`, {
        responseType: 'blob',
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error downloading file:", error);
      alert("Failed to download file");
    }
  };

  const deleteDownload = async (downloadId) => {
    if (!window.confirm("Are you sure you want to delete this download?")) return;
    
    try {
      await axios.delete(`${API}/download/${downloadId}`);
      fetchAllDownloads();
      // Also remove from current downloads if present
      setDownloads(prev => prev.filter(d => d.id !== downloadId));
    } catch (error) {
      console.error("Error deleting download:", error);
      alert("Failed to delete download");
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pending':
        return '⏳';
      case 'downloading':
        return '⬇️';
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      default:
        return '❓';
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'Unknown';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-blue-900 to-indigo-900">
      {/* Header */}
      <header className="text-center py-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-black/20"></div>
        <div className="relative z-10">
          <h1 className="text-6xl font-bold bg-gradient-to-r from-pink-400 via-purple-400 to-blue-400 bg-clip-text text-transparent animate-pulse">
            Pro TikTok Downloader
          </h1>
          <p className="text-xl text-gray-300 mt-4">Ultra HD • No Watermarks • Lightning Fast</p>
          
          {/* Feature badges */}
          <div className="flex justify-center mt-8 space-x-6">
            <div className="bg-gradient-to-r from-green-400 to-emerald-500 rounded-full px-6 py-2 text-white font-semibold shadow-lg transform hover:scale-105 transition-transform">
              ✨ No Ads
            </div>
            <div className="bg-gradient-to-r from-blue-400 to-cyan-500 rounded-full px-6 py-2 text-white font-semibold shadow-lg transform hover:scale-105 transition-transform">
              📦 Bulk Downloader
            </div>
            <div className="bg-gradient-to-r from-purple-400 to-pink-500 rounded-full px-6 py-2 text-white font-semibold shadow-lg transform hover:scale-105 transition-transform">
              🎬 Ultra HD
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 pb-12">
        {/* Download Section */}
        <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-8 shadow-2xl border border-white/20 mb-8">
          <h2 className="text-2xl font-bold text-white mb-6">Download TikTok Videos</h2>
          
          <div className="space-y-6">
            <div>
              <label className="block text-white font-medium mb-3">
                TikTok URLs (one per line):
              </label>
              <textarea
                value={urls}
                onChange={(e) => setUrls(e.target.value)}
                className="w-full h-32 bg-white/10 border border-white/30 rounded-xl px-4 py-3 text-white placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent resize-none"
                placeholder="https://www.tiktok.com/@username/video/1234567890123456789&#10;https://www.tiktok.com/@username/video/9876543210987654321"
                disabled={isLoading}
              />
            </div>
            
            <button
              onClick={handleDownload}
              disabled={isLoading || !urls.trim()}
              className={`w-full py-4 rounded-xl font-bold text-lg transition-all duration-300 ${
                isLoading || !urls.trim()
                  ? 'bg-gray-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-pink-500 via-purple-500 to-blue-500 hover:from-pink-600 hover:via-purple-600 hover:to-blue-600 transform hover:scale-105 shadow-lg'
              } text-white`}
            >
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white mr-3"></div>
                  Processing Downloads...
                </div>
              ) : (
                '⬇️ Start Download'
              )}
            </button>
          </div>
        </div>

        {/* Current Batch Progress */}
        {currentBatch && downloads.length > 0 && (
          <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-6 shadow-2xl border border-white/20 mb-8">
            <h3 className="text-xl font-bold text-white mb-4">Current Downloads</h3>
            <div className="space-y-3">
              {downloads.map((download) => (
                <div key={download.id} className="bg-white/5 rounded-xl p-4 border border-white/10">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <span className="text-2xl">{getStatusIcon(download.status)}</span>
                      <div>
                        <div className="text-white font-medium truncate max-w-xs">
                          {download.title || 'Untitled'}
                        </div>
                        <div className="text-gray-400 text-sm">{download.status}</div>
                      </div>
                    </div>
                    {download.status === 'completed' && (
                      <button
                        onClick={() => downloadFile(download.id, download.filename)}
                        className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg transition-colors"
                      >
                        Download
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Download History */}
        {allDownloads.length > 0 && (
          <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-6 shadow-2xl border border-white/20">
            <h3 className="text-xl font-bold text-white mb-4">Download History</h3>
            <div className="grid gap-4">
              {allDownloads.map((download) => (
                <div key={download.id} className="bg-white/5 rounded-xl p-4 border border-white/10">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <span className="text-2xl">{getStatusIcon(download.status)}</span>
                      
                      {download.thumbnail && (
                        <img
                          src={`data:image/webp;base64,${download.thumbnail}`}
                          alt="Thumbnail"
                          className="w-16 h-16 rounded-lg object-cover"
                        />
                      )}
                      
                      <div>
                        <div className="text-white font-medium truncate max-w-md">
                          {download.title || 'Untitled'}
                        </div>
                        <div className="text-gray-400 text-sm flex space-x-4">
                          <span>Status: {download.status}</span>
                          {download.file_size && <span>Size: {formatFileSize(download.file_size)}</span>}
                          {download.duration && <span>Duration: {formatDuration(download.duration)}</span>}
                        </div>
                        {download.error_message && (
                          <div className="text-red-400 text-sm mt-1">
                            Error: {download.error_message}
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex space-x-2">
                      {download.status === 'completed' && download.filename && (
                        <button
                          onClick={() => downloadFile(download.id, download.filename)}
                          className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg transition-colors"
                        >
                          Download
                        </button>
                      )}
                      <button
                        onClick={() => deleteDownload(download.id)}
                        className="bg-red-500 hover:bg-red-600 text-white px-3 py-2 rounded-lg transition-colors"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="text-center py-8 text-white/70">
        <div className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
          Developed by Md. Talha
        </div>
      </footer>
    </div>
  );
};

export default App;