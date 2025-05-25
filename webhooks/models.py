import hashlib
import json
from django.db import models
from django.utils import timezone


class WebhookEvent(models.Model):
    """Model para armazenar eventos de webhook recebidos da TriboPay"""
    
    PAYMENT_STATUS_CHOICES = [
        ('waiting_payment', 'Aguardando Pagamento'),
        ('paid', 'Pago'),
        ('authorized', 'Autorizado'),
        ('refused', 'Recusado'),
        ('cancelled', 'Cancelado'),
        ('refunded', 'Reembolsado'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('pix', 'PIX'),
        ('credit_card', 'Cartão de Crédito'),
        ('debit_card', 'Cartão de Débito'),
        ('bank_slip', 'Boleto'),
    ]
    
    # Identificação única do webhook
    webhook_hash = models.CharField(max_length=64, unique=True, db_index=True)
    
    # Dados do pagamento
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES)
    amount = models.IntegerField(help_text="Valor em centavos")
    
    # Dados do cliente
    customer_phone = models.CharField(max_length=20)
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    customer_email = models.CharField(max_length=255, null=True, blank=True)
    
    # Timestamps
    payment_created_at = models.DateTimeField(null=True, blank=True)
    payment_updated_at = models.DateTimeField(null=True, blank=True)
    webhook_received_at = models.DateTimeField(auto_now_add=True)
    
    # Dados brutos do webhook
    raw_data = models.JSONField()
    
    # Status de processamento
    processed = models.BooleanField(default=False)
    sms_scheduled = models.BooleanField(default=False)
    
    # Novos campos para melhor prevenção de duplicatas
    sms_sent_count = models.PositiveIntegerField(default=0, help_text="Número de SMS enviados para este webhook")
    last_sms_sent_at = models.DateTimeField(null=True, blank=True, help_text="Último horário de envio de SMS")
    duplicate_key = models.CharField(max_length=128, db_index=True, help_text="Chave única para detectar duplicatas por telefone+valor+método")
    
    class Meta:
        ordering = ['-webhook_received_at']
        indexes = [
            models.Index(fields=['payment_method', 'payment_status']),
            models.Index(fields=['webhook_received_at']),
            models.Index(fields=['processed']),
            models.Index(fields=['customer_phone', 'payment_method', 'amount']),  # Para detectar duplicatas
            models.Index(fields=['duplicate_key']),  # Índice para chave de duplicata
            models.Index(fields=['sms_scheduled', 'payment_method', 'payment_status']),  # Para buscar PIX pendentes
        ]
    
    def save(self, *args, **kwargs):
        if not self.webhook_hash:
            # Gera hash único baseado nos dados do webhook
            # Converter datetime para string para serialização JSON
            raw_data_serializable = self._make_json_serializable(self.raw_data)
            data_string = json.dumps(raw_data_serializable, sort_keys=True)
            self.webhook_hash = hashlib.sha256(data_string.encode()).hexdigest()
        
        # Gerar chave de duplicata baseada em telefone + valor + método
        if not self.duplicate_key:
            self.duplicate_key = self._generate_duplicate_key()
            
        super().save(*args, **kwargs)
    
    def _generate_duplicate_key(self):
        """Gera chave única para detectar potenciais duplicatas baseada em telefone + valor + método"""
        # Normalizar telefone removendo caracteres especiais
        phone_normalized = ''.join(filter(str.isdigit, self.customer_phone))
        
        # Criar string única
        key_string = f"{phone_normalized}_{self.amount}_{self.payment_method}"
        
        # Gerar hash para a chave
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _make_json_serializable(self, data):
        """Converte objetos datetime para string para serialização JSON"""
        import datetime
        if isinstance(data, dict):
            return {key: self._make_json_serializable(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._make_json_serializable(item) for item in data]
        elif isinstance(data, (datetime.datetime, datetime.date)):
            return data.isoformat()
        else:
            return data
    
    def __str__(self):
        return f"Webhook {self.webhook_hash[:8]} - {self.payment_method} - {self.payment_status}"
    
    @property
    def amount_in_real(self):
        """Retorna o valor em reais"""
        return self.amount / 100
    
    def is_pix_waiting_payment(self):
        """Verifica se é um PIX aguardando pagamento"""
        return (
            self.payment_method == 'pix' and 
            self.payment_status in ['waiting', 'waiting_payment', 'pending']
        )
    
    def has_recent_sms_to_same_customer(self, hours=24):
        """
        Verifica se há SMS recentes enviados para o mesmo cliente com valor similar
        """
        from django.utils import timezone
        from datetime import timedelta
        
        time_threshold = timezone.now() - timedelta(hours=hours)
        
        # Buscar webhooks com a mesma chave de duplicata que tiveram SMS enviados recentemente
        similar_webhooks = WebhookEvent.objects.filter(
            duplicate_key=self.duplicate_key,
            sms_sent_count__gt=0,
            last_sms_sent_at__gte=time_threshold
        ).exclude(id=self.id)
        
        return similar_webhooks.exists()
    
    def get_similar_recent_webhooks(self, hours=24):
        """
        Retorna webhooks similares recentes (mesmo telefone, valor e método)
        """
        from django.utils import timezone
        from datetime import timedelta
        
        time_threshold = timezone.now() - timedelta(hours=hours)
        
        return WebhookEvent.objects.filter(
            duplicate_key=self.duplicate_key,
            webhook_received_at__gte=time_threshold
        ).exclude(id=self.id).order_by('-webhook_received_at')
    
    def can_send_sms(self, force=False):
        """
        Verifica se pode enviar SMS considerando regras de duplicata
        
        Args:
            force (bool): Se True, ignora verificações de duplicata
            
        Returns:
            tuple: (can_send: bool, reason: str)
        """
        from .logging_utils import webhook_structured_logger
        
        if force:
            webhook_structured_logger.logger.info(f"🔓 SMS forçado para webhook {self.id} - ignorando verificações de duplicata")
            return True, "Envio forçado"
        
        # Coletar dados para análise
        similar_webhooks = self.get_similar_recent_webhooks(hours=6)
        recent_sms_count = sum(1 for w in similar_webhooks if w.sms_sent_count > 0)
        
        # Calcular tempo desde último SMS se houver
        last_sms_hours_ago = None
        if self.last_sms_sent_at:
            from django.utils import timezone
            time_diff = timezone.now() - self.last_sms_sent_at
            last_sms_hours_ago = time_diff.total_seconds() / 3600
        
        # Log da análise de duplicatas
        webhook_structured_logger.log_sms_duplicate_analysis(
            webhook_id=self.id,
            phone=self.customer_phone,
            amount=self.amount or 0,
            recent_sms_count=recent_sms_count,
            similar_webhooks_count=len(similar_webhooks),
            last_sms_hours_ago=last_sms_hours_ago
        )
        
        # Verificar se já enviou SMS recentemente
        if self.sms_sent_count > 0 and self.last_sms_sent_at:
            from django.utils import timezone
            from datetime import timedelta
            
            # Não enviar mais de 1 SMS por webhook por hora
            one_hour_ago = timezone.now() - timedelta(hours=1)
            if self.last_sms_sent_at > one_hour_ago:
                reason = f"SMS já enviado para este webhook há menos de 1 hora (último: {self.last_sms_sent_at})"
                webhook_structured_logger.log_sms_duplicate_blocked(
                    webhook_id=self.id,
                    phone=self.customer_phone,
                    reason=reason,
                    similar_webhooks=len(similar_webhooks)
                )
                return False, reason
        
        # Verificar se há SMS recentes para o mesmo cliente
        if self.has_recent_sms_to_same_customer(hours=6):  # 6 horas para evitar spam
            recent_sms = [w for w in similar_webhooks if w.sms_sent_count > 0]
            if recent_sms:
                last_sms_webhook = recent_sms[0]
                reason = f"SMS já enviado para mesmo cliente/valor nas últimas 6h (webhook {last_sms_webhook.id} em {last_sms_webhook.last_sms_sent_at})"
                webhook_structured_logger.log_sms_duplicate_blocked(
                    webhook_id=self.id,
                    phone=self.customer_phone,
                    reason=reason,
                    similar_webhooks=len(similar_webhooks)
                )
                return False, reason
        
        webhook_structured_logger.logger.info(f"✅ SMS aprovado para webhook {self.id} - passou em todas as verificações anti-duplicata")
        return True, "Pode enviar SMS"
    
    def record_sms_sent(self):
        """Registra que um SMS foi enviado para este webhook"""
        from django.utils import timezone
        from .logging_utils import webhook_structured_logger
        
        self.sms_sent_count += 1
        self.last_sms_sent_at = timezone.now()
        self.save(update_fields=['sms_sent_count', 'last_sms_sent_at'])
        
        # Log do registro
        webhook_structured_logger.log_sms_sent_recorded(
            webhook_id=self.id,
            phone=self.customer_phone,
            sms_count=self.sms_sent_count
        )


class SMSLog(models.Model):
    """Model para registrar SMS enviados"""
    
    STATUS_CHOICES = [
        ('sent', 'Enviado'),
        ('failed', 'Falhou'),
        ('delivered', 'Entregue'),
        ('undelivered', 'Não Entregue'),
        ('blocked_duplicate', 'Bloqueado - Duplicata'),  # Novo status
    ]
    
    webhook_event = models.ForeignKey(
        WebhookEvent, 
        on_delete=models.CASCADE,
        related_name='sms_logs'
    )
    
    phone_number = models.CharField(max_length=20)
    message = models.TextField()
    
    # Dados do Twilio
    twilio_sid = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    error_message = models.TextField(null=True, blank=True)
    
    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Custos
    price = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    price_unit = models.CharField(max_length=5, null=True, blank=True)
    
    # Novos campos para rastreamento de duplicatas
    is_duplicate_attempt = models.BooleanField(default=False, help_text="Indica se foi uma tentativa de envio duplicado")
    duplicate_reason = models.TextField(null=True, blank=True, help_text="Motivo pelo qual foi considerado duplicata")
    related_webhook_ids = models.JSONField(null=True, blank=True, help_text="IDs de webhooks relacionados/similares")
    
    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['sent_at']),
            models.Index(fields=['phone_number', 'sent_at']),  # Para buscar SMS por telefone
            models.Index(fields=['is_duplicate_attempt']),  # Para análise de duplicatas
        ]
    
    def __str__(self):
        return f"SMS para {self.phone_number} - {self.status}"
    
    @classmethod
    def create_blocked_duplicate(cls, webhook_event, phone_number, reason, related_webhooks=None):
        """
        Cria um registro de SMS bloqueado por duplicata
        
        Args:
            webhook_event: WebhookEvent relacionado
            phone_number: Número de telefone
            reason: Motivo do bloqueio
            related_webhooks: Lista de webhooks relacionados
        """
        related_ids = [w.id for w in related_webhooks] if related_webhooks else []
        
        return cls.objects.create(
            webhook_event=webhook_event,
            phone_number=phone_number,
            message=f"SMS bloqueado - duplicata detectada: {reason}",
            status='blocked_duplicate',
            is_duplicate_attempt=True,
            duplicate_reason=reason,
            related_webhook_ids=related_ids,
            error_message=f"Envio bloqueado para prevenir duplicata: {reason}"
        )
