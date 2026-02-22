# YT Manager (YTStorage)

YT Manager is a modern, web-based YouTube video management application built with FastAPI and Celery. It provides a Google Drive-like interface to schedule, upload, manage, and download your YouTube videos directly from your local machine, leveraging background task processing for a seamless user experience.

## Features

- **Modern Google Drive-Like UI**: Clean, responsive interface styled with Tailwind CSS.
- **Background Upload Processing**: Utilizes Celery and Redis to handle video uploads asynchronously, preventing the web interface from freezing during large file transfers.
- **OAuth 2.0 Authentication**: Securely links and stores refresh tokens for your YouTube account.
- **Job Tracking**: Detailed tracking of upload status (Pending, Uploading, Published, Failed) backed by an SQLite database.
- **Download Capability**: Bypasses the YouTube web player to allow direct downloading of your uploaded videos using `yt-dlp`.
- **Filtered YouTube Feed**: A dedicated "My Drive" tab that syncs with your channel to display Public and Unlisted videos.

## Prerequisites

- **Python 3.9+**
- **Redis**: Required as the message broker for Celery.
  - *Windows Users*: You can use [Memurai](https://www.memurai.com/) or run Redis via WSL/Docker.
- **Google Cloud Console Project**: You must have a project with the **YouTube Data API v3** enabled.

## Setup Instructions

### 1. Configure Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create an **OAuth 2.0 Client ID** (Application type: "Web application").
3. Add `http://localhost:8000/auth/youtube/callback` to the Authorized redirect URIs.
4. Download the JSON credentials file, rename it to `credentials.json`, and place it in the root directory of this project.

### 2. Environment Variables

Create a `.env` file in the root directory of the project and add your Google Client ID and Secret (these can be found inside your `credentials.json`):

```ini
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret
```

### 3. Install Dependencies

Create a virtual environment (optional but recommended) and install the required Python packages:

```bash
pip install -r requirements.txt
```

### 4. Initialize the Database

Apply Alembic migrations to set up the SQLite database schema:

```bash
alembic upgrade head
```

## Running the Application

You will need to run three separate processes/terminal windows to bring up the full stack:

**1. Start the Redis Server**
Ensure your Redis server is running on the default port (`localhost:6379`).

**2. Start the Celery Worker**
This worker handles the heavy lifting of uploading videos to YouTube in the background. If you are on Windows, use the `--pool=solo` flag:
```bash
celery -A src.services.bg.tasks worker --loglevel=info --pool=solo
```

**3. Start the FastAPI Web Server**
Launch the Uvicorn ASGI server to host the web interface:
```bash
uvicorn src.main:app --reload --port 8000
```

## Usage

1. Open your browser and navigate to `http://localhost:8000`.
2. Click **"Link Account"** in the sidebar to authenticate with your YouTube account.
3. Once authenticated, click **"New Upload"**.
4. Select your video file, give it a title and description, and click "Queue Upload". 
5. The video will be uploaded as **Unlisted** in the background. You can monitor its progress from the "Recent Uploads" or "New Upload" page.
6. Once uploaded, click "View" to open it on YouTube, or "Download" to save a local copy.

## Technologies Used

- **Backend**: FastAPI, SQLAlchemy, Celery
- **Frontend**: Jinja2 Templates, Tailwind CSS
- **APIs & Tools**: Google API Python Client, `yt-dlp`, HTTPX
- **Database / Broker**: SQLite, Redis
