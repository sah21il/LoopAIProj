from rest_framework import serializers
from .models import IngestionRequest, Batch, Priority

class IngestionRequestSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=10**9+7),
        min_length=1,
        max_length=1000
    )
    priority = serializers.ChoiceField(choices=Priority.choices)
    
    def validate_ids(self, value):
        if not value:
            raise serializers.ValidationError("IDs list cannot be empty")
        return value

class IngestionResponseSerializer(serializers.Serializer):
    ingestion_id = serializers.CharField()

class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ['batch_id', 'ids', 'status']
        read_only_fields = ['batch_id', 'status']

class StatusResponseSerializer(serializers.Serializer):
    ingestion_id = serializers.CharField()
    status = serializers.CharField()
    batches = BatchSerializer(many=True)