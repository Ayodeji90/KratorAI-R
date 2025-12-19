"""Google Cloud Storage client for asset management."""

from google.cloud import storage
from typing import Optional
import os
import io
from PIL import Image


class GCSClient:
    """Client for interacting with Google Cloud Storage."""
    
    def __init__(self, bucket_name: Optional[str] = None):
        """Initialize GCS client."""
        self.bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME", "kratorai-assets")
        self._client: Optional[storage.Client] = None
        self._bucket: Optional[storage.Bucket] = None
    
    @property
    def client(self) -> storage.Client:
        """Lazy load GCS client."""
        if self._client is None:
            self._client = storage.Client()
        return self._client
    
    @property
    def bucket(self) -> storage.Bucket:
        """Get the configured bucket."""
        if self._bucket is None:
            self._bucket = self.client.bucket(self.bucket_name)
        return self._bucket
    
    def upload_image(
        self,
        image: Image.Image,
        destination_path: str,
        format: str = "PNG",
    ) -> str:
        """
        Upload a PIL Image to GCS.
        
        Args:
            image: PIL Image to upload
            destination_path: Path within bucket (e.g., "generated/abc123.png")
            format: Image format
        
        Returns:
            GCS URI of uploaded image
        """
        blob = self.bucket.blob(destination_path)
        
        # Convert image to bytes
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        buffer.seek(0)
        
        # Upload
        blob.upload_from_file(buffer, content_type=f"image/{format.lower()}")
        
        return f"gs://{self.bucket_name}/{destination_path}"
    
    def download_image(self, gcs_uri: str) -> Image.Image:
        """
        Download an image from GCS.
        
        Args:
            gcs_uri: GCS URI (gs://bucket/path)
        
        Returns:
            PIL Image
        """
        # Parse URI
        path = gcs_uri.replace(f"gs://{self.bucket_name}/", "")
        blob = self.bucket.blob(path)
        
        # Download to bytes
        buffer = io.BytesIO()
        blob.download_to_file(buffer)
        buffer.seek(0)
        
        return Image.open(buffer)
    
    def delete(self, gcs_uri: str) -> None:
        """Delete a file from GCS."""
        path = gcs_uri.replace(f"gs://{self.bucket_name}/", "")
        blob = self.bucket.blob(path)
        blob.delete()
    
    def generate_signed_url(
        self,
        gcs_uri: str,
        expiration_minutes: int = 60,
    ) -> str:
        """Generate a signed URL for temporary access."""
        from datetime import timedelta
        
        path = gcs_uri.replace(f"gs://{self.bucket_name}/", "")
        blob = self.bucket.blob(path)
        
        return blob.generate_signed_url(
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
        )


# Singleton
_gcs_client: Optional[GCSClient] = None


def get_gcs_client() -> GCSClient:
    """Get or create GCS client singleton."""
    global _gcs_client
    if _gcs_client is None:
        _gcs_client = GCSClient()
    return _gcs_client
