# 🛠️ Exemplos Práticos da API SMS-Sender

## 🌐 **cURL Examples**

### Verificação do Sistema
```bash
# Health Check
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/health/" \
  -H "Accept: application/json"

# Status Twilio
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/twilio-config-check/"

# Status SMS Scheduler
curl -X GET "https://sms-senderv2.onrender.com/api/webhooks/sms-scheduler-status/"
```

### Webhooks de Pagamento
```bash
# GhostPay Webhook (PIX Pendente)
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/ghostpay/" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "pay_' $(date +%s) '",
    "status": "PENDING",
    "payment_method": "PIX",
    "amount": 150.00,
    "customer": {
      "name": "Maria Silva",
      "phone": "+5511987654321",
      "email": "maria@email.com"
    },
    "created_at": "' $(date -u +%Y-%m-%dT%H:%M:%SZ) '"
  }'

# TriboPay Webhook
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/tribopay/" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction": {
      "id": "trans_' $(date +%s) '",
      "status": "waiting_payment",
      "payment_method": "pix",
      "amount": 89.90
    },
    "customer": {
      "name": "Pedro Santos",
      "phone": "+5511123456789"
    }
  }'
```

### Testes e Debug
```bash
# Teste de SMS imediato (1 minuto)
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/test-immediate-sms/" \
  -H "Content-Type: application/json" \
  -d '{}'

# Teste de Celery Worker
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/test-celery-task/" \
  -H "Content-Type: application/json" \
  -d '{}'

# Processamento manual de SMS
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/force-process-pending-sms/" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 🐍 **Python Examples**

### Usando requests
```python
import requests
import json
from datetime import datetime

# Base URL
BASE_URL = "https://sms-senderv2.onrender.com/api/webhooks"

# Health Check
def check_health():
    response = requests.get(f"{BASE_URL}/health/")
    return response.json()

# Enviar Webhook GhostPay
def send_ghostpay_webhook(payment_id, amount, customer_name, customer_phone):
    payload = {
        "id": payment_id,
        "status": "PENDING",
        "payment_method": "PIX",
        "amount": amount,
        "customer": {
            "name": customer_name,
            "phone": customer_phone
        },
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    response = requests.post(
        f"{BASE_URL}/ghostpay/",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    return response.json()

# Processar SMS pendentes
def process_pending_sms():
    response = requests.post(
        f"{BASE_URL}/force-process-pending-sms/",
        json={},
        headers={"Content-Type": "application/json"}
    )
    return response.json()

# Exemplo de uso
if __name__ == "__main__":
    # 1. Verificar saúde
    health = check_health()
    print(f"Sistema: {health.get('status')}")
    
    # 2. Enviar webhook
    result = send_ghostpay_webhook(
        payment_id=f"pay_{int(datetime.now().timestamp())}",
        amount=99.90,
        customer_name="João da Silva",
        customer_phone="+5511999888777"
    )
    print(f"Webhook: {result}")
    
    # 3. Processar SMS (após 10 minutos ou forçar)
    import time
    time.sleep(2)  # Aguardar um pouco
    sms_result = process_pending_sms()
    print(f"SMS: {sms_result}")
```

### Monitoramento Automático
```python
import requests
import time
from datetime import datetime

class SMSSenderMonitor:
    def __init__(self):
        self.base_url = "https://sms-senderv2.onrender.com/api/webhooks"
    
    def health_check(self):
        try:
            response = requests.get(f"{self.base_url}/health/", timeout=10)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_pending_sms(self):
        try:
            response = requests.get(f"{self.base_url}/pending-sms/", timeout=10)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def force_process_sms(self):
        try:
            response = requests.post(
                f"{self.base_url}/force-process-pending-sms/",
                json={},
                timeout=30
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def monitor_loop(self, interval=300):  # 5 minutos
        """Monitor contínuo do sistema"""
        while True:
            print(f"\n[{datetime.now()}] Verificando sistema...")
            
            # Health check
            health = self.health_check()
            print(f"Status: {health.get('status', 'unknown')}")
            
            # SMS pendentes
            pending = self.get_pending_sms()
            if 'pending_webhooks' in pending:
                count = pending['pending_webhooks']
                print(f"SMS pendentes: {count}")
                
                if count > 0:
                    print("Processando SMS pendentes...")
                    result = self.force_process_sms()
                    print(f"Resultado: {result}")
            
            time.sleep(interval)

# Uso
monitor = SMSSenderMonitor()
# monitor.monitor_loop()  # Para monitoramento contínuo
```

---

## 📱 **JavaScript/Node.js Examples**

### Usando fetch (Browser/Node.js)
```javascript
const BASE_URL = 'https://sms-senderv2.onrender.com/api/webhooks';

// Health Check
async function checkHealth() {
    try {
        const response = await fetch(`${BASE_URL}/health/`);
        const data = await response.json();
        console.log('Health Status:', data);
        return data;
    } catch (error) {
        console.error('Health check failed:', error);
    }
}

// Enviar Webhook GhostPay
async function sendGhostPayWebhook(paymentData) {
    try {
        const response = await fetch(`${BASE_URL}/ghostpay/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id: paymentData.id,
                status: 'PENDING',
                payment_method: 'PIX',
                amount: paymentData.amount,
                customer: {
                    name: paymentData.customerName,
                    phone: paymentData.customerPhone
                },
                created_at: new Date().toISOString()
            })
        });
        
        const result = await response.json();
        console.log('Webhook Result:', result);
        return result;
    } catch (error) {
        console.error('Webhook failed:', error);
    }
}

// Processar SMS Pendentes
async function processPendingSMS() {
    try {
        const response = await fetch(`${BASE_URL}/force-process-pending-sms/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        });
        
        const result = await response.json();
        console.log('SMS Processing Result:', result);
        return result;
    } catch (error) {
        console.error('SMS processing failed:', error);
    }
}

// Exemplo de uso
async function runExample() {
    // 1. Verificar saúde
    await checkHealth();
    
    // 2. Enviar webhook
    await sendGhostPayWebhook({
        id: `pay_${Date.now()}`,
        amount: 129.90,
        customerName: 'Ana Costa',
        customerPhone: '+5511666555444'
    });
    
    // 3. Aguardar e processar SMS
    setTimeout(async () => {
        await processPendingSMS();
    }, 2000);
}

// Executar exemplo
runExample();
```

### Webhook Listener (Express.js)
```javascript
const express = require('express');
const axios = require('axios');
const app = express();

app.use(express.json());

// Simulador de Gateway de Pagamento
app.post('/payment-webhook', async (req, res) => {
    const { payment_id, status, amount, customer } = req.body;
    
    // Repassar para SMS-Sender se for PIX pendente
    if (status === 'PENDING' && req.body.payment_method === 'PIX') {
        try {
            const response = await axios.post(
                'https://sms-senderv2.onrender.com/api/webhooks/ghostpay/',
                {
                    id: payment_id,
                    status: status,
                    payment_method: 'PIX',
                    amount: amount,
                    customer: customer,
                    created_at: new Date().toISOString()
                }
            );
            
            console.log('SMS-Sender Response:', response.data);
        } catch (error) {
            console.error('Failed to notify SMS-Sender:', error.message);
        }
    }
    
    res.json({ status: 'received' });
});

app.listen(3000, () => {
    console.log('Webhook listener running on port 3000');
});
```

---

## 🔧 **Postman Collection**

### Importar no Postman
```json
{
    "info": {
        "name": "SMS-Sender API",
        "description": "API completa do SMS-Sender"
    },
    "variable": [
        {
            "key": "base_url",
            "value": "https://sms-senderv2.onrender.com/api/webhooks"
        }
    ],
    "item": [
        {
            "name": "Health Check",
            "request": {
                "method": "GET",
                "header": [],
                "url": "{{base_url}}/health/"
            }
        },
        {
            "name": "GhostPay Webhook",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": "{\n  \"id\": \"pay_{{$timestamp}}\",\n  \"status\": \"PENDING\",\n  \"payment_method\": \"PIX\",\n  \"amount\": 99.90,\n  \"customer\": {\n    \"name\": \"Cliente Teste\",\n    \"phone\": \"+5511999999999\"\n  }\n}"
                },
                "url": "{{base_url}}/ghostpay/"
            }
        },
        {
            "name": "Process Pending SMS",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": "{}"
                },
                "url": "{{base_url}}/force-process-pending-sms/"
            }
        }
    ]
}
```

---

## 🔄 **Scripts de Automação**

### Bash Script - Teste Completo
```bash
#!/bin/bash

BASE_URL="https://sms-senderv2.onrender.com/api/webhooks"
TIMESTAMP=$(date +%s)

echo "🚀 Iniciando teste completo do SMS-Sender..."

# 1. Health Check
echo "1️⃣ Verificando saúde do sistema..."
HEALTH=$(curl -s "$BASE_URL/health/")
echo "✅ Health: $HEALTH"

# 2. Criar webhook
echo "2️⃣ Criando webhook de teste..."
WEBHOOK_RESULT=$(curl -s -X POST "$BASE_URL/test-immediate-sms/" \
  -H "Content-Type: application/json" \
  -d '{}')
echo "✅ Webhook: $WEBHOOK_RESULT"

# 3. Aguardar
echo "3️⃣ Aguardando 70 segundos..."
sleep 70

# 4. Processar SMS
echo "4️⃣ Processando SMS pendentes..."
SMS_RESULT=$(curl -s -X POST "$BASE_URL/force-process-pending-sms/" \
  -H "Content-Type: application/json" \
  -d '{}')
echo "✅ SMS: $SMS_RESULT"

echo "🎉 Teste completo finalizado!"
```

### PowerShell Script (Windows)
```powershell
$BaseUrl = "https://sms-senderv2.onrender.com/api/webhooks"
$Headers = @{"Content-Type" = "application/json"}

Write-Host "🚀 Testando SMS-Sender API..." -ForegroundColor Green

# Health Check
$Health = Invoke-RestMethod -Uri "$BaseUrl/health/" -Method Get
Write-Host "✅ Health: $($Health.status)" -ForegroundColor Green

# Webhook de teste
$WebhookBody = @{
    id = "pay_$(Get-Date -UFormat %s)"
    status = "PENDING"
    payment_method = "PIX"
    amount = 99.90
    customer = @{
        name = "Teste PowerShell"
        phone = "+5511999999999"
    }
} | ConvertTo-Json

$WebhookResult = Invoke-RestMethod -Uri "$BaseUrl/ghostpay/" -Method Post -Body $WebhookBody -Headers $Headers
Write-Host "✅ Webhook criado: $($WebhookResult.status)" -ForegroundColor Green

# Processar SMS
Start-Sleep -Seconds 2
$SmsResult = Invoke-RestMethod -Uri "$BaseUrl/force-process-pending-sms/" -Method Post -Body "{}" -Headers $Headers
Write-Host "✅ SMS processados: $($SmsResult.sms_sent)" -ForegroundColor Green
```

---

## 📊 **Monitoring Dashboard (HTML)**

```html
<!DOCTYPE html>
<html>
<head>
    <title>SMS-Sender Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .healthy { background-color: #d4edda; color: #155724; }
        .error { background-color: #f8d7da; color: #721c24; }
        button { padding: 10px 20px; margin: 5px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>📱 SMS-Sender Dashboard</h1>
    
    <div id="status" class="status">Carregando...</div>
    
    <button onclick="checkHealth()">🔍 Verificar Saúde</button>
    <button onclick="testSMS()">📱 Teste SMS</button>
    <button onclick="processSMS()">🔄 Processar SMS</button>
    
    <div id="logs" style="margin-top: 20px; background: #f8f9fa; padding: 15px; border-radius: 5px; max-height: 400px; overflow-y: auto;"></div>

    <script>
        const BASE_URL = 'https://sms-senderv2.onrender.com/api/webhooks';
        
        function log(message) {
            const logs = document.getElementById('logs');
            logs.innerHTML += `<div>${new Date().toLocaleTimeString()}: ${message}</div>`;
            logs.scrollTop = logs.scrollHeight;
        }
        
        async function checkHealth() {
            try {
                log('Verificando saúde do sistema...');
                const response = await fetch(`${BASE_URL}/health/`);
                const data = await response.json();
                
                const statusDiv = document.getElementById('status');
                if (data.status === 'healthy') {
                    statusDiv.className = 'status healthy';
                    statusDiv.innerHTML = `✅ Sistema Saudável - DB: ${data.database}, Cache: ${data.cache}`;
                } else {
                    statusDiv.className = 'status error';
                    statusDiv.innerHTML = `❌ Sistema com Problemas`;
                }
                
                log(`Status: ${data.status}`);
            } catch (error) {
                log(`Erro: ${error.message}`);
            }
        }
        
        async function testSMS() {
            try {
                log('Criando teste de SMS...');
                const response = await fetch(`${BASE_URL}/test-immediate-sms/`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: '{}'
                });
                const data = await response.json();
                log(`SMS agendado: Task ID ${data.task_id}`);
            } catch (error) {
                log(`Erro: ${error.message}`);
            }
        }
        
        async function processSMS() {
            try {
                log('Processando SMS pendentes...');
                const response = await fetch(`${BASE_URL}/force-process-pending-sms/`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: '{}'
                });
                const data = await response.json();
                log(`SMS enviados: ${data.sms_sent}, Bloqueados: ${data.sms_blocked}`);
            } catch (error) {
                log(`Erro: ${error.message}`);
            }
        }
        
        // Auto verificar saúde a cada 30 segundos
        checkHealth();
        setInterval(checkHealth, 30000);
    </script>
</body>
</html>
```

Salve este arquivo como `dashboard.html` e abra no navegador para um dashboard de monitoramento em tempo real!

---

**🎯 Estes exemplos cobrem todos os cenários de uso da API SMS-Sender em diferentes linguagens e ferramentas.**
