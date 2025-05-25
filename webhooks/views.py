import logging
from django.http import HttpResponse, JsonResponse
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import WebhookEvent, SMSLog
from .serializers import (
    TribePayWebhookSerializer, 
    WebhookEventSerializer, 
    SMSLogSerializer
)
from .tasks import schedule_sms_recovery

logger = logging.getLogger('webhooks')


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def tribopay_webhook(request):
    """
    Endpoint para receber webhooks da TriboPay
    """
    try:
        logger.info(f"Webhook recebido: {request.data}")
        
        # Validar dados do webhook
        serializer = TribePayWebhookSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Dados inválidos no webhook: {serializer.errors}")
            return Response(
                {'error': 'Dados inválidos', 'details': serializer.errors}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Converter para formato do modelo
        webhook_data = serializer.to_webhook_event_data()
        
        # Verificar se já foi processado (evitar duplicatas)
        webhook_event, created = WebhookEvent.objects.get_or_create(
            defaults=webhook_data,
            **{k: v for k, v in webhook_data.items() 
               if k in ['payment_id', 'customer_phone', 'payment_method']}
        )
        
        if created:
            logger.info(f"Novo webhook criado: {webhook_event}")
            
            # Se for PIX aguardando pagamento, agendar SMS de recuperação
            if webhook_event.is_pix_waiting_payment():
                logger.info(f"Agendando SMS de recuperação para webhook {webhook_event.id}")
                schedule_sms_recovery.apply_async(
                    args=[webhook_event.id],
                    countdown=600  # 10 minutos em segundos
                )
                webhook_event.sms_scheduled = True
                webhook_event.save()
        else:
            logger.info(f"Webhook duplicado ignorado: {webhook_event}")
        
        # Marcar como processado
        webhook_event.processed = True
        webhook_event.save()
        
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erro ao processar webhook: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Erro interno do servidor'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class WebhookEventListView(generics.ListAPIView):
    """Lista todos os eventos de webhook recebidos"""
    
    queryset = WebhookEvent.objects.all()
    serializer_class = WebhookEventSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros opcionais
        payment_method = self.request.query_params.get('payment_method')
        payment_status = self.request.query_params.get('payment_status')
        processed = self.request.query_params.get('processed')
        
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        if processed is not None:
            queryset = queryset.filter(processed=processed.lower() == 'true')
        
        return queryset


class WebhookEventDetailView(generics.RetrieveAPIView):
    """Detalhes de um evento de webhook específico"""
    
    queryset = WebhookEvent.objects.all()
    serializer_class = WebhookEventSerializer


class SMSLogListView(generics.ListAPIView):
    """Lista todos os logs de SMS enviados"""
    
    queryset = SMSLog.objects.all()
    serializer_class = SMSLogSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros opcionais
        status_filter = self.request.query_params.get('status')
        webhook_event_id = self.request.query_params.get('webhook_event')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if webhook_event_id:
            queryset = queryset.filter(webhook_event_id=webhook_event_id)
        
        return queryset


class SMSLogDetailView(generics.RetrieveAPIView):
    """Detalhes de um log de SMS específico"""
    
    queryset = SMSLog.objects.all()
    serializer_class = SMSLogSerializer


@csrf_exempt
@api_view(['POST'])
def test_sms(request):
    """
    Endpoint para testar envio de SMS
    """
    try:
        phone_number = request.data.get('phone_number')
        message = request.data.get('message', 'Teste de SMS')
        
        if not phone_number:
            return Response(
                {'error': 'phone_number é obrigatório'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Importar aqui para evitar circular import
        from sms_service.sms import TwilioSMSService
        
        sms_service = TwilioSMSService()
        
        # Validar número
        if not sms_service.validate_phone_number(phone_number):
            return Response(
                {'error': 'Número de telefone inválido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Enviar SMS
        success, message_sid, error = sms_service.send_custom_sms(phone_number, message)
        
        if success:
            return Response({
                'status': 'success',
                'message_sid': message_sid,
                'phone_number': phone_number
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'status': 'error',
                'error': error,
                'phone_number': phone_number
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Erro ao testar SMS: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Erro interno do servidor'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class TribopayWebhookView(generics.GenericAPIView):
    """
    View baseada em classe para receber webhooks da TriboPay
    """
    serializer_class = TribePayWebhookSerializer
    permission_classes = [AllowAny]
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        """
        Processa webhook da TriboPay
        """
        try:
            logger.info(f"Webhook recebido: {request.data}")
            
            # Validar dados do webhook
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                logger.error(f"Dados inválidos no webhook: {serializer.errors}")
                return Response(
                    {'error': 'Dados inválidos', 'details': serializer.errors}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Converter para formato do modelo
            webhook_data = serializer.to_webhook_event_data()
            
            # Verificar se já foi processado (evitar duplicatas)
            webhook_event, created = WebhookEvent.objects.get_or_create(
                defaults=webhook_data,
                **{k: v for k, v in webhook_data.items() 
                   if k in ['payment_id', 'customer_phone', 'payment_method']}
            )
            
            if created:
                logger.info(f"Novo webhook criado: {webhook_event}")
                
                # Se for PIX aguardando pagamento, agendar SMS de recuperação
                if webhook_event.is_pix_waiting_payment():
                    logger.info(f"Agendando SMS de recuperação para webhook {webhook_event.id}")
                    schedule_sms_recovery.apply_async(
                        args=[webhook_event.id],
                        countdown=600  # 10 minutos em segundos
                    )
                    webhook_event.sms_scheduled = True
                    webhook_event.save()
            else:
                logger.info(f"Webhook duplicado ignorado: {webhook_event}")
            
            # Marcar como processado
            webhook_event.processed = True
            webhook_event.save()
            
            return Response({'status': 'ok'}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erro ao processar webhook: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Erro interno do servidor'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TestSMSView(generics.GenericAPIView):
    """
    View para testar envio de SMS
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Testa envio de SMS
        """
        try:
            phone_number = request.data.get('phone_number')
            message = request.data.get('message', 'Teste de SMS do sistema de recuperação')
            
            if not phone_number:
                return Response(
                    {'error': 'phone_number é obrigatório'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Importar aqui para evitar circular import
            from sms_service.sms import TwilioSMSService
            
            sms_service = TwilioSMSService()
            
            # Validar número
            if not sms_service.validate_phone_number(phone_number):
                return Response(
                    {'error': 'Número de telefone inválido'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Enviar SMS
            success, message_sid, error = sms_service.send_custom_sms(phone_number, message)
            
            if success:
                return Response({
                    'status': 'success',
                    'message_sid': message_sid,
                    'phone_number': phone_number,
                    'message': message
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'status': 'error',
                    'error': error,
                    'phone_number': phone_number
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Erro ao testar SMS: {str(e)}", exc_info=True)
            return Response(
                {'error': 'Erro interno do servidor'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Endpoint de health check para monitoramento
    """
    try:
        # Verificar conexão com banco
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Verificar Redis/Celery
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)
        
        return JsonResponse({
            'status': 'healthy',
            'service': 'SMS Sender',
            'database': 'connected',
            'cache': 'connected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)
