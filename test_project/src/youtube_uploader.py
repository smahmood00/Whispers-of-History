#!/usr/bin/env python3
"""YouTube Uploader module for Bedtime History Pipeline"""

import os
import logging
import pickle
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from .config import YOUTUBE_SETTINGS

logger = logging.getLogger(__name__)

class YouTubeUploader:
    """Handles authentication and uploads to YouTube"""
    
    # YouTube API scopes
    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/youtube.force-ssl"
    ]
    
    # API service name and version
    API_SERVICE_NAME = "youtube"
    API_VERSION = "v3"
    
    def __init__(self, client_secrets_file: str = None, token_file: str = None):
        """Initialize the YouTube uploader
        
        Args:
            client_secrets_file: Path to client secrets JSON file (default: from config)
            token_file: Path to save/load OAuth token (default: from config)
        """
        # Set paths from config if not provided
        self.client_secrets_file = client_secrets_file or YOUTUBE_SETTINGS["client_secrets_file"]
        self.token_file = token_file or YOUTUBE_SETTINGS["token_file"]
        
        self.youtube_service = None

    def set_thumbnail(self, video_id: str, thumbnail_file: str) -> Dict[str, Any]:
        """Set a custom thumbnail for a video
        
        Args:
            video_id: The YouTube video ID
            thumbnail_file: Path to the thumbnail image file
            
        Returns:
            Dictionary with upload results or error information
        """
        if not self.youtube_service:
            if not self.authenticate():
                return {
                    "success": False,
                    "error": "Authentication failed",
                    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
                }

        if not os.path.exists(thumbnail_file):
            return {
                "success": False,
                "error": f"Thumbnail file not found: {thumbnail_file}",
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }

        try:
            logger.info(f"Setting thumbnail for video {video_id}...")
            
            # Create media upload for thumbnail
            media = MediaFileUpload(
                thumbnail_file,
                mimetype="image/png",
                resumable=True
            )
            
            # Set the thumbnail
            request = self.youtube_service.thumbnails().set(
                videoId=video_id,
                media_body=media
            )
            
            response = request.execute()
            
            logger.info(f"Thumbnail set successfully for video {video_id}")
            
            return {
                "success": True,
                "video_id": video_id,
                "thumbnail_url": response.get("items", [{}])[0].get("default", {}).get("url"),
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
            
        except HttpError as e:
            error_content = e.content.decode("utf-8") if hasattr(e, "content") else str(e)
            logger.error(f"YouTube API error: {error_content}")
            return {
                "success": False,
                "error": f"YouTube API error: {error_content}",
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
        except Exception as e:
            logger.error(f"Thumbnail upload failed: {str(e)}")
            return {
                "success": False,
                "error": f"Thumbnail upload failed: {str(e)}",
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }

    def upload_video_with_thumbnail(
        self,
        video_file: str,
        title: str,
        description: str,
        thumbnail_file: str = None,
        category_id: str = None,
        tags: Optional[list] = None,
        privacy_status: str = None,
        notify_subscribers: bool = None
    ) -> Dict[str, Any]:
        """Upload a video to YouTube and set its thumbnail
        
        Args:
            video_file: Path to the video file
            title: Video title
            description: Video description
            thumbnail_file: Path to thumbnail image file (optional)
            category_id: YouTube category ID (default: from config)
            tags: List of tags/keywords (default: from config)
            privacy_status: Privacy status (default: from config)
            notify_subscribers: Whether to notify subscribers (default: from config)
            
        Returns:
            Dictionary with upload results or error information
        """
        # First upload the video
        upload_result = self.upload_video(
            video_file=video_file,
            title=title,
            description=description,
            category_id=category_id,
            tags=tags,
            privacy_status=privacy_status,
            notify_subscribers=notify_subscribers
        )
        
        if not upload_result["success"]:
            return upload_result
            
        # If thumbnail provided, set it
        if thumbnail_file:
            thumbnail_result = self.set_thumbnail(
                video_id=upload_result["video_id"],
                thumbnail_file=thumbnail_file
            )
            
            if not thumbnail_result["success"]:
                logger.warning(f"Video uploaded but thumbnail setting failed: {thumbnail_result['error']}")
                upload_result["thumbnail_error"] = thumbnail_result["error"]
            else:
                upload_result["thumbnail_url"] = thumbnail_result["thumbnail_url"]
        
        return upload_result
    
    def authenticate(self) -> bool:
        """Authenticate with YouTube API
        
        Returns:
            True if authentication was successful, False otherwise
        """
        credentials = None
        
        # Check if token file exists
        if os.path.exists(self.token_file):
            logger.info(f"Loading credentials from {self.token_file}")
            with open(self.token_file, "rb") as token:
                credentials = pickle.load(token)
        
        # If credentials don't exist or are invalid, get new ones
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                logger.info("Refreshing access token...")
                credentials.refresh(Request())
            else:
                logger.info("Getting new credentials...")
                
                # Check if client secrets file exists
                if not os.path.exists(self.client_secrets_file):
                    logger.error(f"Client secrets file not found: {self.client_secrets_file}")
                    return False
                
                # Get credentials from OAuth flow
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.client_secrets_file, self.SCOPES
                    )
                    credentials = flow.run_local_server(port=8080)
                except Exception as e:
                    logger.error(f"Authentication failed: {str(e)}")
                    return False
            
            # Save credentials for future use
            with open(self.token_file, "wb") as token:
                pickle.dump(credentials, token)
        
        # Build YouTube API client
        try:
            self.youtube_service = build(
                self.API_SERVICE_NAME, self.API_VERSION, credentials=credentials
            )
            logger.info("YouTube API client created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create YouTube API client: {str(e)}")
            return False
    
    def upload_video(
        self,
        video_file: str,
        title: str,
        description: str,
        category_id: str = None,
        tags: Optional[list] = None,
        privacy_status: str = None,
        notify_subscribers: bool = None
    ) -> Dict[str, Any]:
        """Upload a video to YouTube
        
        Args:
            video_file: Path to the video file
            title: Video title
            description: Video description
            category_id: YouTube category ID (default: from config)
            tags: List of tags/keywords (default: from config)
            privacy_status: Privacy status (default: from config)
            notify_subscribers: Whether to notify subscribers (default: from config)
            
        Returns:
            Dictionary with upload results or error information
        """
        # Use defaults from config if not provided
        category_id = category_id or YOUTUBE_SETTINGS["default_category"]
        privacy_status = privacy_status or YOUTUBE_SETTINGS["default_privacy"]
        notify_subscribers = notify_subscribers if notify_subscribers is not None else YOUTUBE_SETTINGS["notify_subscribers"]
        
        if tags is None:
            tags = YOUTUBE_SETTINGS["default_tags"]
        
        # Check if authenticated
        if not self.youtube_service:
            if not self.authenticate():
                return {
                    "success": False,
                    "error": "Authentication failed",
                    "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
                }
        
        # Check if video file exists
        if not os.path.exists(video_file):
            return {
                "success": False,
                "error": f"Video file not found: {video_file}",
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
        
        # Prepare video metadata
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category_id
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False
            }
        }
        
        # Create upload request
        try:
            logger.info(f"Starting upload of {video_file}...")
            start_time = time.time()
            
            # Create media file upload
            media = MediaFileUpload(
                video_file,
                mimetype="video/*",
                resumable=True,
                chunksize=1024*1024*5  # 5MB chunks
            )
            
            # Create insert request
            insert_request = self.youtube_service.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media,
                notifySubscribers=notify_subscribers
            )
            
            # Execute upload with progress tracking
            response = None
            while response is None:
                status, response = insert_request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"Upload progress: {progress}%")
            
            end_time = time.time()
            upload_time = end_time - start_time
            
            # Get video ID from response
            video_id = response["id"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            logger.info(f"Upload complete! Video ID: {video_id}")
            logger.info(f"Video URL: {video_url}")
            
            return {
                "success": True,
                "video_id": video_id,
                "video_url": video_url,
                "upload_time": upload_time,
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
            
        except HttpError as e:
            error_content = e.content.decode("utf-8") if hasattr(e, "content") else str(e)
            logger.error(f"YouTube API error: {error_content}")
            return {
                "success": False,
                "error": f"YouTube API error: {error_content}",
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            return {
                "success": False,
                "error": f"Upload failed: {str(e)}",
                "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S")
            }
    
    def test(self) -> bool:
        """Test YouTube API connection
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Just authenticate to test connection
            if not self.authenticate():
                return False
                
            # Try a simple API call to verify - get video categories instead of channels
            try:
                categories_response = self.youtube_service.videoCategories().list(
                    part="snippet",
                    regionCode="US"
                ).execute()
                
                # Check if we got a valid response
                if categories_response and "items" in categories_response:
                    logger.info(f"Successfully connected to YouTube API")
                    return True
                else:
                    logger.error("Failed to retrieve video categories")
                    return False
            except Exception as e:
                logger.error(f"YouTube API test failed: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"YouTube API test failed: {str(e)}")
            return False


if __name__ == "__main__":
    # Configure logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Simple test if run directly
    uploader = YouTubeUploader()
    if uploader.test():
        logger.info("YouTube API connection test successful!")
    else:
        logger.error("YouTube API connection test failed!") 