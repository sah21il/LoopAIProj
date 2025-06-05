from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
import uuid
import logging

from .models import IngestionRequest, Batch
from .serializers import (
    IngestionRequestSerializer, 
    IngestionResponseSerializer,
    StatusResponseSerializer,
    BatchSerializer
)
from .tasks import batch_processor

logger = logging.getLogger(__name__)

@api_view(['POST'])
def ingest(request):
    """
    POST /ingest
    Submit a data ingestion request
    """
    try:
        serializer = IngestionRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = serializer.validated_data
        ids = validated_data['ids']
        priority = validated_data['priority']

        # ✅ Use atomic transaction to prevent race conditions
        with transaction.atomic():
            ingestion_request = IngestionRequest.objects.create(
                priority=priority
            )
            ingestion_id = ingestion_request.ingestion_id

        # Add batches to processor queue (outside transaction if it's async)
        created_time = timezone.now().timestamp()
        batch_processor.add_batches(ingestion_id, ids, priority, created_time)
        
        logger.info(f"Created ingestion request {ingestion_id} with {len(ids)} IDs and priority {priority}")
        
        # Return response
        response_data = {'ingestion_id': ingestion_id}
        response_serializer = IngestionResponseSerializer(response_data)
        
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error in ingest endpoint: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def get_status(request, ingestion_id):
    """
    GET /status/<ingestion_id>
    Get the status of an ingestion request
    """
    try:
        # Use select_related to avoid N+1 queries and ensure data consistency
        ingestion_request = get_object_or_404(
            IngestionRequest.objects.select_related(), 
            ingestion_id=ingestion_id
        )
        
        # Use select_for_update to prevent race conditions during status reading
        with transaction.atomic():
            batches = Batch.objects.filter(
                ingestion_request=ingestion_request
            ).select_for_update()
            
            batch_serializer = BatchSerializer(batches, many=True)
            
            # Calculate status within transaction to ensure consistency
            if not batches:
                current_status = 'yet_to_start'
            else:
                statuses = [batch.status for batch in batches]
                if all(status == 'completed' for status in statuses):
                    current_status = 'completed'
                elif any(status == 'triggered' for status in statuses):
                    current_status = 'triggered'
                else:
                    current_status = 'yet_to_start'

            response_data = {
                'ingestion_id': ingestion_id,
                'status': current_status,
                'batches': batch_serializer.data
            }

        response_serializer = StatusResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in status endpoint: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def health_check(request):
    """Health check endpoint"""
    return Response({'status': 'healthy'}, status=status.HTTP_200_OK)