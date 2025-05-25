#!/usr/bin/env python
"""
Teste para verificar se o serializer GhostPay funciona sem o campo netValue
"""
import os
import sys
import django

# Configurar Django
sys.path.append('/home/lkdev/workspace/projects/Marketing-Digital-Projects/SMS-Sender')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms_sender.settings')
django.setup()

from webhooks.serializers import GhostPayWebhookSerializer

# Payload real da GhostPay (sem netValue)
payload = {
    "paymentId": "123e4567-e89b-12d3-a456-426614174000",
    "status": "APPROVED",
    "paymentMethod": "PIX",
    "totalValue": 1000,
    "customer": {
        "id": "123e4567-e89b-12d3-a456-426614174004",
        "name": "João Silva",
        "email": "joao.silva@gmail.com",
        "phone": "11987654321",
        "cpf": "01234567890",
        "cep": "11111000",
        "complement": "",
        "number": "",
        "street": "",
        "city": "",
        "state": "",
        "district": ""
    },
    "offer": {
        "id": "123e4567-e89b-12d3-a456-426614174001",
        "price": 100.5,
        "title": "Titulo da oferta"
    },
    "product": {
        "id": "123e4567-e89b-12d3-a456-426614174004",
        "name": "Produto Teste",
        "typeProduct": "DIGITAL"
    },
    "createdAt": "2025-05-25T15:39:47.114Z",
    "updatedAt": "2025-05-25T15:39:47.114Z",
    "approvedAt": "2025-05-25T15:39:47.114Z",
    "refundedAt": None,
    "chargebackAt": None,
    "rejectedAt": None
}

print("🧪 Testando serializer GhostPay...")
print(f"📦 Payload: {payload}")

# Testar serializer
serializer = GhostPayWebhookSerializer(data=payload)

if serializer.is_valid():
    print("✅ Serializer é válido!")
    
    # Testar conversão para WebhookEvent
    webhook_data = serializer.to_webhook_event_data()
    print(f"📊 Dados convertidos: {webhook_data}")
    
    # Verificar campos importantes
    print(f"🆔 Payment ID: {webhook_data['payment_id']}")
    print(f"💳 Payment Method: {webhook_data['payment_method']}")
    print(f"📊 Payment Status: {webhook_data['payment_status']}")
    print(f"💰 Amount: {webhook_data['amount']}")
    print(f"📞 Customer Phone: {webhook_data['customer_phone']}")
    
else:
    print("❌ Serializer inválido!")
    print(f"🚨 Erros: {serializer.errors}")
