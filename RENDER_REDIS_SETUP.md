# 🔴 Redis Configuration Guide for Render

## Opções de Redis para Render

### Opção 1: Redis Internal do Render (Recomendado para produção)

1. **Adicionar Redis Service no Dashboard Render:**
   - Acesse seu Dashboard no Render
   - Clique em "New +" → "Redis"
   - Escolha um nome (ex: `sms-sender-redis`)
   - Selecione o plano (Free tier disponível)
   - Clique em "Create Redis"

2. **Configurar REDIS_URL no seu Web Service:**
   - Vá para o seu web service `sms-senderv2`
   - Na aba "Environment"
   - Adicione a variável:
     ```
     REDIS_URL = redis://red-xxxxxxxxxxxxx:6379
     ```
   - O valor exato será fornecido pelo Render após criar o Redis service

### Opção 2: Redis External (RedisLabs/Upstash)

#### RedisLabs Cloud (Gratuito até 30MB):
1. Acesse https://redislabs.com/
2. Crie uma conta gratuita
3. Crie um database Redis
4. Use a URL fornecida:
   ```
   REDIS_URL = redis://default:senha@redis-xxxxx.redislabs.com:xxxxx
   ```

#### Upstash (Serverless Redis):
1. Acesse https://upstash.com/
2. Crie uma conta
3. Crie um Redis database
4. Use a URL fornecida:
   ```
   REDIS_URL = rediss://default:senha@us1-xxxxx.upstash.io:xxxxx
   ```

### Opção 3: Redis Local (Apenas para desenvolvimento)

```bash
# Para desenvolvimento local
REDIS_URL = redis://localhost:6379
```

## 🔧 Configuração no Render (Recomendada)

### Passo 1: Criar Redis Service

1. **Dashboard Render** → **New +** → **Redis**
2. **Name**: `sms-sender-redis` 
3. **Plan**: Starter (Free) ou Professional
4. **Region**: Same as your web service
5. **Clique em "Create Redis"**

### Passo 2: Obter Redis URL

Após criar o Redis service, você verá:
```
Internal Redis URL: redis://red-xxxxxxxxxxxxx:6379
External Redis URL: rediss://red-xxxxxxxxxxxxx.oregon-postgres.render.com:25061
```

**Use a Internal Redis URL** (mais rápida e segura).

### Passo 3: Configurar Environment Variable

1. Vá para seu web service `sms-senderv2`
2. **Environment** tab
3. Adicione:
   ```
   REDIS_URL = redis://red-xxxxxxxxxxxxx:6379
   ```

### Passo 4: Deploy

Após adicionar a variável, o Render fará redeploy automático.

## 🧪 Testar Configuração

### Via API Health Check:
```bash
curl https://sms-senderv2.onrender.com/api/webhooks/health/
```

Deve retornar:
```json
{
  "cache": "connected",
  "redis_url_configured": true,
  "cache_backend_type": "django_redis.cache.RedisCache"
}
```

### Via Webhook com PIX:
```bash
curl -X POST "https://sms-senderv2.onrender.com/api/webhooks/tribopay/" \
  -H "Content-Type: application/json" \
  -d '{
    "token": "webhook_token_123",
    "event": "payment.created", 
    "status": "waiting",
    "method": "pix",
    "customer": {
      "name": "João Silva",
      "phone_number": "17992666990"
    },
    "transaction": {
      "id": "pay_123456789",
      "amount": 5000
    }
  }'
```

## 📋 Troubleshooting

### Problema: "Redis connection failed"
**Solução**: Verificar se REDIS_URL está correta

### Problema: "AbstractConnection.__init__() got an unexpected keyword argument"
**Solução**: Verificar versão django-redis (deve ser 5.4.0+)

### Problema: "Connection timeout"
**Solução**: Usar Internal Redis URL ao invés da External

## 🎯 URL Recomendada para Render

Para seu caso específico, recomendo:

1. **Criar Redis Service no Render**
2. **Usar Internal Redis URL**: `redis://red-xxxxxxxxxxxxx:6379`
3. **Configurar no Environment Variables**

Isso garantirá:
- ✅ Baixa latência (mesma rede interna)
- ✅ Alta disponibilidade 
- ✅ Backups automáticos
- ✅ Monitoramento integrado
- ✅ Free tier disponível

## 🚀 Próximos Passos

1. Criar Redis service no Render
2. Copiar Internal Redis URL
3. Adicionar `REDIS_URL` no Environment
4. Testar com health check
5. Testar webhook com PIX
6. Verificar SMS scheduling

## 📞 Suporte

Se precisar de ajuda:
1. Verificar logs do Render
2. Usar endpoint `/api/webhooks/health/` para diagnóstico
3. Consultar documentação oficial do Render
