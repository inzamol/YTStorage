from sqlalchemy import Enum
import enum

class UploadStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    uploaded = "uploaded"
    failed = "failed"