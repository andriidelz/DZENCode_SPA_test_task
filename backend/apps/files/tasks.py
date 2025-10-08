from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_uploaded_file(file_id):
    """
    Process uploaded file asynchronously
    """
    try:
        from .models import UploadedFile
        from .services import FileUploadService
        
        file_obj = UploadedFile.objects.get(id=file_id)
        
        if file_obj.status != 'pending':
            logger.warning(f"File {file_id} is not in pending status: {file_obj.status}")
            return
        
        # Mark as processing
        file_obj.status = 'processing'
        file_obj.save()
        
        # Process file
        service = FileUploadService()
        
        if file_obj.file_type == 'image':
            service._process_image(file_obj)
        elif file_obj.file_type == 'text':
            service._process_text_file(file_obj)
        
        # Mark as completed
        file_obj.status = 'completed'
        file_obj.processed_at = timezone.now()
        file_obj.save()
        
        logger.info(f"Successfully processed file {file_id}: {file_obj.original_name}")
        
        # Clear file stats cache
        cache.delete('file_stats')
        
    except Exception as e:
        logger.error(f"Failed to process file {file_id}: {e}")
        
        # Mark as failed
        try:
            file_obj = UploadedFile.objects.get(id=file_id)
            file_obj.status = 'failed'
            file_obj.processing_error = str(e)
            file_obj.save()
        except:
            pass
        
        raise


@shared_task
def cleanup_old_files():
    """
    Periodic task to clean up old files
    """
    try:
        from .services import FileCleanupService
        
        # Clean up files older than 30 days
        deleted_count = FileCleanupService.cleanup_old_files(days=30)
        
        # Clean up failed uploads older than 1 day
        failed_deleted = FileCleanupService.cleanup_failed_uploads()
        
        logger.info(f"Cleanup completed: {deleted_count} old files, {failed_deleted} failed uploads")
        
        # Clear file stats cache
        cache.delete('file_stats')
        
        return {
            'deleted_files': deleted_count,
            'deleted_failed_uploads': failed_deleted
        }
        
    except Exception as e:
        logger.error(f"File cleanup failed: {e}")
        raise


@shared_task
def generate_file_thumbnails():
    """
    Generate missing thumbnails for image files
    """
    try:
        from .models import UploadedFile, ImageFile
        from .services import FileUploadService
        
        # Find image files without thumbnails
        image_files = ImageFile.objects.filter(
            thumbnail__isnull=True,
            uploaded_file__status='completed'
        )
        
        processed_count = 0
        service = FileUploadService()
        
        for image_file in image_files[:10]:  # Limit to 10 per run
            try:
                # Regenerate thumbnail
                service._process_image(image_file.uploaded_file)
                processed_count += 1
                logger.info(f"Generated thumbnail for {image_file.uploaded_file.original_name}")
            except Exception as e:
                logger.error(f"Failed to generate thumbnail for {image_file.id}: {e}")
        
        logger.info(f"Generated {processed_count} thumbnails")
        return processed_count
        
    except Exception as e:
        logger.error(f"Thumbnail generation failed: {e}")
        raise


@shared_task
def update_file_statistics():
    """
    Update cached file statistics
    """
    try:
        from django.db.models import Sum, Count, Avg
        from .models import UploadedFile
        
        # Calculate fresh statistics
        stats = {
            'total_files': UploadedFile.objects.filter(status='completed').count(),
            'total_size': UploadedFile.objects.filter(status='completed').aggregate(
                total=Sum('file_size')
            )['total'] or 0,
            'files_by_type': dict(
                UploadedFile.objects.filter(status='completed').values('file_type').annotate(
                    count=Count('id')
                ).values_list('file_type', 'count')
            ),
            'average_file_size': UploadedFile.objects.filter(status='completed').aggregate(
                avg=Avg('file_size')
            )['avg'] or 0
        }
        
        # Cache for 10 minutes
        cache.set('file_stats', stats, 60 * 10)
        
        logger.info("Updated file statistics cache")
        return stats
        
    except Exception as e:
        logger.error(f"Failed to update file statistics: {e}")
        raise


@shared_task
def optimize_images():
    """
    Optimize image files to reduce storage usage
    """
    try:
        from .models import UploadedFile, ImageFile
        from PIL import Image
        import os
        
        # Find large image files that could be optimized
        large_images = ImageFile.objects.filter(
            uploaded_file__status='completed',
            uploaded_file__file_size__gt=1024*1024,  # Larger than 1MB
            quality__gt=85  # High quality images
        )[:5]  # Limit to 5 per run
        
        optimized_count = 0
        total_saved = 0
        
        for image_file in large_images:
            try:
                old_size = image_file.uploaded_file.file_size
                
                # Optimize image
                with Image.open(image_file.uploaded_file.file.path) as img:
                    # Reduce quality slightly
                    new_quality = max(75, image_file.quality - 10)
                    
                    # Save optimized version
                    img.save(
                        image_file.uploaded_file.file.path,
                        format=image_file.format,
                        quality=new_quality,
                        optimize=True
                    )
                    
                    # Update file size
                    new_size = os.path.getsize(image_file.uploaded_file.file.path)
                    
                    if new_size < old_size:
                        image_file.uploaded_file.file_size = new_size
                        image_file.uploaded_file.save()
                        
                        image_file.quality = new_quality
                        image_file.save()
                        
                        saved_bytes = old_size - new_size
                        total_saved += saved_bytes
                        optimized_count += 1
                        
                        logger.info(
                            f"Optimized {image_file.uploaded_file.original_name}: "
                            f"saved {saved_bytes} bytes"
                        )
            
            except Exception as e:
                logger.error(f"Failed to optimize image {image_file.id}: {e}")
        
        logger.info(f"Optimized {optimized_count} images, saved {total_saved} bytes total")
        
        # Clear file stats cache
        cache.delete('file_stats')
        
        return {
            'optimized_count': optimized_count,
            'bytes_saved': total_saved
        }
        
    except Exception as e:
        logger.error(f"Image optimization failed: {e}")
        raise


@shared_task
def check_file_integrity():
    """
    Check integrity of stored files
    """
    try:
        from .models import UploadedFile
        import os
        import hashlib
        
        # Check random sample of files
        files_to_check = UploadedFile.objects.filter(
            status='completed'
        ).order_by('?')[:20]  # Random 20 files
        
        corrupted_files = []
        missing_files = []
        
        for file_obj in files_to_check:
            try:
                # Check if file exists
                if not os.path.exists(file_obj.file.path):
                    missing_files.append(file_obj.id)
                    logger.warning(f"Missing file: {file_obj.original_name} (ID: {file_obj.id})")
                    continue
                
                # Check file integrity by comparing checksums
                if file_obj.checksum:
                    with open(file_obj.file.path, 'rb') as f:
                        content = f.read()
                        current_checksum = hashlib.md5(content).hexdigest()
                        
                        if current_checksum != file_obj.checksum:
                            corrupted_files.append(file_obj.id)
                            logger.warning(
                                f"Corrupted file: {file_obj.original_name} (ID: {file_obj.id})"
                            )
            
            except Exception as e:
                logger.error(f"Error checking file {file_obj.id}: {e}")
        
        result = {
            'files_checked': len(files_to_check),
            'missing_files': len(missing_files),
            'corrupted_files': len(corrupted_files),
            'missing_file_ids': missing_files,
            'corrupted_file_ids': corrupted_files
        }
        
        logger.info(
            f"File integrity check completed: {len(files_to_check)} files checked, "
            f"{len(missing_files)} missing, {len(corrupted_files)} corrupted"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"File integrity check failed: {e}")
        raise
