from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
from PIL import Image, ImageOps
from io import BytesIO
import os
import hashlib
import mimetypes
import chardet
import json
from .models import UploadedFile, ImageFile, TextFile, FileUploadLog


class FileUploadService:
    """
    Service for handling file uploads and processing
    """
    
    def __init__(self):
        self.max_image_width = getattr(settings, 'IMAGE_MAX_WIDTH', 320)
        self.max_image_height = getattr(settings, 'IMAGE_MAX_HEIGHT', 240)
        self.thumbnail_size = (120, 120)
        self.jpeg_quality = 85
    
    def process_upload(self, uploaded_file, request=None):
        """
        Process uploaded file and create appropriate models
        """
        # Calculate file checksum
        checksum = self._calculate_checksum(uploaded_file)
        
        # Check for duplicate files
        existing_file = UploadedFile.objects.filter(checksum=checksum).first()
        if existing_file:
            return self._handle_duplicate_file(existing_file, uploaded_file, request)
        
        # Determine file type
        mime_type, _ = mimetypes.guess_type(uploaded_file.name)
        file_type = self._determine_file_type(mime_type)
        
        # Get client IP and user agent
        ip_address = self._get_client_ip(request) if request else None
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
        
        # Create base UploadedFile record
        file_record = UploadedFile.objects.create(
            file=uploaded_file,
            original_name=uploaded_file.name,
            file_type=file_type,
            file_size=uploaded_file.size,
            mime_type=mime_type or '',
            checksum=checksum,
            uploaded_by_ip=ip_address,
            user_agent=user_agent[:500],
            status='processing'
        )
        
        try:
            # Process based on file type
            if file_type == 'image':
                self._process_image(file_record)
            elif file_type == 'text':
                self._process_text_file(file_record)
            
            # Mark as completed
            file_record.status = 'completed'
            file_record.processed_at = timezone.now()
            file_record.save()
            
            self._log(file_record, 'info', f'File processed successfully: {uploaded_file.name}')
            
            return self._serialize_file_result(file_record)
        
        except Exception as e:
            # Mark as failed
            file_record.status = 'failed'
            file_record.processing_error = str(e)
            file_record.save()
            
            self._log(file_record, 'error', f'File processing failed: {str(e)}')
            raise
    
    def _process_image(self, file_record):
        """
        Process image file - resize, generate thumbnail, extract metadata
        """
        try:
            # Open image
            with Image.open(file_record.file.path) as img:
                # Store original dimensions
                original_width, original_height = img.size
                original_format = img.format
                
                # Analyze image
                has_transparency = img.mode in ('RGBA', 'LA', 'P')
                color_mode = img.mode
                
                # Extract EXIF data (if available)
                exif_data = {}
                if hasattr(img, '_getexif') and img._getexif():
                    exif_data = dict(img._getexif())
                
                # Resize image if needed
                if img.width > self.max_image_width or img.height > self.max_image_height:
                    # Calculate new dimensions maintaining aspect ratio
                    img.thumbnail((self.max_image_width, self.max_image_height), Image.Resampling.LANCZOS)
                    
                    # Save resized image
                    if img.mode == 'RGBA' and original_format != 'PNG':
                        # Convert RGBA to RGB for JPEG
                        img = img.convert('RGB')
                    
                    img.save(file_record.file.path, format=original_format, quality=self.jpeg_quality, optimize=True)
                
                # Generate thumbnail
                thumbnail_img = img.copy()
                thumbnail_img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
                
                # Save thumbnail
                thumbnail_io = BytesIO()
                thumbnail_format = 'PNG' if has_transparency else 'JPEG'
                thumbnail_img.save(thumbnail_io, format=thumbnail_format, quality=self.jpeg_quality)
                
                # Create thumbnail filename
                base_name = os.path.splitext(file_record.original_name)[0]
                thumbnail_name = f"{base_name}_thumb.{thumbnail_format.lower()}"
                thumbnail_path = f"thumbnails/{timezone.now().strftime('%Y/%m/%d')}/{thumbnail_name}"
                
                # Save thumbnail to storage
                thumbnail_file = default_storage.save(thumbnail_path, BytesIO(thumbnail_io.getvalue()))
                
                # Create ImageFile record
                ImageFile.objects.create(
                    uploaded_file=file_record,
                    original_width=original_width,
                    original_height=original_height,
                    width=img.width,
                    height=img.height,
                    format=original_format,
                    quality=self.jpeg_quality,
                    thumbnail=thumbnail_file,
                    has_transparency=has_transparency,
                    color_mode=color_mode,
                    exif_data=json.dumps(exif_data, default=str)
                )
                
                self._log(file_record, 'info', f'Image processed: {img.width}x{img.height}, thumbnail generated')
        
        except Exception as e:
            self._log(file_record, 'error', f'Image processing failed: {str(e)}')
            raise
    
    def _process_text_file(self, file_record):
        """
        Process text file - analyze content, generate preview
        """
        try:
            # Read file content
            with open(file_record.file.path, 'rb') as f:
                raw_content = f.read()
            
            # Detect encoding
            encoding_result = chardet.detect(raw_content)
            encoding = encoding_result.get('encoding', 'utf-8')
            confidence = encoding_result.get('confidence', 0)
            
            # Try to decode content
            try:
                content = raw_content.decode(encoding)
                is_valid_utf8 = True
                has_binary_content = False
            except UnicodeDecodeError:
                # Fallback to utf-8 with error handling
                try:
                    content = raw_content.decode('utf-8', errors='ignore')
                    is_valid_utf8 = False
                    has_binary_content = True
                except:
                    content = str(raw_content)[:1000]  # Fallback
                    is_valid_utf8 = False
                    has_binary_content = True
            
            # Analyze content
            lines = content.split('\n')
            line_count = len(lines)
            word_count = len(content.split())
            character_count = len(content)
            
            # Generate preview (first 1000 characters)
            preview = content[:1000]
            if len(content) > 1000:
                preview += '...'
            
            # Create TextFile record
            TextFile.objects.create(
                uploaded_file=file_record,
                encoding=encoding,
                line_count=line_count,
                word_count=word_count,
                character_count=character_count,
                preview=preview,
                is_valid_utf8=is_valid_utf8,
                has_binary_content=has_binary_content
            )
            
            self._log(file_record, 'info', f'Text file processed: {line_count} lines, {word_count} words')
        
        except Exception as e:
            self._log(file_record, 'error', f'Text file processing failed: {str(e)}')
            raise
    
    def _calculate_checksum(self, uploaded_file):
        """
        Calculate MD5 checksum of uploaded file
        """
        hash_md5 = hashlib.md5()
        for chunk in uploaded_file.chunks():
            hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _determine_file_type(self, mime_type):
        """
        Determine file type based on MIME type
        """
        if mime_type:
            if mime_type.startswith('image/'):
                return 'image'
            elif mime_type.startswith('text/'):
                return 'text'
            elif mime_type in ['application/pdf', 'application/msword']:
                return 'document'
        
        return 'other'
    
    def _get_client_ip(self, request):
        """
        Extract client IP from request
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def _handle_duplicate_file(self, existing_file, uploaded_file, request):
        """
        Handle duplicate file upload
        """
        self._log(
            existing_file,
            'info',
            f'Duplicate file detected: {uploaded_file.name} (original: {existing_file.original_name})'
        )
        
        return self._serialize_file_result(existing_file)
    
    def _serialize_file_result(self, file_record):
        """
        Serialize file record for API response
        """
        result = {
            'id': file_record.id,
            'original_name': file_record.original_name,
            'file_type': file_record.file_type,
            'file_size': file_record.file_size,
            'status': file_record.status,
            'created_at': file_record.created_at,
            'file_url': file_record.file.url if file_record.file else None
        }
        
        # Add type-specific data
        if file_record.file_type == 'image' and hasattr(file_record, 'image_metadata'):
            image_data = file_record.image_metadata
            result['image_data'] = {
                'width': image_data.width,
                'height': image_data.height,
                'format': image_data.format,
                'thumbnail_url': image_data.thumbnail.url if image_data.thumbnail else None
            }
        
        elif file_record.file_type == 'text' and hasattr(file_record, 'text_metadata'):
            text_data = file_record.text_metadata
            result['text_data'] = {
                'line_count': text_data.line_count,
                'word_count': text_data.word_count,
                'encoding': text_data.encoding,
                'preview': text_data.preview
            }
        
        return result
    
    def _log(self, file_record, level, message, details=''):
        """
        Log file processing events
        """
        FileUploadLog.objects.create(
            uploaded_file=file_record,
            level=level,
            message=message,
            details=details
        )


class FileCleanupService:
    """
    Service for cleaning up old files
    """
    
    @staticmethod
    def cleanup_old_files(days=30):
        """
        Clean up files older than specified days
        """
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        old_files = UploadedFile.objects.filter(created_at__lt=cutoff_date)
        
        deleted_count = 0
        for file_record in old_files:
            try:
                file_record.delete()  # This will also delete the physical file
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting file {file_record.id}: {e}")
        
        return deleted_count
    
    @staticmethod
    def cleanup_failed_uploads():
        """
        Clean up failed uploads older than 1 day
        """
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=1)
        failed_files = UploadedFile.objects.filter(
            status='failed',
            created_at__lt=cutoff_date
        )
        
        deleted_count = 0
        for file_record in failed_files:
            try:
                file_record.delete()
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting failed file {file_record.id}: {e}")
        
        return deleted_count
