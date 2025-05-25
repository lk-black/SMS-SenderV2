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
    e enviar SMS de recuperação se necessário
    """
    try:
        webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
        
        # Verificar se o pagamento ainda está pendente
        if webhook_event.payment_status == 'waiting_payment':
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
                logger.info(f"SMS enviado com sucesso para webhook {webhook_event_id}")
                
        else:
            logger.info(f"Pagamento já foi processado para webhook {webhook_event_id}")
            
    except WebhookEvent.DoesNotExist:
        logger.error(f"Webhook event {webhook_event_id} não encontrado")
    except Exception as exc:
        logger.error(f"Erro ao processar task para webhook {webhook_event_id}: {str(exc)}")
        raise self.retry(countdown=300, exc=exc)


@shared_task
def schedule_sms_recovery(webhook_event_id):
    """
    Task para enviar SMS de recuperação após verificar status do pagamento
    """
    try:
        webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
        
        # Verificar se o pagamento ainda está pendente
        if webhook_event.payment_status == 'waiting_payment':
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
                message=f"SMS de recuperação enviado para {webhook_event.customer_phone}",
                status='sent' if success else 'failed',
                twilio_sid=message_sid,
                error_message=error
            )
            
            if success:
                logger.info(f"SMS de recuperação enviado com sucesso para webhook {webhook_event_id}")
            else:
                logger.error(f"Falha ao enviar SMS de recuperação para webhook {webhook_event_id}: {error}")
                
        else:
            logger.info(f"Pagamento já foi processado para webhook {webhook_event_id}")
            
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
def test_task_connection():
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
