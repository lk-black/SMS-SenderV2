import logging
import time
import json
from functools import wraps
from typing import Dict, Any, Optional
from django.conf import settings

# Configurar loggers específicos
webhook_logger = logging.getLogger('webhooks')
sms_logger = logging.getLogger('sms_service')
metrics_logger = logging.getLogger('metrics')

class StructuredLogger:
    """Utilitário para logging estruturado com métricas"""
    
    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)
    
    def log_webhook_received(self, platform: str, webhook_data: Dict[str, Any], request_info: Dict[str, Any] = None):
        """Log estruturado para webhooks recebidos"""
        log_data = {
            'event': 'webhook_received',
            'platform': platform,
            'webhook_id': webhook_data.get('paymentId') or webhook_data.get('token'),
            'method': webhook_data.get('method') or webhook_data.get('paymentMethod'),
            'status': webhook_data.get('status'),
            'amount': webhook_data.get('amount') or webhook_data.get('totalValue'),
            'customer_phone': self._extract_phone(webhook_data),
            'timestamp': time.time()
        }
        
        if request_info:
            log_data.update({
                'user_agent': request_info.get('HTTP_USER_AGENT', ''),
                'ip_address': request_info.get('REMOTE_ADDR', ''),
                'content_length': request_info.get('CONTENT_LENGTH', 0)
            })
        
        self.logger.info(f"Webhook recebido: {platform} | ID: {log_data['webhook_id']} | Status: {log_data['status']}")
        
        # Log detalhado em formato JSON para métricas
        if hasattr(logging.getLogger('metrics'), 'info'):
            logging.getLogger('metrics').info(json.dumps(log_data))
    
    def log_webhook_processed(self, platform: str, webhook_id: str, success: bool, 
                            sms_scheduled: bool = False, error: str = None, processing_time: float = None):
        """Log estruturado para webhooks processados"""
        log_data = {
            'event': 'webhook_processed',
            'platform': platform,
            'webhook_id': webhook_id,
            'success': success,
            'sms_scheduled': sms_scheduled,
            'error': error,
            'processing_time_ms': round(processing_time * 1000) if processing_time else None,
            'timestamp': time.time()
        }
        
        status_emoji = "✅" if success else "❌"
        sms_emoji = "📱" if sms_scheduled else ""
        
        message = f"{status_emoji} Webhook processado: {platform} | ID: {webhook_id}"
        if sms_scheduled:
            message += f" {sms_emoji} SMS agendado"
        if processing_time:
            message += f" | Tempo: {processing_time*1000:.1f}ms"
        if error:
            message += f" | Erro: {error}"
            
        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)
        
        # Log de métricas
        logging.getLogger('metrics').info(json.dumps(log_data))
    
    def log_sms_attempt(self, phone: str, message_type: str, success: bool, 
                       sid: str = None, error: str = None, formatted_phone: str = None):
        """Log estruturado para tentativas de SMS"""
        log_data = {
            'event': 'sms_attempt',
            'phone_original': phone,
            'phone_formatted': formatted_phone or phone,
            'message_type': message_type,
            'success': success,
            'twilio_sid': sid,
            'error': error,
            'timestamp': time.time()
        }
        
        status_emoji = "✅" if success else "❌"
        message = f"{status_emoji} SMS {message_type}: {formatted_phone or phone}"
        
        if success and sid:
            message += f" | SID: {sid}"
        if error:
            message += f" | Erro: {error}"
            
        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)
        
        # Log de métricas
        logging.getLogger('metrics').info(json.dumps(log_data))
    
    def log_phone_formatting(self, original: str, formatted: str, is_valid: bool):
        """Log para formatação de telefone"""
        if original != formatted:
            self.logger.info(f"📞 Telefone formatado: {original} → {formatted} (válido: {is_valid})")
    
    def log_duplicate_webhook(self, platform: str, webhook_id: str, hash_value: str):
        """Log para webhooks duplicados"""
        self.logger.warning(f"🔄 Webhook duplicado ignorado: {platform} | ID: {webhook_id} | Hash: {hash_value[:8]}")
    
    def log_sms_duplicate_blocked(self, webhook_id: int, phone: str, reason: str, similar_webhooks: int = 0):
        """Log estruturado para SMS bloqueados por duplicata"""
        log_data = {
            'event': 'sms_duplicate_blocked',
            'webhook_id': webhook_id,
            'phone': phone,
            'reason': reason,
            'similar_webhooks_count': similar_webhooks,
            'timestamp': time.time()
        }
        
        message = f"🚫 SMS bloqueado (duplicata): Webhook {webhook_id} | Telefone: {phone} | Motivo: {reason}"
        if similar_webhooks > 0:
            message += f" | Webhooks similares: {similar_webhooks}"
            
        self.logger.warning(message)
        
        # Log de métricas
        logging.getLogger('metrics').info(json.dumps(log_data))
    
    def log_sms_duplicate_analysis(self, webhook_id: int, phone: str, amount: int, 
                                 recent_sms_count: int, similar_webhooks_count: int, 
                                 last_sms_hours_ago: float = None):
        """Log detalhado da análise de duplicatas"""
        log_data = {
            'event': 'sms_duplicate_analysis',
            'webhook_id': webhook_id,
            'phone': phone,
            'amount': amount,
            'recent_sms_count': recent_sms_count,
            'similar_webhooks_count': similar_webhooks_count,
            'last_sms_hours_ago': last_sms_hours_ago,
            'timestamp': time.time()
        }
        
        message = f"🔍 Análise duplicata: Webhook {webhook_id} | SMS recentes: {recent_sms_count} | Webhooks similares: {similar_webhooks_count}"
        if last_sms_hours_ago is not None:
            message += f" | Último SMS: {last_sms_hours_ago:.1f}h atrás"
            
        self.logger.info(message)
        
        # Log de métricas
        logging.getLogger('metrics').info(json.dumps(log_data))
    
    def log_sms_sent_recorded(self, webhook_id: int, phone: str, sms_count: int):
        """Log quando SMS é registrado no webhook para controle de duplicatas"""
        message = f"📝 SMS registrado: Webhook {webhook_id} | Telefone: {phone} | Total SMS: {sms_count}"
        self.logger.info(message)
    
    def log_scheduler_status(self, redis_available: bool, celery_available: bool, pending_count: int = 0):
        """Log para status do scheduler"""
        redis_emoji = "✅" if redis_available else "❌"
        celery_emoji = "✅" if celery_available else "❌"
        
        message = f"🔧 Scheduler Status: Redis {redis_emoji} | Celery {celery_emoji}"
        if pending_count > 0:
            message += f" | SMS Pendentes: {pending_count}"
            
        self.logger.info(message)
    
    def _extract_phone(self, webhook_data: Dict[str, Any]) -> Optional[str]:
        """Extrai número de telefone dos dados do webhook"""
        customer = webhook_data.get('customer', {})
        if isinstance(customer, dict):
            return customer.get('phone') or customer.get('phone_number')
        return None

def log_execution_time(logger_name: str = 'webhooks'):
    """Decorator para medir tempo de execução"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            logger = logging.getLogger(logger_name)
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                logger.info(f"⏱️ {func.__name__} executado em {execution_time*1000:.1f}ms")
                
                # Adicionar tempo de execução ao resultado se for um dict
                if isinstance(result, dict):
                    result['_execution_time'] = execution_time
                    
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"❌ {func.__name__} falhou após {execution_time*1000:.1f}ms: {str(e)}")
                raise
                
        return wrapper
    return decorator

# Instâncias globais para uso fácil
webhook_structured_logger = StructuredLogger('webhooks')
sms_structured_logger = StructuredLogger('sms_service')

# Função para configurar logging em tempo de execução
def configure_production_logging():
    """Configurações adicionais de logging para produção"""
    import sys
    
    # Configurar logging para capturar prints não tratados
    class PrintCapture:
        def __init__(self, original_stream, logger, level):
            self.original_stream = original_stream
            self.logger = logger
            self.level = level
            
        def write(self, text):
            if text.strip():
                self.logger.log(self.level, f"STDOUT: {text.strip()}")
            self.original_stream.write(text)
            
        def flush(self):
            self.original_stream.flush()
    
    # Apenas em produção, capturar prints
    if settings.DEBUG is False:
        logger = logging.getLogger('django')
        sys.stdout = PrintCapture(sys.stdout, logger, logging.INFO)
        sys.stderr = PrintCapture(sys.stderr, logger, logging.ERROR)

# Configuração de health check logging
def log_health_check(component: str, status: str, details: Dict[str, Any] = None):
    """Log estruturado para health checks"""
    logger = logging.getLogger('webhooks')
    
    status_emoji = "✅" if status == "healthy" else "⚠️" if status == "warning" else "❌"
    message = f"{status_emoji} Health Check: {component} = {status}"
    
    if details:
        message += f" | Detalhes: {json.dumps(details)}"
    
    if status == "healthy":
        logger.info(message)
    elif status == "warning":
        logger.warning(message)
    else:
        logger.error(message)
