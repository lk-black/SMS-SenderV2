release: ./pre_start.sh
web: gunicorn sms_sender.wsgi --log-file -
worker: celery -A sms_sender worker --loglevel=info
beat: celery -A sms_sender beat --loglevel=info
