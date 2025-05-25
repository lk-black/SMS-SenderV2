import logging
from typing import Optional, Tuple
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .logging_utils import webhook_structured_logger

logger = logging.getLogger('webhooks')


class SMSSchedulerService:
    """
    Serviço para agendar SMS com fallback quando Redis/Celery não estão disponíveis
    """
    
    def __init__(self):
        self.redis_available = self._check_redis_availability()
        self.celery_available = self._check_celery_availability()
        
        # Log do status inicial
        webhook_structured_logger.log_scheduler_status(
            redis_available=self.redis_available,
            celery_available=self.celery_available
        )
    
    def _check_redis_availability(self) -> bool:
        """Verifica se o Redis está disponível"""
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 10)
            result = cache.get('health_check')
            is_available = result == 'ok'
            
            if is_available:
                webhook_structured_logger.logger.info("✅ Redis conectado e funcionando")
            else:
                webhook_structured_logger.logger.warning("⚠️ Redis não respondeu corretamente ao teste")
            
            return is_available
        except Exception as e:
            webhook_structured_logger.logger.warning(f"❌ Redis não disponível: {e}")
            return False
    
    def _check_celery_availability(self) -> bool:
        """Verifica se o Celery está disponível"""
        try:
            from .tasks import schedule_sms_recovery
            # Não executar a task, apenas verificar se pode ser importada
            is_available = True and self.redis_available
            
            if is_available:
                webhook_structured_logger.logger.info("✅ Celery disponível")
            else:
                webhook_structured_logger.logger.warning("⚠️ Celery não disponível (Redis necessário)")
            
            return is_available
        except Exception as e:
            webhook_structured_logger.logger.warning(f"❌ Celery não disponível: {e}")
            return False
    
    def is_redis_available(self) -> bool:
        """Método público para verificar Redis"""
        return self.redis_available
    
    def is_celery_available(self) -> bool:
        """Método público para verificar Celery"""
        return self.celery_available
    
    def schedule_sms_recovery(self, webhook_event_id: int, delay_minutes: int = None) -> Tuple[bool, str]:
        """
        Agenda SMS de recuperação
        
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        if delay_minutes is None:
            delay_minutes = getattr(settings, 'SMS_RECOVERY_DELAY_MINUTES', 10)
        
        if not getattr(settings, 'SMS_RECOVERY_ENABLED', True):
            return False, "SMS Recovery está desabilitado nas configurações"
        
        # Tentar agendar via Celery
        if self.celery_available:
            try:
                from .tasks import schedule_sms_recovery
                
                result = schedule_sms_recovery.apply_async(
                    args=[webhook_event_id],
                    countdown=delay_minutes * 60  # Converter para segundos
                )
                
                message = f"SMS agendado via Celery (task_id: {result.id})"
                webhook_structured_logger.logger.info(f"✅ SMS agendado via Celery para webhook {webhook_event_id} em {delay_minutes} minutos")
                return True, message
                
            except Exception as e:
                webhook_structured_logger.logger.error(f"❌ Falha ao agendar SMS via Celery: {e}")
                # Continuar para fallback
        
        # Fallback: Registrar para processamento manual/futuro
        return self._schedule_fallback(webhook_event_id, delay_minutes)
    
    def _schedule_fallback(self, webhook_event_id: int, delay_minutes: int) -> Tuple[bool, str]:
        """
        Fallback quando Redis/Celery não estão disponíveis
        """
        try:
            from .models import WebhookEvent, SMSLog
            
            # Marcar webhook como precisando de SMS
            webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
            webhook_event.sms_scheduled = False  # Marcar como não agendado ainda
            webhook_event.save()
            
            # Criar registro de SMS pendente
            scheduled_time = timezone.now() + timedelta(minutes=delay_minutes)
            
            # Salvar informação no raw_data para processamento posterior
            raw_data = webhook_event.raw_data or {}
            raw_data['sms_recovery'] = {
                'scheduled_for': scheduled_time.isoformat(),
                'delay_minutes': delay_minutes,
                'status': 'pending_redis',
                'reason': 'Redis/Celery não disponível - necessário processamento manual'
            }
            webhook_event.raw_data = raw_data
            webhook_event.save()
            
            logger.warning(f"SMS para webhook {webhook_event_id} registrado para processamento manual em {scheduled_time}")
            
            return True, f"SMS registrado para processamento manual (Redis indisponível). Scheduled for: {scheduled_time}"
            
        except Exception as e:
            logger.error(f"Falha no fallback de agendamento: {e}")
            return False, f"Falha completa no agendamento: {e}"
    
    def get_status(self) -> dict:
        """Retorna status do serviço de agendamento"""
        return {
            'redis_available': self.redis_available,
            'celery_available': self.celery_available,
            'sms_recovery_enabled': getattr(settings, 'SMS_RECOVERY_ENABLED', True),
            'fallback_mode': not self.celery_available,
            'delay_minutes': getattr(settings, 'SMS_RECOVERY_DELAY_MINUTES', 10)
        }
    
    def get_pending_sms(self) -> list:
        """Retorna lista de SMS pendentes para processamento manual"""
        try:
            from .models import WebhookEvent
            
            pending_webhooks = WebhookEvent.objects.filter(
                sms_scheduled=False,
                payment_method='pix',
                payment_status__in=['waiting', 'waiting_payment', 'pending']
            ).exclude(
                raw_data__sms_recovery__status='completed'
            )
            
            pending_list = []
            for webhook in pending_webhooks:
                sms_recovery = webhook.raw_data.get('sms_recovery', {}) if webhook.raw_data else {}
                if sms_recovery.get('status') == 'pending_redis':
                    pending_list.append({
                        'webhook_id': webhook.id,
                        'payment_id': webhook.payment_id,
                        'customer_phone': webhook.customer_phone,
                        'scheduled_for': sms_recovery.get('scheduled_for'),
                        'delay_minutes': sms_recovery.get('delay_minutes', 10)
                    })
            
            return pending_list
            
        except Exception as e:
            logger.error(f"Erro ao buscar SMS pendentes: {e}")
            return []
