import logging
import json
import hashlib
import time
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
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
    SMSLogSerializer,
    GhostPayWebhookSerializer  # Serializer for GhostPay webhooks
)
from .tasks import schedule_sms_recovery
from .logging_utils import (
    webhook_structured_logger, 
    sms_structured_logger, 
    log_execution_time,
    log_health_check
)

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
                
                # Usar o novo SMSSchedulerService com fallback automático
                from .sms_scheduler import SMSSchedulerService
                scheduler = SMSSchedulerService()
                
                success, message = scheduler.schedule_sms_recovery(webhook_event.id)
                
                if success:
                    webhook_event.sms_scheduled = True
                    webhook_event.save()
                    logger.info(f"SMS agendado com sucesso para webhook {webhook_event.id}: {message}")
                else:
                    logger.warning(f"Falha ao agendar SMS para webhook {webhook_event.id}: {message}")
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
        Processa webhook da TriboPay com logging estruturado
        """
        start_time = time.time()
        platform = "TriboPay"
        webhook_id = None
        
        try:
            # Log do webhook recebido
            webhook_structured_logger.log_webhook_received(
                platform=platform,
                webhook_data=request.data,
                request_info=request.META
            )
            
            # Validar dados do webhook
            serializer = self.get_serializer(data=request.data)
            if not serializer.is_valid():
                processing_time = time.time() - start_time
                webhook_structured_logger.log_webhook_processed(
                    platform=platform,
                    webhook_id=str(request.data.get('token', 'unknown')),
                    success=False,
                    error=f"Dados inválidos: {serializer.errors}",
                    processing_time=processing_time
                )
                return Response(
                    {"error": "Dados inválidos", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Processar webhook
            webhook_data = serializer.to_webhook_event_data()
            webhook_id = webhook_data.get('payment_id')
            
            webhook_event, created = WebhookEvent.objects.get_or_create(
                defaults=webhook_data,
                **{k: v for k, v in webhook_data.items() 
                   if k in ['payment_id', 'customer_phone', 'payment_method']}
            )
            
            sms_scheduled = False
            
            if created:
                webhook_structured_logger.logger.info(f"✅ Novo webhook criado: {webhook_event}")
                
                # Verificar se deve agendar SMS
                if webhook_event.is_pix_waiting_payment():
                    webhook_structured_logger.logger.info(f"📱 PIX aguardando detectado - agendando SMS para webhook {webhook_event.id}")
                    
                    try:
                        from .sms_scheduler import SMSSchedulerService
                        scheduler = SMSSchedulerService()
                        
                        success, message = scheduler.schedule_sms_recovery(webhook_event.id)
                        
                        if success:
                            webhook_event.sms_scheduled = True
                            webhook_event.save()
                            sms_scheduled = True
                            webhook_structured_logger.logger.info(f"✅ SMS agendado com sucesso para webhook {webhook_event.id}: {message}")
                        else:
                            webhook_structured_logger.logger.warning(f"⚠️ Falha ao agendar SMS para webhook {webhook_event.id}: {message}")
                            
                    except Exception as sms_error:
                        webhook_structured_logger.logger.error(f"❌ Erro ao agendar SMS para webhook {webhook_event.id}: {str(sms_error)}")
            else:
                webhook_structured_logger.log_duplicate_webhook(platform, webhook_id, webhook_event.webhook_hash)
            
            # Marcar como processado
            webhook_event.processed = True
            webhook_event.save()
            
            processing_time = time.time() - start_time
            webhook_structured_logger.log_webhook_processed(
                platform=platform,
                webhook_id=webhook_id,
                success=True,
                sms_scheduled=sms_scheduled,
                processing_time=processing_time
            )
            
            return Response({"status": "ok"}, status=status.HTTP_200_OK)
            
        except Exception as e:
            processing_time = time.time() - start_time
            webhook_structured_logger.log_webhook_processed(
                platform=platform,
                webhook_id=webhook_id or 'unknown',
                success=False,
                error=str(e),
                processing_time=processing_time
            )
            
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
@log_execution_time('webhooks')
def health_check(request):
    """
    Endpoint de health check para monitoramento com logging estruturado
    """
    start_time = time.time()
    
    try:
        # Database check
        try:
            from django.db import connection
            connection.ensure_connection()
            db_status = "connected"
            log_health_check("database", "healthy")
        except Exception as e:
            db_status = f"error: {str(e)}"
            log_health_check("database", "error", {"error": str(e)})

        # Cache/Redis check
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 10)
            cache_result = cache.get('health_check')
            if cache_result == 'ok':
                cache_status = "connected"
                log_health_check("cache", "healthy")
            else:
                cache_status = "warning: test failed"
                log_health_check("cache", "warning", {"test_result": cache_result})
        except Exception as e:
            cache_status = f"error: {str(e)}"
            log_health_check("cache", "error", {"error": str(e)})

        # SMS Scheduler check
        try:
            from .sms_scheduler import SMSSchedulerService
            scheduler = SMSSchedulerService()
            redis_available = scheduler.is_redis_available()
            celery_available = scheduler.is_celery_available()
            
            if redis_available and celery_available:
                sms_status = {"redis_available": True, "celery_available": True}
                log_health_check("sms_scheduler", "healthy", sms_status)
            else:
                sms_status = {"redis_available": redis_available, "celery_available": celery_available}
                log_health_check("sms_scheduler", "warning", sms_status)
        except Exception as e:
            sms_status = f"error: {str(e)}"
            log_health_check("sms_scheduler", "error", {"error": str(e)})

        processing_time = time.time() - start_time
        
        health_data = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'database': db_status,
            'cache': cache_status,
            'sms_scheduler': sms_status,
            'processing_time_ms': round(processing_time * 1000, 2)
        }
        
        webhook_structured_logger.logger.info(f"🏥 Health check completado em {processing_time*1000:.1f}ms")
        
        return JsonResponse(health_data)
        
    except Exception as e:
        processing_time = time.time() - start_time
        webhook_structured_logger.logger.error(f"🚨 Health check falhou após {processing_time*1000:.1f}ms: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'processing_time_ms': round(processing_time * 1000, 2)
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
                    
                    # Se for PIX aguardando pagamento, agendar SMS de recuperação
                    if payment_method == 'pix' and payment_status in ['waiting', 'waiting_payment', 'pending']:
                        logger.info(f"Agendando SMS de recuperação para webhook flexível {webhook_event.id}")
                        
                        # Usar o novo SMSSchedulerService com fallback automático
                        from .sms_scheduler import SMSSchedulerService
                        scheduler = SMSSchedulerService()
                        
                        success, message = scheduler.schedule_sms_recovery(webhook_event.id)
                        
                        if success:
                            webhook_event.sms_scheduled = True
                            webhook_event.save()
                            logger.info(f"SMS agendado com sucesso para webhook flexível {webhook_event.id}: {message}")
                        else:
                            logger.warning(f"Falha ao agendar SMS para webhook flexível {webhook_event.id}: {message}")
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


@api_view(['GET'])
@permission_classes([AllowAny])
def sms_scheduler_status(request):
    """
    Endpoint para verificar status do SMS Scheduler Service
    """
    try:
        from .sms_scheduler import SMSSchedulerService
        scheduler = SMSSchedulerService()
        status_info = scheduler.get_status()
        
        return JsonResponse({
            'status': 'success',
            'scheduler_status': status_info,
            'message': 'Fallback mode' if status_info['fallback_mode'] else 'Full functionality'
        })
        
    except Exception as e:
        logger.error(f"Erro ao verificar status do scheduler: {e}")
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def pending_sms_list(request):
    """
    Endpoint para listar SMS pendentes para processamento manual
    """
    try:
        from .sms_scheduler import SMSSchedulerService
        scheduler = SMSSchedulerService()
        pending_sms = scheduler.get_pending_sms()
        
        return JsonResponse({
            'status': 'success',
            'count': len(pending_sms),
            'pending_sms': pending_sms
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar SMS pendentes: {e}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def test_phone_formatting(request):
    """
    Testa a formatação de números de telefone sem enviar SMS
    """
    try:
        phone_number = request.data.get('phone_number')
        if not phone_number:
            return Response({'error': 'phone_number é obrigatório'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Instanciar serviço SMS
        from sms_service.sms import TwilioSMSService
        sms_service = TwilioSMSService()
        
        # Testar formatação
        formatted_phone = sms_service.format_phone_for_twilio(phone_number)
        is_valid = sms_service.validate_phone_number(phone_number)
        
        return Response({
            'original_phone': phone_number,
            'formatted_phone': formatted_phone,
            'is_valid': is_valid,
            'formatting_applied': phone_number != formatted_phone
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Erro ao testar formatação: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Erro interno do servidor'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class GhostPayWebhookView(generics.GenericAPIView):
    """
    View para receber webhooks da GhostPay
    """
    serializer_class = GhostPayWebhookSerializer
    permission_classes = [AllowAny]
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        """
        Processa webhook da GhostPay com logging estruturado
        """
        start_time = time.time()
        platform = "GhostPay"
        webhook_id = None
        
        try:
            # Log informações brutas da requisição para debug
            webhook_structured_logger.logger.info(f"🔍 GhostPay Raw Request - Content-Type: {request.content_type}")
            webhook_structured_logger.logger.info(f"🔍 GhostPay Raw Request - Body: {request.body.decode('utf-8', errors='ignore')}")
            
            # Parse manual do JSON para evitar problemas de encoding
            request_data = None
            
            # Tentar parse manual do JSON
            if request.body:
                try:
                    # Primeiro tentar decode UTF-8 padrão
                    body_str = request.body.decode('utf-8')
                    request_data = json.loads(body_str)
                except UnicodeDecodeError:
                    # Se falhar, tentar com ISO-8859-1
                    try:
                        body_str = request.body.decode('iso-8859-1')
                        request_data = json.loads(body_str)
                    except:
                        # Como último recurso, usar o request.data do DRF
                        request_data = request.data
                except json.JSONDecodeError as e:
                    # Log detalhado do erro JSON
                    webhook_structured_logger.logger.error(f"❌ GhostPay JSON Parse Error: {str(e)}")
                    webhook_structured_logger.logger.error(f"❌ Problematic JSON: {request.body.decode('utf-8', errors='replace')}")
                    
                    processing_time = time.time() - start_time
                    webhook_structured_logger.log_webhook_processed(
                        platform=platform,
                        webhook_id='unknown',
                        success=False,
                        error=f"JSON parse error - {str(e)}",
                        processing_time=processing_time
                    )
                    return Response(
                        {"error": "JSON inválido", "details": str(e)},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                # Se não há body, usar request.data
                request_data = request.data
            
            # Log do webhook recebido
            webhook_structured_logger.log_webhook_received(
                platform=platform,
                webhook_data=request_data,
                request_info=request.META
            )
            
            # Validar dados do webhook
            serializer = self.get_serializer(data=request_data)
            if not serializer.is_valid():
                processing_time = time.time() - start_time
                webhook_structured_logger.log_webhook_processed(
                    platform=platform,
                    webhook_id=str(request_data.get('paymentId', 'unknown')),
                    success=False,
                    error=f"Dados inválidos: {serializer.errors}",
                    processing_time=processing_time
                )
                return Response(
                    {"error": "Dados inválidos", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Processar webhook
            webhook_data = serializer.to_webhook_event_data()
            webhook_id = webhook_data.get('payment_id')
            
            webhook_event, created = WebhookEvent.objects.get_or_create(
                defaults=webhook_data,
                **{k: v for k, v in webhook_data.items() 
                   if k in ['payment_id', 'customer_phone', 'payment_method']}
            )
            
            sms_scheduled = False
            
            if created:
                webhook_structured_logger.logger.info(f"✅ Novo webhook GhostPay criado: {webhook_event}")
                
                # Verificar se deve agendar SMS
                if webhook_event.is_pix_waiting_payment():
                    webhook_structured_logger.logger.info(f"📱 PIX aguardando detectado - agendando SMS para webhook {webhook_event.id}")
                    
                    try:
                        from .sms_scheduler import SMSSchedulerService
                        scheduler = SMSSchedulerService()
                        
                        success, message = scheduler.schedule_sms_recovery(webhook_event.id)
                        
                        if success:
                            webhook_event.sms_scheduled = True
                            webhook_event.save()
                            sms_scheduled = True
                            webhook_structured_logger.logger.info(f"✅ SMS agendado com sucesso para webhook {webhook_event.id}: {message}")
                        else:
                            webhook_structured_logger.logger.warning(f"⚠️ Falha ao agendar SMS para webhook {webhook_event.id}: {message}")
                            
                    except Exception as sms_error:
                        webhook_structured_logger.logger.error(f"❌ Erro ao agendar SMS para webhook {webhook_event.id}: {str(sms_error)}")
            else:
                webhook_structured_logger.log_duplicate_webhook(platform, webhook_id, webhook_event.webhook_hash)
            
            # Marcar como processado
            webhook_event.processed = True
            webhook_event.save()
            
            processing_time = time.time() - start_time
            webhook_structured_logger.log_webhook_processed(
                platform=platform,
                webhook_id=webhook_id,
                success=True,
                sms_scheduled=sms_scheduled,
                processing_time=processing_time
            )
            
            return Response({"status": "ok"}, status=status.HTTP_200_OK)
            
        except Exception as e:
            processing_time = time.time() - start_time
            webhook_structured_logger.log_webhook_processed(
                platform=platform,
                webhook_id=webhook_id or 'unknown',
                success=False,
                error=str(e),
                processing_time=processing_time
            )
            
            return Response(
                {'error': 'Erro interno do servidor'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def ghostpay_test_format(request):
    """
    Endpoint de teste para validar o formato da GhostPay sem usar banco de dados
    """
    try:
        logger.info(f"GhostPay Test Format - Data received: {request.data}")
        
        # Testar o serializer da GhostPay
        from .serializers import GhostPayWebhookSerializer
        
        serializer = GhostPayWebhookSerializer(data=request.data)
        if serializer.is_valid():
            # Converter para formato do webhook event
            webhook_data = serializer.to_webhook_event_data()
            
            # Log dos dados processados
            logger.info(f"GhostPay Test - Dados processados: {webhook_data}")
            
            # Verificar se é PIX aguardando pagamento
            is_pix_waiting = (
                webhook_data.get('payment_method') == 'pix' and 
                webhook_data.get('payment_status') in ['waiting_payment', 'pending']
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Formato GhostPay validado com sucesso',
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
        logger.error(f"Erro no teste de formato GhostPay: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def ghostpay_debug(request):
    """
    Endpoint de debug para capturar exatamente o que a GhostPay está enviando
    """
    try:
        # Capturar todos os dados da requisição
        debug_data = {
            'method': request.method,
            'headers': dict(request.headers),
            'content_type': request.content_type,
            'body_raw': request.body.decode('utf-8', errors='replace'),
            'body_length': len(request.body) if request.body else 0,
            'POST': dict(request.POST),
            'GET': dict(request.GET),
        }
        
        # Tentar diferentes métodos de parse
        json_attempts = []
        
        # Tentativa 1: UTF-8 padrão
        if request.body:
            try:
                body_utf8 = request.body.decode('utf-8')
                parsed_json = json.loads(body_utf8)
                json_attempts.append({
                    'method': 'utf-8',
                    'success': True,
                    'data': parsed_json
                })
            except Exception as e:
                json_attempts.append({
                    'method': 'utf-8',
                    'success': False,
                    'error': str(e)
                })
            
            # Tentativa 2: ISO-8859-1
            try:
                body_iso = request.body.decode('iso-8859-1')
                parsed_json = json.loads(body_iso)
                json_attempts.append({
                    'method': 'iso-8859-1',
                    'success': True,
                    'data': parsed_json
                })
            except Exception as e:
                json_attempts.append({
                    'method': 'iso-8859-1',
                    'success': False,
                    'error': str(e)
                })
        
        # Tentativa 3: request.data do DRF
        try:
            drf_data = request.data
            json_attempts.append({
                'method': 'drf_request_data',
                'success': True,
                'data': drf_data
            })
        except Exception as e:
            json_attempts.append({
                'method': 'drf_request_data',
                'success': False,
                'error': str(e)
            })
        
        debug_data['json_parse_attempts'] = json_attempts
        
        # Log os dados de debug
        logger.info(f"GhostPay Debug: {json.dumps(debug_data, indent=2, ensure_ascii=False, default=str)}")
        
        # Encontrar o primeiro parse bem-sucedido
        successful_parse = next((attempt for attempt in json_attempts if attempt['success']), None)
        
        if successful_parse:
            # Tentar processar com o serializer
            try:
                from .serializers import GhostPayWebhookSerializer
                serializer = GhostPayWebhookSerializer(data=successful_parse['data'])
                
                if serializer.is_valid():
                    webhook_data = serializer.to_webhook_event_data()
                    debug_data['serializer_result'] = {
                        'success': True,
                        'webhook_data': webhook_data
                    }
                else:
                    debug_data['serializer_result'] = {
                        'success': False,
                        'errors': serializer.errors
                    }
            except Exception as e:
                debug_data['serializer_result'] = {
                    'success': False,
                    'error': str(e)
                }
        
        return JsonResponse({
            'status': 'debug_complete',
            'debug_data': debug_data
        })
        
    except Exception as e:
        logger.error(f"Erro no debug GhostPay: {str(e)}")
        return JsonResponse({
            'status': 'debug_error',
            'error': str(e)
        }, status=500)
