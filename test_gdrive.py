#!/usr/bin/env python3
"""
Google Drive Upload Test Script
Uploads a file to Google Drive SEO/reports folder using API key
"""

import os
import sys

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
except ImportError:
    print("❌ Google API client library not installed")
    print("Install with: pip3 install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    sys.exit(1)

# Load environment variables from parent directory
print("🔧 Loading environment variables...")
try:
    from dotenv import load_dotenv
    # Try multiple possible .env locations
    env_paths = ['../.env', '../.env', '/Users/ankur/Documents/.env']
    loaded = False
    for env_path in env_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            print(f"✅ Environment variables loaded from {env_path}")
            loaded = True
            break
    if not loaded:
        print("⚠️ No .env file found, using system environment variables")
except ImportError:
    print("⚠️ python-dotenv not available, using system environment variables")
except Exception as e:
    print(f"⚠️ Error loading .env file: {e}")

def get_or_create_folder(service, folder_name, parent_id=None):
    """Get existing folder or create new one in Google Drive"""
    try:
        print(f"📁 Looking for folder '{folder_name}'...")
        
        # Build search query for the folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            query += f" and '{parent_id}' in parents"
            print(f"   Searching in parent folder ID: {parent_id}")
        else:
            print("   Searching in root directory")
        
        # Search for existing folder
        results = service.files().list(q=query).execute()
        folders = results.get('files', [])
        
        if folders:
            folder_id = folders[0]['id']
            print(f"✅ Found existing folder '{folder_name}' (ID: {folder_id})")
            return folder_id
        
        # Create new folder if not found
        print(f"📁 Creating new folder '{folder_name}'...")
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            folder_metadata['parents'] = [parent_id]
        
        folder = service.files().create(body=folder_metadata).execute()
        folder_id = folder['id']
        print(f"✅ Created folder '{folder_name}' (ID: {folder_id})")
        return folder_id
        
    except HttpError as e:
        print(f"❌ Google Drive API error in get_or_create_folder: {e}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error in get_or_create_folder: {e}")
        raise

def upload_file_to_drive(file_path, api_key):
    """Upload file to Google Drive SEO/reports folder"""
    try:
        print(f"🚀 Starting Google Drive upload process...")
        
        # Step 1: Build the Drive service using API key
        print(f"🔑 Authenticating with Google Drive API...")
        try:
            service = build('drive', 'v3', developerKey=api_key)
            print(f"✅ Google Drive service initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Google Drive service: {e}")
            return None
        
        # Step 2: Create folder structure SEO/reports
        print(f"📂 Setting up folder structure...")
        try:
            seo_folder_id = get_or_create_folder(service, 'SEO')
            reports_folder_id = get_or_create_folder(service, 'reports', seo_folder_id)
            print(f"✅ Folder structure ready: SEO/reports (ID: {reports_folder_id})")
        except Exception as e:
            print(f"❌ Failed to create folder structure: {e}")
            return None
        
        # Step 3: Determine MIME type based on file extension
        filename = os.path.basename(file_path)
        if file_path.endswith('.html'):
            mimetype = 'text/html'
        elif file_path.endswith('.json'):
            mimetype = 'application/json'
        elif file_path.endswith('.txt'):
            mimetype = 'text/plain'
        elif file_path.endswith('.pdf'):
            mimetype = 'application/pdf'
        else:
            mimetype = 'application/octet-stream'
        
        print(f"📄 File: {filename} (MIME type: {mimetype})")
        
        # Step 4: Prepare file metadata and media upload
        print(f"📤 Preparing file upload...")
        try:
            file_metadata = {
                'name': filename,
                'parents': [reports_folder_id]
            }
            media = MediaFileUpload(file_path, mimetype=mimetype)
            print(f"✅ File prepared for upload")
        except Exception as e:
            print(f"❌ Failed to prepare file for upload: {e}")
            return None
        
        # Step 5: Upload the file
        print(f"⬆️ Uploading file to Google Drive...")
        try:
            result = service.files().create(body=file_metadata, media_body=media).execute()
            file_id = result['id']
            print(f"✅ File uploaded successfully!")
            print(f"   📁 Folder: SEO/reports")
            print(f"   📄 File: {filename}")
            print(f"   🆔 File ID: {file_id}")
            print(f"   🔗 URL: https://drive.google.com/file/d/{file_id}/view")
            return file_id
        except HttpError as e:
            print(f"❌ Google Drive API error during upload: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error during upload: {e}")
            return None
        
    except Exception as e:
        print(f"❌ Critical error in upload_file_to_drive: {e}")
        return None

def main():
    """Main function - handles command line arguments and orchestrates the upload"""
    print("🚀 Google Drive Upload Test Script")
    print("=" * 40)
    
    # Step 1: Validate command line arguments
    if len(sys.argv) < 2:
        print("❌ Error: No file path provided")
        print("Usage: python test_gdrive.py <file_path>")
        print("Required environment variable: GOOGLE_CLOUD_API_KEY")
        sys.exit(1)
    
    file_path = sys.argv[1]
    print(f"📄 Target file: {file_path}")
    
    # Step 2: Check if file exists and get file info
    if not os.path.exists(file_path):
        print(f"❌ Error: File '{file_path}' not found")
        sys.exit(1)
    
    try:
        file_size = os.path.getsize(file_path)
        print(f"✅ File exists ({file_size:,} bytes)")
    except Exception as e:
        print(f"❌ Error reading file info: {e}")
        sys.exit(1)
    
    # Step 3: Get and validate API key
    print(f"🔑 Checking API key...")
    api_key = os.getenv('GOOGLE_CLOUD_API_KEY')
    if not api_key:
        # Try to set it directly from the known .env file
        try:
            with open('/Users/ankur/Documents/.env', 'r') as f:
                for line in f:
                    if line.startswith('GOOGLE_CLOUD_API_KEY='):
                        api_key = line.split('=', 1)[1].strip()
                        os.environ['GOOGLE_CLOUD_API_KEY'] = api_key
                        print(f"✅ API key loaded from .env file")
                        break
        except:
            pass
        
        if not api_key:
            print("❌ Error: GOOGLE_CLOUD_API_KEY environment variable not set")
            print("Make sure your .env file contains: GOOGLE_CLOUD_API_KEY=your_key_here")
            sys.exit(1)
    
    # Mask the API key for security (show only first/last few characters)
    masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***masked***"
    print(f"✅ API key found: {masked_key}")
    
    # Step 4: Start upload process
    print(f"\n📤 Starting upload process...")
    print(f"Target: Google Drive SEO/reports folder")
    print("-" * 40)
    
    try:
        file_id = upload_file_to_drive(file_path, api_key)
        if file_id:
            print(f"\n🎉 Upload completed successfully!")
            print(f"File ID: {file_id}")
        else:
            print(f"\n💥 Upload failed - check error messages above")
            sys.exit(1)
    except KeyboardInterrupt:
        print(f"\n⚠️ Upload cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()