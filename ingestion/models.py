from django.db import models
import uuid
from django.utils import timezone

def generate_uuid():
    """Generate UUID as a string"""
    return str(uuid.uuid4())

class Priority(models.TextChoices):
    HIGH = 'HIGH', 'High'
    MEDIUM = 'MEDIUM', 'Medium'
    LOW = 'LOW', 'Low'

class BatchStatus(models.TextChoices):
    YET_TO_START = 'yet_to_start', 'Yet to Start'
    TRIGGERED = 'triggered', 'Triggered'
    COMPLETED = 'completed', 'Completed'

class IngestionRequest(models.Model):
    ingestion_id = models.CharField(max_length=100, unique=True, default=generate_uuid, db_index=True)
    priority = models.CharField(max_length=10, choices=Priority.choices)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        # Add database-level constraint for better concurrency handling
        constraints = [
            models.UniqueConstraint(fields=['ingestion_id'], name='unique_ingestion_id')
        ]
    
    def __str__(self):
        return f"Ingestion {self.ingestion_id} - {self.priority}"
    
    @property
    def status(self):
        """
        Calculate status based on associated batches
        Uses select_for_update to prevent race conditions
        """
        from django.db import transaction
        
        # Use atomic transaction to ensure consistent reads
        with transaction.atomic():
            batches = self.batches.select_for_update().all()
            
            if not batches.exists():
                return 'yet_to_start'
            
            statuses = list(batches.values_list('status', flat=True))
            
            if all(status == BatchStatus.COMPLETED for status in statuses):
                return 'completed'
            elif any(status == BatchStatus.TRIGGERED for status in statuses):
                return 'triggered'
            else:
                return 'yet_to_start'

class Batch(models.Model):
    batch_id = models.CharField(max_length=100, unique=True, default=generate_uuid, db_index=True)
    ingestion_request = models.ForeignKey(IngestionRequest, related_name='batches', on_delete=models.CASCADE)
    ids = models.JSONField()  # Store list of IDs
    status = models.CharField(max_length=20, choices=BatchStatus.choices, default=BatchStatus.YET_TO_START)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        constraints = [
            models.UniqueConstraint(fields=['batch_id'], name='unique_batch_id')
        ]
    
    def __str__(self):
        return f"Batch {self.batch_id} - {self.status}"