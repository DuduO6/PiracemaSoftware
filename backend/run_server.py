import os
import sys
from dotenv import load_dotenv
from django.core.management import execute_from_command_line

if __name__ == '__main__':

    # 1️⃣ Carrega variáveis do .env
    load_dotenv()

    # 2️⃣ Define o settings do Django
    os.environ.setdefault(
        'DJANGO_SETTINGS_MODULE',
        'backend.settings'
    )

    # 3️⃣ Comando fixo (PyInstaller-safe)
    sys.argv = [
        'manage.py',
        'runserver',
        '127.0.0.1:8000',
        '--noreload',
        '--insecure'
    ]

    execute_from_command_line(sys.argv)
