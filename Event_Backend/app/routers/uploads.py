from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.core.roles import UserRole
from app.core.security import require_roles
from app.models.user import User

router = APIRouter(prefix="/uploads", tags=["uploads"])

MAX_IMAGE_SIZE = 5 * 1024 * 1024
IMAGE_FORMATS = {
    "image/jpeg": (".jpg", lambda data: data.startswith(b"\xff\xd8\xff")),
    "image/png": (".png", lambda data: data.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/gif": (".gif", lambda data: data.startswith((b"GIF87a", b"GIF89a"))),
    "image/webp": (
        ".webp",
        lambda data: len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP",
    ),
}


@router.post("/images", status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict[str, str]:
    image_format = IMAGE_FORMATS.get(file.content_type or "")
    if image_format is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a JPEG, PNG, GIF, or WebP image",
        )

    image_data = await file.read(MAX_IMAGE_SIZE + 1)
    if not image_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded image is empty",
        )
    if len(image_data) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Images must be 5 MB or smaller",
        )

    extension, is_valid_image = image_format
    if not is_valid_image(image_data):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="The uploaded file does not match its image type",
        )

    filename = f"{uuid4().hex}{extension}"
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    try:
        (settings.UPLOAD_DIR / filename).write_bytes(image_data)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The image could not be saved",
        ) from exc

    return {"image_url": f"/uploads/{filename}"}
