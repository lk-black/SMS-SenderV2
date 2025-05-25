# 🚨 Diagnóstico do Problema: Celery Worker não está processando SMS automaticamente

**Data:** 25 de Maio de 2025  
**Status:** 🔍 PROBLEMA IDENTIFICADO - Worker não funcional

---

## ❌ **Resumo do Problema**

O **worker do Celery no Render não está processando automaticamente** as tasks agendadas de SMS, mesmo com todas as configurações corretas.

### 🔍 **Evidências Coletadas**

| ✅ Funcionando | ❌ Não Funcionando |
|---|---|
| API REST funcionando perfeitamente | Worker não processa tasks agendadas |
| Redis conectado e disponível | SMS ficam pendentes indefinidamente |
| Twilio configurado corretamente | Tasks criadas mas não executadas |
| Health check retorna "healthy" | Webhooks ficam `processed: false` |
| Tasks são criadas (task IDs gerados) | Delay de 10 minutos nunca é respeitado |
| Processamento manual funciona 100% | Worker não responde a comandos |

---

## 🧪 **Testes Realizados**

### 1. **Teste de Health Check**
```bash
curl https://sms-senderv2.onrender.com/api/webhooks/health/
```
**Resultado:** ✅ Sistema saudável, Redis conectado, Celery disponível

### 2. **Teste de Task Celery**
```bash
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/test-celery-task/
```
**Resultado:** ✅ Task criada com sucesso (Task ID gerado), mas ❌ nunca processada

### 3. **Teste de SMS Imediato**
```bash
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/test-immediate-sms/
```
**Resultado:** ✅ Webhook criado, SMS agendado para 1 minuto, mas ❌ nunca enviado automaticamente

### 4. **Teste de Processamento Manual**
```bash
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/force-process-pending-sms/
```
**Resultado:** ✅ Funciona perfeitamente, processa todos os SMS pendentes

---

## 🎯 **Causa Raiz Identificada**

O **worker Celery no Render** não está:

1. **Rodando corretamente** - Worker pode estar crashando silenciosamente
2. **Conectando ao Redis** - Problema de conectividade ou variáveis de ambiente
3. **Processando tasks** - Worker roda mas não pega tasks da fila

---

## 🔧 **Configuração Atual (Correta)**

### render.yaml
```yaml
- type: worker
  name: sms-sender-worker
  env: python
  plan: free
  buildCommand: "./build.sh"
  startCommand: "celery -A sms_sender worker --loglevel=info"
```

### Celery Settings (Corretas)
```python
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
```

---

## 🛠️ **Soluções Propostas**

### 🔴 **Solução Imediata (Workaround)**
Use o processamento manual sempre que necessário:

```bash
# Verificar SMS pendentes
curl https://sms-senderv2.onrender.com/api/webhooks/pending-sms/

# Processar manualmente
curl -X POST https://sms-senderv2.onrender.com/api/webhooks/force-process-pending-sms/
```

**Vantagem:** Funciona 100% das vezes  
**Desvantagem:** Requer intervenção manual

### 🟡 **Investigação no Dashboard do Render**

**AÇÕES PRIORITÁRIAS:**

1. **Verificar Status do Worker**
   - Acessar dashboard do Render
   - Verificar se `sms-sender-worker` está "Running"
   - Se não estiver, investigar por quê

2. **Verificar Logs do Worker**
   - Abrir logs do `sms-sender-worker`
   - Procurar por erros de:
     - Conexão com Redis
     - Importação de módulos
     - Variáveis de ambiente
     - Crashes ou timeouts

3. **Verificar Variáveis de Ambiente**
   - Confirmar que o worker tem acesso a:
     - `REDIS_URL`
     - `SECRET_KEY`
     - `DATABASE_URL`
     - `TWILIO_*` (se necessário)

### 🟢 **Soluções Técnicas**

#### Opção 1: Recriar Worker
```yaml
# Deletar e recriar o worker no render.yaml
- type: worker
  name: sms-sender-worker-v2
  env: python
  plan: free
  buildCommand: "./build.sh"
  startCommand: "celery -A sms_sender worker --loglevel=debug"
```

#### Opção 2: Worker com Logs Verbosos
```yaml
startCommand: "celery -A sms_sender worker --loglevel=debug --concurrency=1"
```

#### Opção 3: Verificação de Conectividade
Adicionar endpoint para testar conectividade do worker:

```python
@shared_task
def test_worker_connectivity():
    """Task para testar se worker está funcionando"""
    from django.core.cache import cache
    cache.set('worker_test', f'OK-{timezone.now()}', 60)
    return f"Worker funcionando em {timezone.now()}"
```

---

## 📊 **Evidências Coletadas**

### Webhooks com Problema
| ID | Payment ID | Processed | SMS Scheduled | Status |
|---|---|---|---|---|
| 12 | immediate_test_1748201892 | ❌ False | ✅ True | Pendente há 30+ minutos |
| 11 | d8951e41-348c-46d5-91e0... | ✅ True | ✅ True | Processado manualmente |
| 10 | d0f65817-a2dd-4685-8465... | ✅ True | ✅ True | Processado manualmente |

### Tasks Celery Criadas mas não Processadas
```
Task ID: 6cacb445-6208-47e4-9cd3-6542109a6c1f - PENDING (nunca executada)
Task ID: d7796952-af6d-4f92-91ab-805d2e103c48 - PENDING (nunca executada)
Task ID: a362a732-97c7-460f-a909-b694584b6873 - PENDING (nunca executada)
```

---

## 🚨 **Próximos Passos Críticos**

### 1. **VERIFICAÇÃO IMEDIATA** (Você deve fazer)
- [ ] Acessar dashboard do Render
- [ ] Verificar se worker `sms-sender-worker` está rodando
- [ ] Verificar logs do worker para erros
- [ ] Confirmar variáveis de ambiente do worker

### 2. **TESTE DE CONECTIVIDADE**
- [ ] Verificar se worker consegue se conectar ao Redis
- [ ] Testar se worker consegue importar módulos Django
- [ ] Verificar se não há conflitos de dependências

### 3. **SOLUÇÃO TÉCNICA**
- [ ] Recriar worker se necessário
- [ ] Aumentar loglevel para debug
- [ ] Considerar usar worker com concurrency=1

---

## 💡 **Recomendação Final**

**AÇÃO IMEDIATA:** Verificar logs do worker no dashboard do Render. Muito provavelmente você encontrará:

1. **Worker crashando** por falta de variável de ambiente
2. **Worker não conectando** ao Redis
3. **Worker rodando** mas com erro de importação
4. **Worker não iniciando** por problema de build

O processamento manual funciona perfeitamente, então o problema é 100% específico do worker, não da aplicação.

---

**Status:** 🔍 Investigação necessária no dashboard do Render  
**Prioridade:** 🔴 Alta (impacta funcionamento automático)  
**Workaround:** ✅ Disponível (processamento manual funciona)
