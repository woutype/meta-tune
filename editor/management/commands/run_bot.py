import time

from django.core.management.base import BaseCommand, CommandError

from editor import telegram, visits


class Command(BaseCommand):
    help = 'Runs the Telegram bot. Only the admin can use it, everyone else gets "Access denied"'

    def handle(self, *args, **options):
        if not telegram.bot_is_ready():
            raise CommandError('Fill TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_ID in the .env file')

        try:
            me = telegram.call_api('getMe')
        except Exception as error:
            raise CommandError(f'Cannot connect to Telegram ({type(error).__name__}). Check the internet.')

        if not me.get('ok'):
            raise CommandError(f"Telegram says: {me.get('description')}. Check TELEGRAM_BOT_TOKEN.")

        # The menu with commands (only the admin can use them anyway)
        telegram.call_api('setMyCommands', {
            'commands': '[{"command": "stats", "description": "Visitors counter"}]',
        })

        self.stdout.write(f"Bot @{me['result']['username']} is running. Press Ctrl+C to stop.")
        offset = 0

        while True:
            try:
                result = telegram.call_api('getUpdates', {'offset': offset, 'timeout': 30}, timeout=40)
            except Exception as error:
                self.stderr.write(f'Connection problem ({type(error).__name__}), trying again...')
                time.sleep(5)
                continue

            if not result.get('ok'):
                # For example the token was changed, or the bot is started twice
                self.stderr.write(f"Telegram error: {result.get('description')}")
                time.sleep(5)
                continue

            for update in result.get('result', []):
                offset = update['update_id'] + 1
                try:
                    self.handle_update(update)
                except Exception as error:
                    self.stderr.write(f'Update error ({type(error).__name__})')

    def handle_update(self, update):
        message = update.get('message')
        if not message or message['chat']['type'] != 'private':
            return

        chat_id = message['chat']['id']

        # Strangers are not allowed to use the bot
        if not telegram.is_admin(message['from']['id']):
            telegram.send_message(chat_id, '⛔ Access denied.')
            return

        text = message.get('text', '')

        if text.startswith('/stats'):
            total = visits.get_total()
            answer = f'👥 Посетителей на сайте: <b>{total}</b>' if total is not None else 'База данных недоступна.'
        else:
            answer = (
                '👋 Привет! Я присылаю отчёт каждый раз, когда на сайте сохраняют теги трека.\n\n'
                '/stats — сколько людей заходило на сайт'
            )

        telegram.send_message(chat_id, answer)
