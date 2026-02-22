from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from src.services.file_service import FileService
from src.core.config import get_settings

settings = get_settings()


class UploadService(FileService):
    def __init__(self):
        pass
    def upload_video(self, refresh_token, file_path, file_name, description, category_id, privacy_status, mime_type="application/octet-stream"):
        creds = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET
        )

        youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": file_name,
                    "description": description,
                    "categoryId": category_id
                },
                "status": {"privacyStatus": privacy_status}
            },
            media_body=MediaFileUpload(file_path, mimetype=mime_type, resumable=True)
        )

        response = request.execute()
        return response["id"]