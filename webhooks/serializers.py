from rest_framework import serializers
from .models import WebhookEvent, SMSLog


class WebhookEventSerializer(serializers.ModelSerializer):
    """Serializer para eventos de webhook da TriboPay"""
    
    amount_in_real = serializers.ReadOnlyField()
    
    class Meta:
        model = WebhookEvent
        fields = [
            'id', 'webhook_hash', 'payment_id', 'payment_method', 
            'payment_status', 'amount', 'amount_in_real',
            'customer_phone', 'customer_name', 'customer_email',
            'payment_created_at', 'payment_updated_at', 'webhook_received_at',
            'processed', 'sms_scheduled'
        ]
        read_only_fields = ['webhook_hash', 'webhook_received_at', 'amount_in_real']


class TribePayRealWebhookSerializer(serializers.Serializer):
    """Serializer para o formato real da TriboPay baseado nos dados capturados"""
    
    # Campos do nível raiz
    token = serializers.CharField(required=False)
    event = serializers.CharField(required=False)
    status = serializers.CharField(max_length=50)
    method = serializers.CharField(max_length=20)
    created_at = serializers.DateTimeField(required=False)
    paid_at = serializers.DateTimeField(required=False, allow_null=True)
    refund_at = serializers.DateTimeField(required=False, allow_null=True)
    platform = serializers.CharField(required=False)
    
    # Dados do cliente
    customer = serializers.DictField()
    
    # Dados da transação
    transaction = serializers.DictField()
    
    # Campos adicionais opcionais
    affiliate = serializers.DictField(required=False)
    offer = serializers.DictField(required=False)
    items = serializers.ListField(required=False)
    tracking = serializers.DictField(required=False)
    ip = serializers.CharField(required=False, allow_null=True)
    fbp = serializers.CharField(required=False, allow_null=True)
    fbc = serializers.CharField(required=False, allow_null=True)
    
    def validate_customer(self, value):
        """Valida se os dados do cliente contêm telefone"""
        phone_fields = ['phone', 'phone_number']
        if not any(field in value for field in phone_fields):
            raise serializers.ValidationError(
                "Campo 'phone' ou 'phone_number' é obrigatório nos dados do cliente"
            )
        return value
    
    def validate_transaction(self, value):
        """Valida se os dados da transação contêm ID e amount"""
        if 'id' not in value:
            raise serializers.ValidationError(
                "Campo 'id' é obrigatório nos dados da transação"
            )
        if 'amount' not in value:
            raise serializers.ValidationError(
                "Campo 'amount' é obrigatório nos dados da transação"
            )
        return value
    
    def to_webhook_event_data(self):
        """Converte dados validados para formato do WebhookEvent"""
        validated_data = self.validated_data
        customer_data = validated_data.get('customer', {})
        transaction_data = validated_data.get('transaction', {})
        
        # Extrair telefone (priorizar phone_number, depois phone)
        customer_phone = (
            customer_data.get('phone_number') or 
            customer_data.get('phone') or 
            ''
        )
        
        # Converter dados para formato serializável
        raw_data = dict(validated_data)
        
        # Converter datetime para string se necessário
        for key, value in raw_data.items():
            if hasattr(value, 'isoformat'):  # datetime objects
                raw_data[key] = value.isoformat()
        
        # Gerar hash único para evitar duplicatas
        import hashlib
        import json
        data_str = json.dumps(raw_data, sort_keys=True, default=str)
        webhook_hash = hashlib.sha256(data_str.encode()).hexdigest()
        
        return {
            'webhook_hash': webhook_hash,
            'payment_id': transaction_data['id'],
            'payment_method': validated_data['method'],
            'payment_status': validated_data['status'],
            'amount': int(transaction_data['amount']),
            'customer_phone': customer_phone,
            'customer_name': customer_data.get('name'),
            'customer_email': customer_data.get('email'),
            'payment_created_at': validated_data.get('created_at'),
            'payment_updated_at': validated_data.get('paid_at'),  # Usar paid_at como updated_at
            'raw_data': raw_data,
        }


class TribePayWebhookSerializer(serializers.Serializer):
    """Serializer para processar dados recebidos da TriboPay"""
    
    payment_method = serializers.CharField(max_length=20)
    payment_status = serializers.CharField(max_length=20)
    amount = serializers.IntegerField()
    created_at = serializers.DateTimeField(required=False)
    updated_at = serializers.DateTimeField(required=False)
    
    # Dados do cliente aninhados
    customer = serializers.DictField()
    
    # ID do pagamento (pode variar conforme a API)
    id = serializers.CharField(max_length=100, required=False)
    payment_id = serializers.CharField(max_length=100, required=False)
    
    def validate_customer(self, value):
        """Valida se os dados do cliente contêm phone_number"""
        if 'phone_number' not in value:
            raise serializers.ValidationError(
                "Campo 'phone_number' é obrigatório nos dados do cliente"
            )
        return value
    
    def to_webhook_event_data(self):
        """Converte dados validados para formato do WebhookEvent"""
        validated_data = self.validated_data
        customer_data = validated_data.get('customer', {})
        
        # Converter dados para formato serializável
        raw_data = dict(validated_data)
        
        # Converter datetime para string se necessário
        for key, value in raw_data.items():
            if hasattr(value, 'isoformat'):  # datetime objects
                raw_data[key] = value.isoformat()
        
        return {
            'payment_id': (
                validated_data.get('id') or 
                validated_data.get('payment_id')
            ),
            'payment_method': validated_data['payment_method'],
            'payment_status': validated_data['payment_status'],
            'amount': validated_data['amount'],
            'customer_phone': customer_data['phone_number'],
            'customer_name': customer_data.get('name'),
            'customer_email': customer_data.get('email'),
            'payment_created_at': validated_data.get('created_at'),
            'payment_updated_at': validated_data.get('updated_at'),
            'raw_data': raw_data,
        }


class SMSLogSerializer(serializers.ModelSerializer):
    """Serializer para logs de SMS"""
    
    webhook_event_id = serializers.ReadOnlyField(source='webhook_event.id')
    
    class Meta:
        model = SMSLog
        fields = [
            'id', 'webhook_event_id', 'phone_number', 'message',
            'twilio_sid', 'status', 'error_message',
            'sent_at', 'delivered_at', 'price', 'price_unit'
        ]
        read_only_fields = ['sent_at']
