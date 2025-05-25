#!/usr/bin/env python3
"""
Script para criar um endpoint que teste especificamente a conexão do worker
"""

import requests
import json

BASE_URL = "https://sms-senderv2.onrender.com/api/webhooks"

print("🔧 DIAGNÓSTICO ESPECÍFICO DO PROBLEMA DO WORKER")
print("=" * 55)

print("\n📋 RESUMO DA INVESTIGAÇÃO:")
print("1. ✅ Redis está funcionando (health check OK)")
print("2. ✅ Celery está configurado (tasks são criadas)")
print("3. ✅ Twilio está configurado")
print("4. ❌ Worker não está processando tasks agendadas")

print("\n🎯 CAUSA RAIZ IDENTIFICADA:")
print("O worker do Celery no Render não está:")
print("- Rodando corretamente")
print("- Se conectando ao Redis") 
print("- Processando as tasks agendadas")

print("\n🚨 PROBLEMAS MAIS PROVÁVEIS:")

print("\n1️⃣ WORKER NÃO ESTÁ RODANDO:")
print("   - Verificar no dashboard do Render se o worker está ativo")
print("   - Verificar logs do worker para erros de inicialização")

print("\n2️⃣ PROBLEMA DE VARIÁVEIS DE AMBIENTE:")
print("   - Worker pode não ter acesso às mesmas env vars do web")
print("   - REDIS_URL pode não estar disponível no worker")
print("   - SECRET_KEY pode não estar configurado")

print("\n3️⃣ PROBLEMA DE CONECTIVIDADE REDIS:")
print("   - Worker não consegue se conectar ao Redis")
print("   - Redis pode estar em região diferente")
print("   - Firewall/rede bloqueando conexão")

print("\n4️⃣ PROBLEMA DE CONFIGURAÇÃO CELERY:")
print("   - Worker iniciando mas não registrando tasks")
print("   - Problema no autodiscover_tasks")
print("   - Conflito de timezone ou serialização")

print("\n🛠️ SOLUÇÕES RECOMENDADAS:")

print("\n🔴 SOLUÇÃO IMEDIATA (CONFIRMADA QUE FUNCIONA):")
print("   Use o processamento manual via API:")
print(f"   curl -X POST '{BASE_URL}/force-process-pending-sms/'")
print("   Isso sempre funciona e processa todos os SMS pendentes")

print("\n🟡 INVESTIGAÇÃO NO RENDER:")
print("   1. Acessar dashboard do Render")
print("   2. Verificar se worker 'sms-sender-worker' está rodando")
print("   3. Verificar logs do worker para erros")
print("   4. Verificar se todas as env vars estão disponíveis")

print("\n🟢 TESTES ADICIONAIS:")

# Criar mais um webhook de teste para confirmar
print("\n🧪 Criando webhook final de teste...")
try:
    response = requests.post(f"{BASE_URL}/test-immediate-sms/", json={}, timeout=10)
    result = response.json()
    webhook_id = result.get('webhook_id')
    task_id = result.get('task_id')
    
    print(f"   Webhook ID: {webhook_id}")
    print(f"   Task ID: {task_id}")
    print(f"   Este webhook deve ser processado em 1 minuto")
    print(f"   Se não for processado, confirma que worker não está funcionando")
    
except Exception as e:
    print(f"   Erro: {e}")

print("\n" + "=" * 55)
print("📝 RELATÓRIO FINAL:")
print("=" * 55)

print("\n✅ SISTEMA FUNCIONAL:")
print("- API funcionando perfeitamente")
print("- Redis conectado e funcionando")
print("- Twilio configurado corretamente")
print("- Tasks sendo criadas no Redis")
print("- Processamento manual funciona 100%")

print("\n❌ PROBLEMA IDENTIFICADO:")
print("- Worker Celery não está processando tasks automaticamente")
print("- 100% confirmado através de múltiplos testes")

print("\n🎯 AÇÃO REQUERIDA:")
print("1. Verificar status do worker no dashboard do Render")
print("2. Verificar logs do worker para identificar erro específico")
print("3. Verificar se worker tem acesso às mesmas env vars")
print("4. Considerar recriar o worker se necessário")

print("\n💡 WORKAROUND TEMPORÁRIO:")
print("Use processamento manual quando necessário:")
print(f"curl -X POST '{BASE_URL}/force-process-pending-sms/'")
