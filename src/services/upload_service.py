from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()   


class UploadService(FileService):
    def __init__(self):
        pass
    def upload_video(refresh_token, file_path, file_name, description, category_id, privacy_status):
        creds = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=os.getenv("GOOGLE_CLIENT_ID"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET")
        )

        youtube = build("youtube", "v3", credentials=creds)

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
            media_body=MediaFileUpload(file_path)
        )

        response = request.execute()
        return response["id"]