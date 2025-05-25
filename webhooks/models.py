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
    
    class Meta:
        ordering = ['-webhook_received_at']
        indexes = [
            models.Index(fields=['payment_method', 'payment_status']),
            models.Index(fields=['webhook_received_at']),
            models.Index(fields=['processed']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.webhook_hash:
            # Gera hash único baseado nos dados do webhook
            # Converter datetime para string para serialização JSON
            raw_data_serializable = self._make_json_serializable(self.raw_data)
            data_string = json.dumps(raw_data_serializable, sort_keys=True)
            self.webhook_hash = hashlib.sha256(data_string.encode()).hexdigest()
        super().save(*args, **kwargs)
    
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


class SMSLog(models.Model):
    """Model para registrar SMS enviados"""
    
    STATUS_CHOICES = [
        ('sent', 'Enviado'),
        ('failed', 'Falhou'),
        ('delivered', 'Entregue'),
        ('undelivered', 'Não Entregue'),
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
    
    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['sent_at']),
        ]
    
    def __str__(self):
        return f"SMS para {self.phone_number} - {self.status}"
