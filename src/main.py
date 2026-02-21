from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

app = FastAPI()

CLIENT_SECRETS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
REDIRECT_URI = "http://localhost:8000/auth/youtube/callback"

@app.get("/auth/youtube")
def auth_youtube():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent"
    )

    return RedirectResponse(authorization_url)


@app.get("/auth/youtube/callback")
def youtube_callback(code: str):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )

    flow.fetch_token(code=code)
    credentials = flow.credentials

    refresh_token = credentials.refresh_token

    # 🔥 SAVE refresh_token in your DB linked to user
    print(refresh_token)

    return {"message": "YouTube connected"}