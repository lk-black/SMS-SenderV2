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
    TribePayRealWebhookSerializer,  # Updated serializer for real TriboPay format
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
    Updated to handle real TriboPay webhook format with nested transaction and customer data
    """
    try:
        logger.info(f"Webhook recebido: {request.data}")
        
        # Validar dados do webhook com o formato real da TriboPay
        serializer = TribePayRealWebhookSerializer(data=request.data)
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
                try:
                    schedule_sms_recovery.apply_async(
                        args=[webhook_event.id],
                        countdown=600  # 10 minutos em segundos
                    )
                    webhook_event.sms_scheduled = True
                    webhook_event.save()
                    logger.info(f"SMS agendado com sucesso para webhook {webhook_event.id}")
                except Exception as e:
                    logger.warning(f"Falha ao agendar SMS (Redis não conectado): {str(e)}. Webhook salvo sem agendamento.")
                    # Continua sem marcar sms_scheduled = True
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
    serializer_class = TribePayRealWebhookSerializer
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
                    try:
                        schedule_sms_recovery.apply_async(
                            args=[webhook_event.id],
                            countdown=600  # 10 minutos em segundos
                        )
                        webhook_event.sms_scheduled = True
                        webhook_event.save()
                        logger.info(f"SMS agendado com sucesso para webhook {webhook_event.id}")
                    except Exception as e:
                        logger.warning(f"Falha ao agendar SMS (Redis não conectado): {str(e)}. Webhook salvo sem agendamento.")
                        # Continua sem marcar sms_scheduled = True
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


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def debug_db(request):
    """
    Endpoint de debug para verificar status do banco
    """
    try:
        from django.db import connection
        
        # Verificar conexão
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            
        # Verificar se tabelas existem
        tables_info = {}
        try:
            webhook_count = WebhookEvent.objects.count()
            tables_info['webhook_events'] = f"Table exists, {webhook_count} records"
        except Exception as e:
            tables_info['webhook_events'] = f"Error: {str(e)}"
            
        try:
            sms_count = SMSLog.objects.count()
            tables_info['sms_logs'] = f"Table exists, {sms_count} records"
        except Exception as e:
            tables_info['sms_logs'] = f"Error: {str(e)}"
        
        return JsonResponse({
            'status': 'debug',
            'database': 'connected',
            'tables': tables_info
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def force_migrate(request):
    """
    Endpoint para forçar execução das migrations
    """
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Capturar output das migrations
        out = StringIO()
        
        # Executar migrations
        call_command('migrate', stdout=out)
        
        migration_output = out.getvalue()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Migrations executadas com sucesso',
            'output': migration_output
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def tribopay_raw_debug(request):
    """
    Endpoint de debug para capturar exatamente o que a TriboPay está enviando
    """
    import json
    from django.http import HttpResponse
    
    try:
        # Capturar todos os dados da requisição
        debug_data = {
            'method': request.method,
            'headers': dict(request.headers),
            'content_type': request.content_type,
            'body_raw': request.body.decode('utf-8', errors='ignore'),
            'POST': dict(request.POST),
            'GET': dict(request.GET),
        }
        
        # Tentar fazer parse do JSON se possível
        if request.content_type == 'application/json' and request.body:
            try:
                debug_data['body_json'] = json.loads(request.body)
            except json.JSONDecodeError as e:
                debug_data['json_error'] = str(e)
        
        # Log the debug data
        logger.info(f"TriboPay Raw Debug: {json.dumps(debug_data, indent=2, ensure_ascii=False)}")
        
        # Retornar uma resposta simples que a TriboPay pode aceitar
        return HttpResponse('OK', status=200)
        
    except Exception as e:
        logger.error(f"Erro no debug raw: {str(e)}")
        return HttpResponse('ERROR', status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def tribopay_flexible(request):
    """
    Endpoint flexível para receber webhooks da TriboPay com diferentes formatos
    """
    import json
    
    try:
        logger.info(f"TriboPay Flexible - Headers: {dict(request.headers)}")
        logger.info(f"TriboPay Flexible - Content-Type: {request.content_type}")
        logger.info(f"TriboPay Flexible - Body: {request.body.decode('utf-8', errors='ignore')}")
        
        # Tentar extrair dados de diferentes formatos
        webhook_data = None
        
        # Formato 1: JSON direto
        if request.content_type == 'application/json' and request.body:
            try:
                webhook_data = json.loads(request.body)
                logger.info(f"Dados JSON recebidos: {webhook_data}")
            except json.JSONDecodeError:
                pass
        
        # Formato 2: Form data
        if not webhook_data and request.POST:
            webhook_data = dict(request.POST)
            logger.info(f"Dados POST recebidos: {webhook_data}")
        
        # Formato 3: Query parameters
        if not webhook_data and request.GET:
            webhook_data = dict(request.GET)
            logger.info(f"Dados GET recebidos: {webhook_data}")
        
        # Se ainda não temos dados, tentar parse manual
        if not webhook_data and request.body:
            body_str = request.body.decode('utf-8', errors='ignore')
            # Tentar diferentes formatos
            if body_str.startswith('{'):
                try:
                    webhook_data = json.loads(body_str)
                except:
                    pass
        
        if webhook_data:
            # Criar um evento webhook simplificado
            try:
                from .models import WebhookEvent
                import hashlib
                
                # Gerar hash para evitar duplicatas
                data_str = json.dumps(webhook_data, sort_keys=True)
                webhook_hash = hashlib.sha256(data_str.encode()).hexdigest()
                
                # Tentar extrair campos básicos de diferentes estruturas
                payment_id = webhook_data.get('id') or webhook_data.get('payment_id') or webhook_data.get('transaction_id')
                payment_method = webhook_data.get('payment_method') or webhook_data.get('method') or 'unknown'
                payment_status = webhook_data.get('payment_status') or webhook_data.get('status') or 'unknown'
                amount = webhook_data.get('amount') or webhook_data.get('value') or 0
                
                # Extrair dados do cliente
                customer_data = webhook_data.get('customer', {})
                if isinstance(customer_data, str):
                    try:
                        customer_data = json.loads(customer_data)
                    except:
                        customer_data = {}
                
                customer_phone = customer_data.get('phone_number') or customer_data.get('phone') or ''
                customer_name = customer_data.get('name') or customer_data.get('customer_name') or ''
                customer_email = customer_data.get('email') or customer_data.get('customer_email') or ''
                
                # Criar registro se não existe
                webhook_event, created = WebhookEvent.objects.get_or_create(
                    webhook_hash=webhook_hash,
                    defaults={
                        'payment_id': payment_id,
                        'payment_method': payment_method,
                        'payment_status': payment_status,
                        'amount': int(amount) if amount else 0,
                        'customer_phone': customer_phone,
                        'customer_name': customer_name,
                        'customer_email': customer_email,
                        'raw_data': webhook_data,
                        'processed': True
                    }
                )
                
                if created:
                    logger.info(f"Webhook flexível criado: {webhook_event.id}")
                else:
                    logger.info(f"Webhook flexível já existia: {webhook_event.id}")
                
                return JsonResponse({'status': 'ok', 'id': webhook_event.id})
                
            except Exception as e:
                logger.error(f"Erro ao processar webhook flexível: {str(e)}")
                return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
        else:
            logger.warning("Nenhum dado encontrado no webhook")
            return JsonResponse({'status': 'error', 'message': 'Nenhum dado encontrado'}, status=400)
            
    except Exception as e:
        logger.error(f"Erro geral no webhook flexível: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def tribopay_test_format(request):
    """
    Endpoint de teste para validar o formato real da TriboPay sem usar banco de dados
    """
    try:
        logger.info(f"TriboPay Test Format - Data received: {request.data}")
        
        # Testar o serializer real da TriboPay
        from .serializers import TribePayRealWebhookSerializer
        
        serializer = TribePayRealWebhookSerializer(data=request.data)
        if serializer.is_valid():
            # Converter para formato do webhook event
            webhook_data = serializer.to_webhook_event_data()
            
            # Log dos dados processados
            logger.info(f"TriboPay Test - Dados processados: {webhook_data}")
            
            # Verificar se é PIX aguardando pagamento
            is_pix_waiting = (
                webhook_data.get('payment_method') == 'pix' and 
                webhook_data.get('payment_status') in ['waiting', 'pending']
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Formato TriboPay validado com sucesso',
                'data': {
                    'payment_id': webhook_data.get('payment_id'),
                    'payment_method': webhook_data.get('payment_method'),
                    'payment_status': webhook_data.get('payment_status'),
                    'amount': webhook_data.get('amount'),
                    'amount_in_real': webhook_data.get('amount', 0) / 100,
                    'customer_phone': webhook_data.get('customer_phone'),
                    'customer_name': webhook_data.get('customer_name'),
                    'is_pix_waiting': is_pix_waiting,
                    'would_schedule_sms': is_pix_waiting
                }
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Formato inválido',
                'errors': serializer.errors
            }, status=400)
            
    except Exception as e:
        logger.error(f"Erro no teste de formato: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)
