"""
SeaweedFS Storage Implementation

Supports Filer API (primary) and S3 API (fallback).
"""

import logging
from pathlib import Path
from typing import AsyncIterator, List, Optional

import aiohttp

from dockingvina.config import storage as storage_config

logger = logging.getLogger(__name__)


class SeaweedStorage:
    """SeaweedFS Filer API storage implementation."""
    
    def __init__(self):
        self.filer_endpoint = storage_config.filer_endpoint
        self.bucket = storage_config.bucket
        self.base_url = storage_config.get_filer_base_url()
        
        logger.info(
            "SeaweedStorage initialized: filer=%s, bucket=%s",
            self.filer_endpoint, self.bucket
        )
    
    def _get_url(self, remote_key: str) -> str:
        """Build full Filer URL."""
        key = remote_key.lstrip('/')
        return f"{self.base_url}/{key}"
    
    async def upload_file(self, local_path: Path, remote_key: str) -> str:
        """
        Upload local file to SeaweedFS.
        
        Args:
            local_path: Local file path
            remote_key: Remote storage path (without bucket)
            
        Returns:
            Stored remote_key
        """
        url = self._get_url(remote_key)
        
        async with aiohttp.ClientSession() as session:
            with open(local_path, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('file', f, filename=local_path.name)
                async with session.post(url, data=data) as response:
                    if response.status not in (200, 201):
                        text = await response.text()
                        raise Exception(f"Upload failed: {response.status} - {text}")
        
        logger.info("Uploaded file: %s -> %s", local_path, remote_key)
        return remote_key
    
    async def upload_bytes(
        self,
        data: bytes,
        remote_key: str,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload bytes to SeaweedFS.
        
        Args:
            data: Bytes to upload
            remote_key: Remote storage path
            content_type: Optional MIME type
            
        Returns:
            Stored remote_key
        """
        url = self._get_url(remote_key)
        
        async with aiohttp.ClientSession() as session:
            form_data = aiohttp.FormData()
            form_data.add_field(
                'file', data,
                filename=remote_key.split('/')[-1],
                content_type=content_type or 'application/octet-stream'
            )
            async with session.post(url, data=form_data) as response:
                if response.status not in (200, 201):
                    text = await response.text()
                    raise Exception(f"Upload failed: {response.status} - {text}")
        
        logger.info("Uploaded bytes: %d bytes -> %s", len(data), remote_key)
        return remote_key
    
    async def download_file(self, remote_key: str, local_path: Path) -> Path:
        """
        Download file from SeaweedFS to local path.
        
        Args:
            remote_key: Remote storage path
            local_path: Local save path
            
        Returns:
            Local file path
        """
        url = self._get_url(remote_key)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 404:
                    raise FileNotFoundError(f"File not found: {remote_key}")
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Download failed: {response.status} - {text}")
                
                with open(local_path, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
        
        logger.info("Downloaded file: %s -> %s", remote_key, local_path)
        return local_path
    
    async def download_bytes(self, remote_key: str) -> bytes:
        """
        Download file content as bytes.
        
        Args:
            remote_key: Remote storage path
            
        Returns:
            File content as bytes
        """
        url = self._get_url(remote_key)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 404:
                    raise FileNotFoundError(f"File not found: {remote_key}")
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Download failed: {response.status} - {text}")
                
                data = await response.read()
        
        logger.debug("Downloaded bytes: %s (%d bytes)", remote_key, len(data))
        return data
    
    async def get_presigned_url(
        self,
        remote_key: str,
        expires: Optional[int] = None
    ) -> str:
        """
        Generate direct download URL.
        
        Note: Filer doesn't require signing, returns direct URL.
        
        Args:
            remote_key: Remote storage path
            expires: URL expiration (seconds), ignored for Filer
            
        Returns:
            Download URL
        """
        url = self._get_url(remote_key)
        logger.debug("Generated download URL for %s", remote_key)
        return url
    
    async def delete_file(self, remote_key: str) -> bool:
        """
        Delete file from SeaweedFS.
        
        Args:
            remote_key: Remote storage path
            
        Returns:
            Whether deletion was successful
        """
        url = self._get_url(remote_key)
        
        async with aiohttp.ClientSession() as session:
            async with session.delete(url) as response:
                if response.status not in (200, 202, 204, 404):
                    text = await response.text()
                    raise Exception(f"Delete failed: {response.status} - {text}")
        
        logger.info("Deleted file: %s", remote_key)
        return True
    
    async def delete_files(self, remote_keys: List[str]) -> bool:
        """
        Batch delete files from SeaweedFS.
        
        Args:
            remote_keys: List of remote storage paths
            
        Returns:
            Whether deletion was successful
        """
        for key in remote_keys:
            await self.delete_file(key)
        
        logger.info("Deleted %d files", len(remote_keys))
        return True
    
    async def list_files(self, prefix: str) -> List[str]:
        """
        List files with given prefix.
        
        Args:
            prefix: Path prefix
            
        Returns:
            List of file paths
        """
        url = self._get_url(prefix.rstrip('/') + '/')
        params = {'pretty': 'y'}
        
        result = []
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, params=params,
                headers={'Accept': 'application/json'}
            ) as response:
                if response.status == 404:
                    return []
                if response.status != 200:
                    return []
                
                try:
                    data = await response.json()
                    entries = data.get('Entries', []) or []
                    for entry in entries:
                        name = entry.get('FullPath', '') or entry.get('Name', '')
                        if name:
                            if name.startswith('/buckets/' + self.bucket + '/'):
                                name = name[len('/buckets/' + self.bucket + '/'):]
                            result.append(name)
                except Exception:
                    pass
        
        logger.debug("Listed %d files with prefix: %s", len(result), prefix)
        return result
    
    async def file_exists(self, remote_key: str) -> bool:
        """
        Check if file exists.
        
        Args:
            remote_key: Remote storage path
            
        Returns:
            Whether file exists
        """
        url = self._get_url(remote_key)
        
        async with aiohttp.ClientSession() as session:
            async with session.head(url) as response:
                return response.status == 200
    
    async def copy_file(self, src_key: str, dest_key: str) -> str:
        """
        Copy file (via download and re-upload).
        
        Args:
            src_key: Source file path
            dest_key: Destination file path
            
        Returns:
            Destination file path
        """
        data = await self.download_bytes(src_key)
        await self.upload_bytes(data, dest_key)
        
        logger.info("Copied file: %s -> %s", src_key, dest_key)
        return dest_key
    
    async def get_file_stream(
        self,
        remote_key: str,
        chunk_size: int = 8192
    ) -> AsyncIterator[bytes]:
        """
        Get file stream for streaming download.
        
        Args:
            remote_key: Remote storage path
            chunk_size: Chunk size in bytes
            
        Yields:
            File content chunks
        """
        url = self._get_url(remote_key)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 404:
                    raise FileNotFoundError(f"File not found: {remote_key}")
                if response.status != 200:
                    text = await response.text()
                    raise Exception(f"Download failed: {response.status} - {text}")
                
                async for chunk in response.content.iter_chunked(chunk_size):
                    yield chunk
    
    async def get_file_info(self, remote_key: str) -> Optional[dict]:
        """
        Get file metadata.
        
        Args:
            remote_key: Remote storage path
            
        Returns:
            File info dict with size, content_type, last_modified, etc.
        """
        url = self._get_url(remote_key)
        
        async with aiohttp.ClientSession() as session:
            async with session.head(url) as response:
                if response.status != 200:
                    return None
                
                return {
                    'size': int(response.headers.get('Content-Length', 0)),
                    'content_type': response.headers.get('Content-Type'),
                    'last_modified': response.headers.get('Last-Modified'),
                    'etag': response.headers.get('ETag'),
                }
    
    async def upload_directory(self, local_dir: Path, remote_prefix: str) -> List[str]:
        """
        Upload entire directory.
        
        Args:
            local_dir: Local directory path
            remote_prefix: Remote path prefix
            
        Returns:
            List of uploaded file paths
        """
        uploaded = []
        for file_path in local_dir.rglob('*'):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_dir)
                remote_key = f"{remote_prefix}/{relative_path}".replace('\\', '/')
                await self.upload_file(file_path, remote_key)
                uploaded.append(remote_key)
        
        logger.info(
            "Uploaded directory %s -> %s (%d files)",
            local_dir, remote_prefix, len(uploaded)
        )
        return uploaded
    
    async def download_directory(self, remote_prefix: str, local_dir: Path) -> List[Path]:
        """
        Download entire directory.
        
        Args:
            remote_prefix: Remote path prefix
            local_dir: Local directory path
            
        Returns:
            List of downloaded local file paths
        """
        files = await self.list_files(remote_prefix)
        downloaded = []
        
        for remote_key in files:
            relative_path = remote_key[len(remote_prefix):].lstrip('/')
            local_path = local_dir / relative_path
            await self.download_file(remote_key, local_path)
            downloaded.append(local_path)
        
        logger.info(
            "Downloaded directory %s -> %s (%d files)",
            remote_prefix, local_dir, len(downloaded)
        )
        return downloaded
    
    async def ensure_bucket_exists(self) -> bool:
        """Ensure bucket directory exists."""
        url = f"{self.filer_endpoint}/buckets/{self.bucket}/"
        
        async with aiohttp.ClientSession() as session:
            async with session.head(url) as response:
                if response.status == 200:
                    return True
            
            async with session.post(url) as response:
                return response.status in (200, 201)
        
        return False
