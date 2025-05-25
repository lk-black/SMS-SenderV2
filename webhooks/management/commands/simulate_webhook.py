import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.test import Client


class Command(BaseCommand):
    """
    Command para simular recebimento de webhook da TriboPay
    """
    help = 'Simula o recebimento de um webhook da TriboPay'

    def add_arguments(self, parser):
        parser.add_argument(
            '--phone',
            type=str,
            help='Número de telefone (ex: +5511999999999)',
            required=True
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=['waiting_payment', 'paid', 'refused', 'cancelled'],
            help='Status do pagamento',
            default='waiting_payment'
        )
        parser.add_argument(
            '--amount',
            type=int,
            help='Valor em centavos',
            default=5000
        )
        parser.add_argument(
            '--method',
            type=str,
            choices=['pix', 'credit_card', 'debit_card', 'bank_slip'],
            help='Método de pagamento',
            default='pix'
        )
        parser.add_argument(
            '--name',
            type=str,
            help='Nome do cliente',
            default='Cliente Simulado'
        )

    def handle(self, *args, **options):
        client = Client()
        
        webhook_data = {
            "id": f"payment_{int(timezone.now().timestamp())}",
            "payment_method": options['method'],
            "payment_status": options['status'],
            "amount": options['amount'],
            "created_at": timezone.now().isoformat(),
            "updated_at": timezone.now().isoformat(),
            "customer": {
                "phone_number": options['phone'],
                "name": options['name'],
                "email": "simulado@email.com"
            }
        }
        
        self.stdout.write('🚀 Simulando webhook da TriboPay...')
        self.stdout.write(f'📱 Telefone: {options["phone"]}')
        self.stdout.write(f'💰 Valor: R$ {options["amount"]/100:.2f}')
        self.stdout.write(f'💳 Método: {options["method"]}')
        self.stdout.write(f'📊 Status: {options["status"]}')
        self.stdout.write(f'👤 Cliente: {options["name"]}')
        
        self.stdout.write('\n📤 Enviando webhook...')
        
        response = client.post(
            '/api/webhooks/tribopay/',
            data=json.dumps(webhook_data),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            self.stdout.write(
                self.style.SUCCESS('✅ Webhook processado com sucesso!')
            )
            
            if options['method'] == 'pix' and options['status'] == 'waiting_payment':
                self.stdout.write(
                    self.style.WARNING('⏱️  SMS de recuperação agendado para 10 minutos')
                )
        else:
            self.stdout.write(
                self.style.ERROR(f'❌ Erro no webhook: {response.status_code}')
            )
            try:
                error_data = response.json()
                self.stdout.write(f'Detalhes: {json.dumps(error_data, indent=2)}')
            except:
                self.stdout.write(response.content.decode())
        
        self.stdout.write('\n🔍 Para verificar os dados, acesse:')
        self.stdout.write('   - Admin: http://localhost:8000/admin/')
        self.stdout.write('   - API Webhooks: http://localhost:8000/api/webhooks/events/')
        self.stdout.write('   - API SMS Logs: http://localhost:8000/api/webhooks/sms-logs/')
