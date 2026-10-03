from django.conf import settings
from django.core.management.base import BaseCommand

from editor import telegram, visits


class Command(BaseCommand):
    help = 'Checks the .env settings: Supabase connection and Telegram bot (sends a test message)'

    def handle(self, *args, **options):
        self.check_database()
        self.stdout.write('')
        self.check_telegram()

    def check_database(self):
        self.stdout.write('--- Supabase ---')
        if not settings.SUPABASE_DB_URL:
            self.stdout.write('FAIL: SUPABASE_DB_URL is empty in .env')
            return

        try:
            with visits.connect() as connection:
                connection.execute('SELECT 1')
        except Exception as error:
            self.stdout.write(f'FAIL: {type(error).__name__}: {str(error).strip()[:300]}')
            self.stdout.write('Hints:')
            self.stdout.write('  - the direct address (db.xxx.supabase.co) often works only over IPv6;')
            self.stdout.write('    in Supabase press Connect and copy the "Session pooler" address instead')
            self.stdout.write('  - check the password (special symbols must be URL-encoded)')
            return

        visits.paused_until = 0
        total = visits.get_total()
        self.stdout.write(f'OK: connected, visitors in the table: {total}')

    def check_telegram(self):
        self.stdout.write('--- Telegram ---')
        if not telegram.bot_is_ready():
            self.stdout.write('FAIL: TELEGRAM_BOT_TOKEN or TELEGRAM_ADMIN_ID is empty in .env')
            return

        try:
            me = telegram.call_api('getMe')
        except Exception as error:
            self.stdout.write(f'FAIL: cannot connect to Telegram ({type(error).__name__})')
            return

        if not me.get('ok'):
            self.stdout.write(f"FAIL: {me.get('description')} (check TELEGRAM_BOT_TOKEN)")
            return

        self.stdout.write(f"OK: bot @{me['result']['username']} found")

        result = telegram.send_message(settings.TELEGRAM_ADMIN_ID, '✅ MetaTune: проверка связи прошла успешно')
        if result.get('ok'):
            self.stdout.write('OK: test message sent, look in Telegram')
        else:
            self.stdout.write(f"FAIL: {result.get('description')}")
            self.stdout.write('  - open your bot in Telegram and press Start, then run this command again')
            self.stdout.write('  - check that TELEGRAM_ADMIN_ID is your own numeric id')
