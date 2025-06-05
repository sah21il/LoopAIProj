import threading
import time
import heapq
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass, field
from .models import Batch, BatchStatus, Priority, IngestionRequest
import logging

logger = logging.getLogger(__name__)

@dataclass
class QueueItem:
    priority_value: int  # Lower value = higher priority
    created_time: float
    batch_id: str
    ids: List[int]
    ingestion_id: str
    
    def __lt__(self, other):
        # First sort by priority (lower value = higher priority)
        if self.priority_value != other.priority_value:
            return self.priority_value < other.priority_value
        # Then by creation time (earlier = higher priority)
        return self.created_time < other.created_time

class BatchProcessor:
    def __init__(self):
        self.queue = []
        self.lock = threading.Lock()
        self.last_processed_time = 0
        self.rate_limit_seconds = 5
        self.processing = False
        self.worker_thread = None
        
    def get_priority_value(self, priority: str) -> int:
        """Convert priority enum to numeric value for sorting"""
        priority_map = {
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3
        }
        return priority_map.get(priority, 3)
    
    def add_batches(self, ingestion_id: str, ids: List[int], priority: str, created_time: float):
        """Add batches to the processing queue"""
        with self.lock:
            # Split IDs into batches of 3
            batch_size = 3
            priority_value = self.get_priority_value(priority)
            
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i + batch_size]
                
                # Create batch in database
                ingestion_request = IngestionRequest.objects.get(ingestion_id=ingestion_id)
                batch = Batch.objects.create(
                    ingestion_request=ingestion_request,
                    ids=batch_ids,
                    status=BatchStatus.YET_TO_START
                )
                
                # Add to priority queue
                queue_item = QueueItem(
                    priority_value=priority_value,
                    created_time=created_time,
                    batch_id=str(batch.batch_id),
                    ids=batch_ids,
                    ingestion_id=ingestion_id
                )
                
                heapq.heappush(self.queue, queue_item)
                logger.info(f"Added batch {batch.batch_id} to queue with priority {priority}")
            
            # Start processing if not already running
            if not self.processing:
                self.start_processing()
    
    def start_processing(self):
        """Start the background worker thread"""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            self.processing = True
            self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
            self.worker_thread.start()
            logger.info("Started batch processing worker thread")
    
    def _process_queue(self):
        """Background worker that processes batches from the queue"""
        while True:
            with self.lock:
                if not self.queue:
                    self.processing = False
                    logger.info("Queue is empty, stopping processing")
                    break
                
                # Check rate limit
                current_time = time.time()
                time_since_last_process = current_time - self.last_processed_time
                
                if time_since_last_process < self.rate_limit_seconds:
                    wait_time = self.rate_limit_seconds - time_since_last_process
                else:
                    wait_time = 0
            
            # Wait outside the lock
            if wait_time > 0:
                logger.info(f"Rate limiting: waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
            
            # Process next batch
            with self.lock:
                if self.queue:
                    queue_item = heapq.heappop(self.queue)
                    self.last_processed_time = time.time()
                    
                    # Process outside the lock
                    threading.Thread(
                        target=self._process_batch,
                        args=(queue_item,),
                        daemon=True
                    ).start()
    
    def _process_batch(self, queue_item: QueueItem):
        """Process a single batch"""
        try:
            # Update batch status to triggered
            batch = Batch.objects.get(batch_id=queue_item.batch_id)
            batch.status = BatchStatus.TRIGGERED
            batch.save()
            
            logger.info(f"Processing batch {queue_item.batch_id} with IDs {queue_item.ids}")
            
            # Simulate external API processing
            processed_data = []
            for id_val in queue_item.ids:
                # Simulate API call delay
                time.sleep(0.1)  # Small delay to simulate processing
                processed_data.append({
                    "id": id_val,
                    "data": "processed"
                })
            
            # Update batch status to completed
            batch.status = BatchStatus.COMPLETED
            batch.save()
            
            logger.info(f"Completed processing batch {queue_item.batch_id}")
            
        except Exception as e:
            logger.error(f"Error processing batch {queue_item.batch_id}: {str(e)}")
            # Update batch status to completed even on error for now
            try:
                batch = Batch.objects.get(batch_id=queue_item.batch_id)
                batch.status = BatchStatus.COMPLETED
                batch.save()
            except:
                pass

# Global instance
batch_processor = BatchProcessor()