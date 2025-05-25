from django.urls import path
from . import views

app_name = 'webhooks'

urlpatterns = [
    # Health check endpoint
    path('health/', views.health_check, name='health-check'),
    
    # Debug endpoint
    path('debug/', views.debug_db, name='debug-db'),
    
    # TriboPay raw debug endpoint
    path('tribopay-debug/', views.tribopay_raw_debug, name='tribopay-debug'),
    
    # TriboPay flexible endpoint
    path('tribopay-flex/', views.tribopay_flexible, name='tribopay-flexible'),
    
    # Force migrate endpoint
    path('force-migrate/', views.force_migrate, name='force-migrate'),
    
    # Endpoint principal para receber webhooks da TriboPay
    path('tribopay/', views.TribopayWebhookView.as_view(), name='tribopay-webhook'),
    
    # Endpoints para monitoramento e auditoria
    path('events/', views.WebhookEventListView.as_view(), name='webhook-events'),
    path('events/<int:pk>/', views.WebhookEventDetailView.as_view(), name='webhook-event-detail'),
    path('sms-logs/', views.SMSLogListView.as_view(), name='sms-logs'),
    path('sms-logs/<int:pk>/', views.SMSLogDetailView.as_view(), name='sms-log-detail'),
    
    # Endpoint para testar envio de SMS
    path('test-sms/', views.TestSMSView.as_view(), name='test-sms'),
    
    # TriboPay test format endpoint (no database)
    path('tribopay-test/', views.tribopay_test_format, name='tribopay-test'),
]
