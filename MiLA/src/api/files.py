"""
File serving API endpoints for generated PDFs.
"""
import logging
import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse

from ..components.pdf_generator import pdf_generator

logger = logging.getLogger(__name__)

# Create router for file endpoints
router = APIRouter(prefix="/api", tags=["files"])


@router.get("/files/{filename}")
async def serve_file(filename: str):
    """
    Serve generated PDF files for download.
    
    Provides secure file serving for generated PDFs with proper content types
    and security restrictions to prevent directory traversal attacks.
    
    Args:
        filename: Name of the file to serve (must be in output directory)
        
    Returns:
        FileResponse with the requested PDF file
        
    Raises:
        HTTPException: If file not found, invalid filename, or security violation
    """
    logger.info(f"File download request: {filename}")
    
    try:
        # Security check: ensure filename doesn't contain path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            logger.warning(f"Security violation: Invalid filename attempted: {filename}")
            raise HTTPException(
                status_code=400,
                detail="Invalid filename. Path traversal attempts are not allowed."
            )
        
        # Security check: ensure filename has proper extension
        if not filename.lower().endswith('.pdf'):
            logger.warning(f"Invalid file type requested: {filename}")
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed for download."
            )
        
        # Get file path from PDF generator
        file_path = pdf_generator.get_file_path(filename)
        
        if file_path is None or not file_path.exists():
            logger.info(f"File not found: {filename}")
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {filename}"
            )
        
        # Check if file is a regular file (not a directory or special file)
        if not file_path.is_file():
            logger.warning(f"Invalid file type: {filename}")
            raise HTTPException(
                status_code=400,
                detail="Invalid file type."
            )
        
        # Get file size for logging
        file_size = file_path.stat().st_size
        logger.info(f"Serving file: {filename} ({file_size} bytes)")
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/pdf"
        
        # Create filename for download (clean version)
        download_filename = filename
        
        # Return file response with proper headers
        return FileResponse(
            path=str(file_path),
            media_type=content_type,
            filename=download_filename,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error serving file {filename}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while serving file"
        )


@router.get("/files/{filename}/info")
async def get_file_info(filename: str):
    """
    Get information about a generated PDF file.
    
    Returns metadata about the file without serving the actual content.
    Useful for checking if a file exists and getting basic information.
    
    Args:
        filename: Name of the file to get information about
        
    Returns:
        Dictionary with file information
        
    Raises:
        HTTPException: If file not found or invalid filename
    """
    logger.info(f"File info request: {filename}")
    
    try:
        # Security check: ensure filename doesn't contain path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            logger.warning(f"Security violation: Invalid filename attempted: {filename}")
            raise HTTPException(
                status_code=400,
                detail="Invalid filename. Path traversal attempts are not allowed."
            )
        
        # Security check: ensure filename has proper extension
        if not filename.lower().endswith('.pdf'):
            logger.warning(f"Invalid file type requested: {filename}")
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed."
            )
        
        # Get file path from PDF generator
        file_path = pdf_generator.get_file_path(filename)
        
        if file_path is None or not file_path.exists():
            logger.info(f"File not found: {filename}")
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {filename}"
            )
        
        # Get file statistics
        stat = file_path.stat()
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/pdf"
        
        file_info = {
            "filename": filename,
            "size": stat.st_size,
            "content_type": content_type,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "download_url": f"/api/files/{filename}"
        }
        
        logger.info(f"File info retrieved: {filename} ({stat.st_size} bytes)")
        
        return {
            "success": True,
            "file_info": file_info
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error getting file info for {filename}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while getting file information"
        )


@router.get("/files")
async def list_files():
    """
    List all available PDF files in the output directory.
    
    Returns a list of all PDF files available for download.
    This can be useful for debugging or administrative purposes.
    
    Returns:
        Dictionary with list of available files and their basic information
    """
    logger.info("File list request")
    
    try:
        files = []
        output_dir = pdf_generator.output_directory
        
        # List all PDF files in the output directory
        for pdf_file in output_dir.glob("*.pdf"):
            if pdf_file.is_file():
                stat = pdf_file.stat()
                files.append({
                    "filename": pdf_file.name,
                    "size": stat.st_size,
                    "created": stat.st_ctime,
                    "modified": stat.st_mtime,
                    "download_url": f"/api/files/{pdf_file.name}"
                })
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        logger.info(f"File list retrieved: {len(files)} files")
        
        return {
            "success": True,
            "file_count": len(files),
            "files": files
        }
        
    except Exception as e:
        logger.error(f"Unexpected error listing files: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while listing files"
        )


@router.delete("/files/{filename}")
async def delete_file(filename: str):
    """
    Delete a specific PDF file.
    
    Allows manual deletion of generated PDF files.
    Should be used carefully as deleted files cannot be recovered.
    
    Args:
        filename: Name of the file to delete
        
    Returns:
        Success confirmation
        
    Raises:
        HTTPException: If file not found, invalid filename, or deletion fails
    """
    logger.info(f"File deletion request: {filename}")
    
    try:
        # Security check: ensure filename doesn't contain path traversal attempts
        if '..' in filename or '/' in filename or '\\' in filename:
            logger.warning(f"Security violation: Invalid filename attempted: {filename}")
            raise HTTPException(
                status_code=400,
                detail="Invalid filename. Path traversal attempts are not allowed."
            )
        
        # Security check: ensure filename has proper extension
        if not filename.lower().endswith('.pdf'):
            logger.warning(f"Invalid file type for deletion: {filename}")
            raise HTTPException(
                status_code=400,
                detail="Only PDF files can be deleted."
            )
        
        # Get file path from PDF generator
        file_path = pdf_generator.get_file_path(filename)
        
        if file_path is None or not file_path.exists():
            logger.info(f"File not found for deletion: {filename}")
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {filename}"
            )
        
        # Delete the file
        file_path.unlink()
        
        logger.info(f"File deleted successfully: {filename}")
        
        return {
            "success": True,
            "message": f"File deleted successfully: {filename}"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
        
    except Exception as e:
        logger.error(f"Unexpected error deleting file {filename}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while deleting file"
        )


@router.post("/files/cleanup")
async def cleanup_old_files(max_age_hours: Optional[int] = 24):
    """
    Clean up old PDF files from the output directory.
    
    Deletes PDF files older than the specified age.
    This is useful for preventing storage bloat.
    
    Args:
        max_age_hours: Maximum age of files to keep in hours (default: 24)
        
    Returns:
        Information about the cleanup operation
    """
    logger.info(f"File cleanup request: max_age_hours={max_age_hours}")
    
    try:
        # Validate max_age_hours
        if max_age_hours is None or max_age_hours < 0:
            max_age_hours = 24
        
        # Limit maximum age to prevent accidental deletion of all files
        if max_age_hours > 168:  # 1 week
            max_age_hours = 168
        
        # Perform cleanup
        deleted_count = pdf_generator.cleanup_old_files(max_age_hours)
        
        logger.info(f"File cleanup completed: {deleted_count} files deleted")
        
        return {
            "success": True,
            "message": f"File cleanup completed",
            "deleted_count": deleted_count,
            "max_age_hours": max_age_hours
        }
        
    except Exception as e:
        logger.error(f"Unexpected error during file cleanup: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during file cleanup"
        )