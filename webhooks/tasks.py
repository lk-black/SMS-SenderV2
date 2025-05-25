import logging
from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone

from .models import WebhookEvent, SMSLog
from sms_service.sms import TwilioSMSService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def check_payment_status(self, webhook_event_id):
    """
    Task para verificar o status do pagamento após 10 minutos
    e enviar SMS de recuperação se necessário.
    Inclui lógica de prevenção de duplicatas
    """
    try:
        webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
        
        # Verificar se o pagamento ainda está pendente
        if webhook_event.payment_status != 'waiting_payment':
            logger.info(f"Pagamento já foi processado para webhook {webhook_event_id}")
            return
        
        # Verificar se pode enviar SMS (anti-duplicata)
        can_send, reason = webhook_event.can_send_sms()
        
        if not can_send:
            logger.info(f"SMS bloqueado para webhook {webhook_event_id}: {reason}")
            
            # Registrar tentativa de duplicata
            SMSLog.create_blocked_duplicate(
                webhook_event=webhook_event,
                phone_number=webhook_event.customer_phone,
                reason=reason
            )
            return
        
        logger.info(f"Enviando SMS de recuperação para webhook {webhook_event_id}")
        
        # Enviar SMS de recuperação
        sms_service = TwilioSMSService()
        success, message_sid, error = sms_service.send_recovery_sms(
            phone_number=webhook_event.customer_phone,
            customer_name=webhook_event.customer_name or "Cliente",
            amount=webhook_event.amount
        )
        
        # Registrar o log do SMS
        SMSLog.objects.create(
            webhook_event=webhook_event,
            phone_number=webhook_event.customer_phone,
            message_content=f"SMS de recuperação enviado para {webhook_event.customer_phone}",
            status='sent' if success else 'failed',
            twilio_sid=message_sid,
            error_message=error
        )
        
        if not success:
            logger.error(f"Falha ao enviar SMS para webhook {webhook_event_id}: {error}")
            # Retry se falhou
            raise self.retry(countdown=300, exc=Exception(error))
        else:
            # Registrar envio no webhook para controle anti-duplicata
            webhook_event.record_sms_sent()
            logger.info(f"SMS enviado com sucesso para webhook {webhook_event_id}")
            
    except WebhookEvent.DoesNotExist:
        logger.error(f"Webhook event {webhook_event_id} não encontrado")
    except Exception as exc:
        logger.error(f"Erro ao processar task para webhook {webhook_event_id}: {str(exc)}")
        raise self.retry(countdown=300, exc=exc)


@shared_task
def schedule_sms_recovery(webhook_event_id):
    """
    Task para enviar SMS de recuperação após verificar status do pagamento
    Inclui lógica de prevenção de duplicatas
    """
    try:
        webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
        
        # Verificar se o pagamento ainda está pendente
        if webhook_event.payment_status != 'waiting_payment':
            logger.info(f"Pagamento já foi processado para webhook {webhook_event_id}")
            return
        
        # Verificar se pode enviar SMS (anti-duplicata)
        can_send, reason = webhook_event.can_send_sms()
        
        if not can_send:
            logger.info(f"SMS bloqueado para webhook {webhook_event_id}: {reason}")
            
            # Registrar tentativa de duplicata
            SMSLog.create_blocked_duplicate(
                webhook_event=webhook_event,
                phone_number=webhook_event.customer_phone,
                reason=reason
            )
            return
        
        logger.info(f"Enviando SMS de recuperação para webhook {webhook_event_id}")
        
        # Enviar SMS de recuperação
        sms_service = TwilioSMSService()
        success, message_sid, error = sms_service.send_recovery_sms(
            phone_number=webhook_event.customer_phone,
            customer_name=webhook_event.customer_name or "Cliente",
            amount=webhook_event.amount
        )
        
        # Registrar o log do SMS
        sms_log = SMSLog.objects.create(
            webhook_event=webhook_event,
            phone_number=webhook_event.customer_phone,
            message=f"SMS de recuperação enviado para {webhook_event.customer_phone}",
            status='sent' if success else 'failed',
            twilio_sid=message_sid,
            error_message=error
        )
        
        if success:
            # Registrar envio no webhook para controle anti-duplicata
            webhook_event.record_sms_sent()
            logger.info(f"SMS de recuperação enviado com sucesso para webhook {webhook_event_id}")
        else:
            logger.error(f"Falha ao enviar SMS de recuperação para webhook {webhook_event_id}: {error}")
            
    except WebhookEvent.DoesNotExist:
        logger.error(f"Webhook event {webhook_event_id} não encontrado")
    except Exception as exc:
        logger.error(f"Erro ao processar SMS de recuperação para webhook {webhook_event_id}: {str(exc)}")


@shared_task
def update_payment_status(webhook_event_id, new_status):
    """
    Atualiza o status do pagamento quando receber webhook de atualização
    """
    try:
        webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
        old_status = webhook_event.payment_status
        webhook_event.payment_status = new_status
        webhook_event.updated_at = timezone.now()
        webhook_event.save()
        
        logger.info(f"Status do webhook {webhook_event_id} atualizado de {old_status} para {new_status}")
        
    except WebhookEvent.DoesNotExist:
        logger.error(f"Webhook event {webhook_event_id} não encontrado para atualização")
    except Exception as exc:
        logger.error(f"Erro ao atualizar status do webhook {webhook_event_id}: {str(exc)}")


@shared_task
def test_task_connection(test_message="Teste de conexão"):
    """
    Task simples para testar conexão Redis/Celery
    """
    import time
    from datetime import datetime
    
    logger.info("Task de teste iniciada")
    
    # Simular algum processamento
    time.sleep(1)
    
    result = {
        'status': 'success',
        'message': 'Redis/Celery funcionando corretamente',
        'timestamp': datetime.now().isoformat(),
        'task_id': test_task_connection.request.id if hasattr(test_task_connection, 'request') else None
    }
    
    logger.info(f"Task de teste concluída: {result}")
    return result


@shared_task
def test_worker_database_access():
    """
    Task para testar se o worker consegue acessar corretamente o banco de dados
    Especificamente testa se consegue acessar a tabela webhook_events
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("=== TESTE DE ACESSO AO BANCO DE DADOS PELO WORKER ===")
        
        # Tentar importar os models
        from .models import WebhookEvent, SMSLog
        logger.info("✅ Models importados com sucesso")
        
        # Verificar se consegue acessar a tabela webhook_events
        try:
            webhook_count = WebhookEvent.objects.count()
            logger.info(f"✅ Tabela webhook_events acessível - {webhook_count} registros")
        except Exception as e:
            logger.error(f"❌ ERRO ao acessar webhook_events: {str(e)}")
            logger.error(f"❌ Tipo do erro: {type(e)}")
            return f"ERRO webhook_events: {str(e)}"
        
        # Verificar se consegue acessar a tabela sms_logs  
        try:
            sms_count = SMSLog.objects.count()
            logger.info(f"✅ Tabela sms_logs acessível - {sms_count} registros")
        except Exception as e:
            logger.error(f"❌ ERRO ao acessar sms_logs: {str(e)}")
            return f"ERRO sms_logs: {str(e)}"
        
        # Testar se consegue buscar um webhook específico
        try:
            latest_webhook = WebhookEvent.objects.order_by('-created_at').first()
            if latest_webhook:
                logger.info(f"✅ Webhook mais recente acessível - ID: {latest_webhook.id}")
                logger.info(f"   Payment ID: {latest_webhook.payment_id}")
                logger.info(f"   Status: {latest_webhook.payment_status}")
                logger.info(f"   Method: {latest_webhook.payment_method}")
            else:
                logger.info("⚠️ Nenhum webhook encontrado na tabela")
        except Exception as e:
            logger.error(f"❌ ERRO ao buscar webhook específico: {str(e)}")
            return f"ERRO busca webhook: {str(e)}"
        
        # Testar importação da função can_send_sms
        try:
            if latest_webhook:
                can_send, reason = latest_webhook.can_send_sms()
                logger.info(f"✅ Método can_send_sms funcionando - Pode enviar: {can_send}, Razão: {reason}")
            else:
                logger.info("⚠️ Não foi possível testar can_send_sms - sem webhooks")
        except Exception as e:
            logger.error(f"❌ ERRO ao testar can_send_sms: {str(e)}")
            return f"ERRO can_send_sms: {str(e)}"
        
        logger.info("🎉 TESTE COMPLETO - Worker consegue acessar o banco corretamente!")
        return f"SUCESSO - webhook_events: {webhook_count}, sms_logs: {sms_count}"
        
    except Exception as exc:
        logger.error(f"❌ ERRO FATAL no teste de banco: {str(exc)}")
        logger.error(f"❌ Tipo do erro: {type(exc)}")
        return f"ERRO FATAL: {str(exc)}"
