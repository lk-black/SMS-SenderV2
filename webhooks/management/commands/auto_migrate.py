import time
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.db.utils import OperationalError


class Command(BaseCommand):
    """
    Comando para executar migrações com retry em caso de falha
    """
    help = 'Executa migrações com retry automático'

    def add_arguments(self, parser):
        parser.add_argument(
            '--max-retries',
            type=int,
            default=5,
            help='Número máximo de tentativas'
        )
        parser.add_argument(
            '--retry-delay',
            type=int,
            default=2,
            help='Delay entre tentativas em segundos'
        )

    def handle(self, *args, **options):
        max_retries = options['max_retries']
        retry_delay = options['retry_delay']
        
        self.stdout.write(
            self.style.SUCCESS('🔄 Iniciando processo de migração automática...')
        )
        
        for attempt in range(1, max_retries + 1):
            try:
                # Testar conexão com banco
                self.stdout.write(f'📊 Tentativa {attempt}/{max_retries} - Testando conexão...')
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                
                # Executar migrações
                self.stdout.write('🔄 Executando migrações...')
                call_command('migrate', '--noinput', verbosity=2)
                
                # Verificar migrações aplicadas
                self.stdout.write('✅ Verificando status das migrações...')
                call_command('showmigrations', verbosity=1)
                
                self.stdout.write(
                    self.style.SUCCESS('✅ Migrações executadas com sucesso!')
                )
                return
                
            except OperationalError as e:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠️  Tentativa {attempt} falhou: {e}'
                    )
                )
                
                if attempt < max_retries:
                    self.stdout.write(f'⏳ Aguardando {retry_delay}s antes da próxima tentativa...')
                    time.sleep(retry_delay)
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            '❌ Falha ao executar migrações após múltiplas tentativas!'
                        )
                    )
                    raise
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Erro inesperado: {e}')
                )
                raise
