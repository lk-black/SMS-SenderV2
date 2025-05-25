import os
import sys
from pathlib import Path

# Diretório base para logs
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / 'logs'

# Criar diretório de logs apenas se não estivermos na Render
if not os.environ.get('RENDER'):
    LOGS_DIR.mkdir(exist_ok=True)

# Determinar se estamos em produção (Render)
IS_PRODUCTION = bool(os.environ.get('RENDER'))
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO' if IS_PRODUCTION else 'DEBUG')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} [{name}:{lineno}] {funcName} - {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'simple': {
            'format': '[{levelname}] {name} - {message}',
            'style': '{',
        },
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "module": "%(module)s", "function": "%(funcName)s", "line": "%(lineno)d", "message": "%(message)s"}',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
        'render_format': {
            'format': '🔍 [{asctime}] {levelname} | {name} | {funcName}:{lineno} | {message}',
            'style': '{',
            'datefmt': '%H:%M:%S'
        },
        'webhook_format': {
            'format': '📡 [{asctime}] {levelname} | WEBHOOK | {message}',
            'style': '{',
            'datefmt': '%H:%M:%S'
        },
        'sms_format': {
            'format': '📱 [{asctime}] {levelname} | SMS | {message}',
            'style': '{',
            'datefmt': '%H:%M:%S'
        },
        'error_format': {
            'format': '🚨 [{asctime}] {levelname} | {name} | {funcName}:{lineno} | {message}',
            'style': '{',
            'datefmt': '%H:%M:%S'
        }
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'render_format' if IS_PRODUCTION else 'verbose',
            'stream': sys.stdout,
        },
        'console_error': {
            'level': 'ERROR',
            'class': 'logging.StreamHandler',
            'formatter': 'error_format',
            'stream': sys.stderr,
        },
        'webhook_console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'webhook_format',
            'stream': sys.stdout,
        },
        'sms_console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'sms_format',
            'stream': sys.stdout,
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        # Django core
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console_error'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console_error'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['null'] if IS_PRODUCTION else ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        
        # Application loggers
        'webhooks': {
            'handlers': ['webhook_console', 'console_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'webhooks.views': {
            'handlers': ['webhook_console', 'console_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'webhooks.serializers': {
            'handlers': ['webhook_console'],
            'level': 'INFO',
            'propagate': False,
        },
        'sms_service': {
            'handlers': ['sms_console', 'console_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'sms_service.sms': {
            'handlers': ['sms_console', 'console_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'console_error'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery.task': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        
        # Third party
        'twilio': {
            'handlers': ['sms_console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'redis': {
            'handlers': ['console'] if not IS_PRODUCTION else ['null'],
            'level': 'WARNING',
            'propagate': False,
        },
        'urllib3': {
            'handlers': ['null'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
}

# Adicionar file handlers apenas em desenvolvimento
if not IS_PRODUCTION:
    # File handlers para desenvolvimento
    LOGGING['handlers'].update({
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'sms_sender.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'webhooks_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'webhooks.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
        },
        'sms_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'sms.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'errors.log',
            'maxBytes': 1024*1024*5,  # 5MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
    })
    
    # Adicionar file handlers aos loggers em desenvolvimento
    for logger_name in ['webhooks', 'sms_service', 'django']:
        if logger_name in LOGGING['loggers']:
            LOGGING['loggers'][logger_name]['handlers'].extend(['file', 'error_file'])
        
    LOGGING['loggers']['webhooks']['handlers'].append('webhooks_file')
    LOGGING['loggers']['sms_service']['handlers'].append('sms_file')

# Configuração específica para produção na Render
if IS_PRODUCTION:
    # Configurações otimizadas para Render
    print("🚀 Configurando logs para produção na Render")
    
    # Reduzir logs desnecessários em produção
    LOGGING['loggers']['django.security']['level'] = 'ERROR'
    LOGGING['loggers']['django']['level'] = 'WARNING'
    
    # Configurar logging estruturado para métricas
    LOGGING['handlers']['metrics'] = {
        'level': 'INFO',
        'class': 'logging.StreamHandler',
        'formatter': 'json',
        'stream': sys.stdout,
    }
