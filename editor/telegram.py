import logging
from html import escape

import requests
from django.conf import settings
from django.utils import timezone

from . import visits
from .tags import FIELD_LABELS

logger = logging.getLogger(__name__)

API_URL = 'https://api.telegram.org/bot{token}/{method}'

# The fields that are shown in the report (the lyrics and the comment are too long)
REPORT_FIELDS = ['title', 'artist', 'album', 'album_artist', 'genre', 'year', 'track', 'composer']


def bot_is_ready():
    return bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_ADMIN_ID)


def is_admin(user_id):
    return str(user_id) == str(settings.TELEGRAM_ADMIN_ID)


def call_api(method, data=None, files=None, timeout=15):
    url = API_URL.format(token=settings.TELEGRAM_BOT_TOKEN, method=method)
    response = requests.post(url, data=data, files=files, timeout=timeout)
    return response.json()


def send_message(chat_id, text):
    return call_api('sendMessage', {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'})


def short(text, limit=40):
    text = text.strip()
    return text if len(text) <= limit else text[:limit - 1] + '…'


def describe_device(user_agent):
    """Very simple detection of the browser and the system from the User-Agent"""
    if 'Windows' in user_agent:
        system = 'Windows'
    elif 'Android' in user_agent:
        system = 'Android'
    elif 'iPhone' in user_agent or 'iPad' in user_agent:
        system = 'iOS'
    elif 'Mac OS X' in user_agent:
        system = 'macOS'
    elif 'Linux' in user_agent:
        system = 'Linux'
    else:
        system = 'неизвестная система'

    if 'Edg/' in user_agent:
        browser = 'Edge'
    elif 'OPR/' in user_agent:
        browser = 'Opera'
    elif 'Firefox/' in user_agent:
        browser = 'Firefox'
    elif 'Chrome/' in user_agent or 'CriOS/' in user_agent:
        browser = 'Chrome'
    elif 'Safari/' in user_agent:
        browser = 'Safari'
    else:
        browser = 'неизвестный браузер'

    return f'{browser} · {system}'


def make_report_text(report, visitor_number):
    lines = ['🎵 <b>Теги трека сохранены</b>', '']

    for name in REPORT_FIELDS:
        value = report['fields'][name]
        if value:
            lines.append(f'<b>{FIELD_LABELS[name]}:</b> {escape(short(value))}')

    if report['fields']['lyrics']:
        lines.append(f"<b>Текст песни:</b> {len(report['fields']['lyrics'])} симв.")

    if report['changed']:
        changed = ', '.join(FIELD_LABELS[name].lower() for name in report['changed'])
        lines.append('')
        lines.append(f'✏️ <b>Изменено:</b> {escape(changed)}')

    info = report['info']
    lines.append(f"📁 {escape(short(report['filename'], 50))}")
    lines.append(f"{info['format']} · {info['duration']} · {info['size']} МБ")

    number_text = f'№{visitor_number}' if visitor_number else 'неизвестен'
    lines.append('')
    lines.append('👤 <b>Кто:</b>')
    lines.append(f'Посетитель {number_text} · {escape(report["ip"])}')
    lines.append(escape(report['device']))
    lines.append(f"🕒 {timezone.localtime().strftime('%d.%m.%Y %H:%M')}")

    return '\n'.join(lines)


def send_save_report(report, cover_data, cover_mime):
    """Sends the report to the admin. It runs in a separate thread, so errors must not break the site"""
    if not bot_is_ready():
        return

    try:
        visitor_number = visits.get_visitor_number(report['visitor_id'])
        text = make_report_text(report, visitor_number)
        chat_id = settings.TELEGRAM_ADMIN_ID
        text_sent = False

        if cover_data:
            extension = 'png' if cover_mime == 'image/png' else 'jpg'
            caption_fits = len(text) <= 1024
            data = {'chat_id': chat_id, 'parse_mode': 'HTML'}
            if caption_fits:
                data['caption'] = text

            result = call_api('sendPhoto', data, files={'photo': (f'cover.{extension}', cover_data)})
            if not result.get('ok'):
                logger.warning('Telegram did not accept the cover: %s', result.get('description'))
            text_sent = bool(result.get('ok')) and caption_fits

        if not text_sent:
            result = send_message(chat_id, text)
            if not result.get('ok'):
                logger.warning(
                    'Telegram did not accept the report: %s. Open the bot in Telegram and press Start.',
                    result.get('description'),
                )
    except Exception as error:
        # Do not log the exception text: it can contain the bot token inside the URL
        logger.warning('Telegram report was not sent (%s)', type(error).__name__)
