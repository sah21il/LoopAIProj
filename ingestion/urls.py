from django.urls import path
from . import views

urlpatterns = [
    path('ingest', views.ingest, name='ingest'),
    path('status/<str:ingestion_id>', views.get_status, name='get_status'),
    path('health', views.health_check, name='health_check'),
]