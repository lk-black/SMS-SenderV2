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
    Inclui lógica de prevenção de duplicatas e cancelamento de tasks
    """
    task_id = self.request.id
    
    try:
        logger.info(f"🔄 [WORKER] Iniciando verificação de pagamento - Webhook ID: {webhook_event_id}, Task ID: {task_id}")
        
        webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
        
        # Remover esta task da lista de pendentes (task está sendo executada)
        if task_id:
            webhook_event.remove_pending_task(task_id)
        
        # Log detalhado do webhook
        logger.info(f"📋 [WORKER] Webhook carregado - ID: {webhook_event_id}")
        logger.info(f"   💰 Payment ID: {webhook_event.payment_id}")
        logger.info(f"   👤 Cliente: {webhook_event.customer_name} ({webhook_event.customer_phone})")
        logger.info(f"   💵 Valor: R$ {webhook_event.amount/100:.2f}")
        logger.info(f"   🔄 Status: {webhook_event.payment_status}")
        logger.info(f"   📱 Método: {webhook_event.payment_method}")
        
        # Verificar se o pagamento ainda está pendente
        if webhook_event.payment_status != 'waiting_payment':
            logger.info(f"✅ [WORKER] Pagamento já foi processado para webhook {webhook_event_id} - Status: {webhook_event.payment_status}")
            return
        
        # Verificar se pode enviar SMS (anti-duplicata)
        can_send, reason = webhook_event.can_send_sms()
        
        if not can_send:
            logger.warning(f"🚫 [WORKER] SMS bloqueado para webhook {webhook_event_id}")
            logger.warning(f"   📞 Telefone: {webhook_event.customer_phone}")
            logger.warning(f"   ❌ Razão: {reason}")
            
            # Registrar tentativa de duplicata
            SMSLog.create_blocked_duplicate(
                webhook_event=webhook_event,
                phone_number=webhook_event.customer_phone,
                reason=reason
            )
            return
        
        logger.info(f"📱 [WORKER] Preparando envio de SMS de recuperação")
        logger.info(f"   🎯 Webhook ID: {webhook_event_id}")
        logger.info(f"   📞 Para: {webhook_event.customer_phone}")
        logger.info(f"   👤 Cliente: {webhook_event.customer_name or 'Cliente'}")
        
        # Preparar dados da mensagem ANTES do envio
        from decimal import Decimal
        amount_formatted = ""
        if webhook_event.amount:
            amount_decimal = Decimal(webhook_event.amount) / 100
            amount_formatted = f"de R$ {amount_decimal:.2f} "
        
        sms_service = TwilioSMSService()
        message_content = sms_service._create_recovery_message(
            webhook_event.customer_name or "Cliente", 
            amount_formatted
        )
        
        # Logs detalhados PRÉ-ENVIO
        logger.info(f"💬 [WORKER] Conteúdo da mensagem preparada:")
        logger.info(f"   📝 Texto: {message_content}")
        logger.info(f"   📏 Comprimento: {len(message_content)} caracteres")
        logger.info(f"   💰 Valor formatado: {amount_formatted.strip() if amount_formatted else 'Não especificado'}")
        
        # Log de formatação do telefone
        formatted_phone = sms_service.format_phone_for_twilio(webhook_event.customer_phone)
        logger.info(f"📞 [WORKER] Formatação do telefone:")
        logger.info(f"   📱 Original: {webhook_event.customer_phone}")
        logger.info(f"   🌍 Formatado: {formatted_phone}")
        
        # Enviar SMS de recuperação
        success, message_sid, error = sms_service.send_recovery_sms(
            phone_number=webhook_event.customer_phone,
            customer_name=webhook_event.customer_name or "Cliente",
            amount=webhook_event.amount
        )
        
        # Log detalhado do resultado
        if success:
            logger.info(f"✅ [WORKER] SMS enviado com sucesso!")
            logger.info(f"   📞 Para: {webhook_event.customer_phone} (formatado: {formatted_phone})")
            logger.info(f"   🆔 Twilio SID: {message_sid}")
            logger.info(f"   💬 Mensagem confirmada: {message_content}")
            logger.info(f"   💰 Valor: R$ {webhook_event.amount/100:.2f}")
            logger.info(f"   ⏱️ Task ID: {self.request.id}")
            logger.info(f"   🕐 Tentativa: {self.request.retries + 1}/{self.max_retries}")
        else:
            logger.error(f"❌ [WORKER] Falha ao enviar SMS!")
            logger.error(f"   📞 Para: {webhook_event.customer_phone} (formatado: {formatted_phone})")
            logger.error(f"   ❌ Erro detalhado: {error}")
            logger.error(f"   💬 Mensagem que falhou: {message_content}")
            logger.error(f"   ⏱️ Task ID: {self.request.id}")
            logger.error(f"   🕐 Tentativa: {self.request.retries + 1}/{self.max_retries}")
            
            # Log adicional de debug para falhas
            if error:
                import traceback
                logger.error(f"   📋 Stack trace: {traceback.format_exc()}")
        
        # Registrar o log do SMS com informações detalhadas
        logger.info(f"📝 [WORKER] Criando registro no SMSLog...")
        logger.info(f"   🎯 Webhook ID: {webhook_event.id}")
        logger.info(f"   📞 Telefone: {webhook_event.customer_phone}")
        logger.info(f"   💬 Mensagem: {len(message_content)} chars")
        logger.info(f"   ✅/❌ Status: {'sent' if success else 'failed'}")
        if message_sid:
            logger.info(f"   🆔 Twilio SID: {message_sid}")
        if error:
            logger.info(f"   ❌ Erro: {error}")
            
        SMSLog.objects.create(
            webhook_event=webhook_event,
            phone_number=webhook_event.customer_phone,
            message_content=message_content,
            status='sent' if success else 'failed',
            twilio_sid=message_sid,
            error_message=error
        )
        
        logger.info(f"📝 [WORKER] SMSLog registrado com sucesso!")
        
        if not success:
            logger.error(f"🔄 [WORKER] Agendando retry para webhook {webhook_event_id} em 5 minutos")
            logger.error(f"   🕐 Próxima tentativa: {self.request.retries + 2}/{self.max_retries}")
            # Retry se falhou
            raise self.retry(countdown=300, exc=Exception(error))
        else:
            # Registrar envio no webhook para controle anti-duplicata
            webhook_event.record_sms_sent()
            logger.info(f"🎉 [WORKER] Processamento concluído com sucesso para webhook {webhook_event_id}")
            logger.info(f"   📊 Status final: SMS enviado e registrado")
            logger.info(f"   🗑️ Tasks pendentes canceladas automaticamente")
            
    except WebhookEvent.DoesNotExist:
        logger.error(f"❌ [WORKER] Webhook event {webhook_event_id} não encontrado na base de dados")
        logger.error(f"   🔍 Possíveis causas: ID inválido, webhook deletado, problema de sincronização")
        logger.error(f"   ⏱️ Task ID: {self.request.id}")
    except Exception as exc:
        logger.error(f"💥 [WORKER] Erro inesperado ao processar webhook {webhook_event_id}")
        logger.error(f"   ❌ Erro: {str(exc)}")
        logger.error(f"   🔧 Tipo do erro: {type(exc).__name__}")
        logger.error(f"   ⏱️ Task ID: {self.request.id}")
        logger.error(f"   🔄 Tentativa: {self.request.retries + 1}/{self.max_retries}")
        
        # Log do traceback completo para debug
        import traceback
        logger.error(f"   📋 Traceback completo:")
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                logger.error(f"     {line}")
                
        raise self.retry(countdown=300, exc=exc)


@shared_task
def schedule_sms_recovery(webhook_event_id):
    """
    Task para enviar SMS de recuperação após verificar status do pagamento
    Inclui lógica de prevenção de duplicatas e cancelamento de tasks
    """
    task_id = schedule_sms_recovery.request.id
    
    try:
        logger.info(f"🚀 [WORKER] Iniciando task de recuperação SMS - Webhook ID: {webhook_event_id}, Task ID: {task_id}")
        
        webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
        
        # Remover esta task da lista de pendentes (task está sendo executada)
        if task_id:
            webhook_event.remove_pending_task(task_id)
        
        # Log detalhado do webhook
        logger.info(f"📋 [WORKER] Dados do webhook carregados:")
        logger.info(f"   💰 Payment ID: {webhook_event.payment_id}")
        logger.info(f"   👤 Cliente: {webhook_event.customer_name} ({webhook_event.customer_phone})")
        logger.info(f"   💵 Valor: R$ {webhook_event.amount/100:.2f}")
        logger.info(f"   🔄 Status: {webhook_event.payment_status}")
        logger.info(f"   📱 Método: {webhook_event.payment_method}")
        
        # Verificar se o pagamento ainda está pendente
        if webhook_event.payment_status != 'waiting_payment':
            logger.info(f"✅ [WORKER] Pagamento já processado - Status atual: {webhook_event.payment_status}")
            return
        
        # Verificar se pode enviar SMS (anti-duplicata)
        can_send, reason = webhook_event.can_send_sms()
        
        if not can_send:
            logger.warning(f"🚫 [WORKER] SMS bloqueado por política anti-duplicata")
            logger.warning(f"   📞 Telefone: {webhook_event.customer_phone}")
            logger.warning(f"   ❌ Razão: {reason}")
            
            # Registrar tentativa de duplicata
            SMSLog.create_blocked_duplicate(
                webhook_event=webhook_event,
                phone_number=webhook_event.customer_phone,
                reason=reason
            )
            return
        
        logger.info(f"📱 [WORKER] Preparando envio de SMS de recuperação")
        logger.info(f"   🎯 Destino: {webhook_event.customer_phone}")
        logger.info(f"   👤 Cliente: {webhook_event.customer_name or 'Cliente'}")
        
        # Capturar a mensagem que será enviada ANTES do envio para logging completo
        from decimal import Decimal
        amount_formatted = ""
        if webhook_event.amount:
            amount_decimal = Decimal(webhook_event.amount) / 100
            amount_formatted = f"de R$ {amount_decimal:.2f} "
        
        sms_service = TwilioSMSService()
        message_content = sms_service._create_recovery_message(
            webhook_event.customer_name or "Cliente", 
            amount_formatted
        )
        
        # Logs detalhados PRÉ-ENVIO
        logger.info(f"💬 [WORKER] Conteúdo da mensagem preparada:")
        logger.info(f"   📝 Texto: {message_content}")
        logger.info(f"   📏 Comprimento: {len(message_content)} caracteres")
        logger.info(f"   💰 Valor formatado: {amount_formatted.strip() if amount_formatted else 'Não especificado'}")
        
        # Log de formatação do telefone
        formatted_phone = sms_service.format_phone_for_twilio(webhook_event.customer_phone)
        logger.info(f"📞 [WORKER] Formatação do telefone:")
        logger.info(f"   📱 Original: {webhook_event.customer_phone}")
        logger.info(f"   🌍 Formatado: {formatted_phone}")
        
        # Enviar SMS de recuperação
        success, message_sid, error = sms_service.send_recovery_sms(
            phone_number=webhook_event.customer_phone,
            customer_name=webhook_event.customer_name or "Cliente",
            amount=webhook_event.amount
        )
        
        # Log detalhado do resultado
        if success:
            logger.info(f"✅ [WORKER] SMS de recuperação enviado com sucesso!")
            logger.info(f"   📞 Para: {webhook_event.customer_phone} (formatado: {formatted_phone})")
            logger.info(f"   🆔 Twilio SID: {message_sid}")
            logger.info(f"   💬 Mensagem confirmada: {message_content}")
            logger.info(f"   💰 Valor: R$ {webhook_event.amount/100:.2f}")
            logger.info(f"   📏 Tamanho da mensagem: {len(message_content)} caracteres")
        else:
            logger.error(f"❌ [WORKER] Falha no envio do SMS de recuperação!")
            logger.error(f"   📞 Para: {webhook_event.customer_phone} (formatado: {formatted_phone})")
            logger.error(f"   ❌ Erro detalhado: {error}")
            logger.error(f"   💬 Mensagem que falhou: {message_content}")
            logger.error(f"   📏 Tamanho da mensagem: {len(message_content)} caracteres")
            
            # Log adicional de debug para falhas
            if error:
                import traceback
                logger.error(f"   📋 Stack trace: {traceback.format_exc()}")
        
        # Registrar o log do SMS com informações detalhadas
        logger.info(f"📝 [WORKER] Criando registro detalhado no SMSLog...")
        logger.info(f"   🎯 Webhook ID: {webhook_event.id}")
        logger.info(f"   📞 Telefone: {webhook_event.customer_phone} -> {formatted_phone}")
        logger.info(f"   💬 Mensagem: {len(message_content)} caracteres")
        logger.info(f"   ✅/❌ Status: {'sent' if success else 'failed'}")
        if message_sid:
            logger.info(f"   🆔 Twilio SID: {message_sid}")
        if error:
            logger.info(f"   ❌ Erro capturado: {error}")
            
        sms_log = SMSLog.objects.create(
            webhook_event=webhook_event,
            phone_number=webhook_event.customer_phone,
            message=message_content,
            status='sent' if success else 'failed',
            twilio_sid=message_sid,
            error_message=error
        )
        
        logger.info(f"📝 [WORKER] SMS Log criado com sucesso - ID: {sms_log.id}")
        logger.info(f"   🕐 Timestamp: {sms_log.created_at}")
        
        if success:
            # Registrar envio no webhook para controle anti-duplicata
            webhook_event.record_sms_sent()
            logger.info(f"🎉 [WORKER] SMS de recuperação processado com sucesso para webhook {webhook_event_id}")
            logger.info(f"   📊 Resumo: SMS enviado, SID {message_sid}, Log ID {sms_log.id}")
        else:
            logger.error(f"💥 [WORKER] Processamento falhou para webhook {webhook_event_id}")
            logger.error(f"   📊 Resumo: Falha registrada, Erro: {error}, Log ID {sms_log.id}")
            
    except WebhookEvent.DoesNotExist:
        logger.error(f"❌ [WORKER] Webhook event {webhook_event_id} não encontrado na base de dados")
        logger.error(f"   🔍 Possíveis causas: ID inválido, webhook deletado, problema de sincronização")
        logger.error(f"   📋 Função: schedule_sms_recovery")
    except Exception as exc:
        logger.error(f"💥 [WORKER] Erro inesperado ao processar SMS de recuperação")
        logger.error(f"   🎯 Webhook ID: {webhook_event_id}")
        logger.error(f"   ❌ Erro: {str(exc)}")
        logger.error(f"   🔧 Tipo do erro: {type(exc).__name__}")
        logger.error(f"   📋 Função: schedule_sms_recovery")
        
        # Log do traceback detalhado
        import traceback
        logger.error(f"   📋 Traceback detalhado:")
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                logger.error(f"     {line}")


@shared_task
def update_payment_status(webhook_event_id, new_status):
    """
    Atualiza o status do pagamento quando receber webhook de atualização
    """
    try:
        logger.info(f"🔄 [WORKER] Atualizando status de pagamento - Webhook ID: {webhook_event_id}")
        logger.info(f"   🎯 Novo status: {new_status}")
        
        webhook_event = WebhookEvent.objects.get(id=webhook_event_id)
        old_status = webhook_event.payment_status
        
        logger.info(f"📋 [WORKER] Dados do webhook encontrado:")
        logger.info(f"   💰 Payment ID: {webhook_event.payment_id}")
        logger.info(f"   👤 Cliente: {webhook_event.customer_name}")
        logger.info(f"   📞 Telefone: {webhook_event.customer_phone}")
        logger.info(f"   🔄 Status atual: {old_status}")
        logger.info(f"   ➡️ Mudando para: {new_status}")
        
        webhook_event.payment_status = new_status
        webhook_event.updated_at = timezone.now()
        webhook_event.save()
        
        logger.info(f"✅ [WORKER] Status atualizado com sucesso!")
        logger.info(f"   📊 Mudança: {old_status} → {new_status}")
        logger.info(f"   🕐 Timestamp: {webhook_event.updated_at}")
        
    except WebhookEvent.DoesNotExist:
        logger.error(f"❌ [WORKER] Webhook event {webhook_event_id} não encontrado para atualização")
        logger.error(f"   🎯 Status tentado: {new_status}")
        logger.error(f"   🔍 Verificar se o webhook existe na base de dados")
    except Exception as exc:
        logger.error(f"💥 [WORKER] Erro ao atualizar status do webhook {webhook_event_id}")
        logger.error(f"   ❌ Erro: {str(exc)}")
        logger.error(f"   🔧 Tipo: {type(exc).__name__}")
        logger.error(f"   🎯 Status tentado: {new_status}")
        
        # Log do traceback
        import traceback
        logger.error(f"   📋 Traceback:")
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                logger.error(f"     {line}")


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
