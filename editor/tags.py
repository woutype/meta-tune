import re
import shutil
from pathlib import Path

from mutagen import File
from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, COMM, TALB, TCOM, TCON, TDRC, TIT2, TPE1, TPE2, TRCK, USLT
from mutagen.mp3 import MP3
from mutagen.wave import WAVE

# All the tags that the user can edit
FIELD_NAMES = [
    'title', 'artist', 'album', 'album_artist', 'genre',
    'year', 'track', 'composer', 'comment', 'lyrics',
]

# Human names (used in the Telegram report)
FIELD_LABELS = {
    'title': 'Название',
    'artist': 'Исполнитель',
    'album': 'Альбом',
    'album_artist': 'Исполнитель альбома',
    'genre': 'Жанр',
    'year': 'Год',
    'track': 'Номер трека',
    'composer': 'Композитор',
    'comment': 'Комментарий',
    'lyrics': 'Текст песни',
    'cover': 'Обложка',
}

# Simple text frames for mp3 and wav (ID3)
ID3_FRAMES = {
    'title': TIT2,
    'artist': TPE1,
    'album': TALB,
    'album_artist': TPE2,
    'genre': TCON,
    'year': TDRC,
    'track': TRCK,
    'composer': TCOM,
}

# Names of the tags inside a flac file (Vorbis comments)
FLAC_KEYS = {
    'title': 'title',
    'artist': 'artist',
    'album': 'album',
    'album_artist': 'albumartist',
    'genre': 'genre',
    'year': 'date',
    'track': 'tracknumber',
    'composer': 'composer',
    'comment': 'comment',
    'lyrics': 'lyrics',
}

MAX_COVER_SIZE = 10 * 1024 * 1024

# Maximum length of the text fields (the default is 200)
MAX_LENGTHS = {'genre': 100, 'comment': 500, 'lyrics': 50000}

FORMAT_NAMES = {'MP3': 'MP3', 'WAVE': 'WAV', 'FLAC': 'FLAC'}


# ==========================================================================
# Helpers
# ==========================================================================
def open_audio(file_path):
    openers = {'.mp3': MP3, '.wav': WAVE, '.flac': FLAC}
    opener = openers.get(file_path.suffix.lower())
    if opener is None:
        raise ValueError('Unsupported file type')

    try:
        return opener(file_path)
    except Exception:
        # The extension can be wrong, so try to find the real type by the content
        audio = File(file_path)
        if isinstance(audio, (MP3, WAVE, FLAC)):
            return audio
        raise


def clean_fields(data):
    """Makes the text safe: no null symbols, one type of line breaks, no extra spaces"""
    values = {}
    for name in FIELD_NAMES:
        text = str(data.get(name, '') or '')
        text = text.replace('\x00', '').replace('\r\n', '\n').replace('\r', '\n')
        if name == 'lyrics':
            values[name] = text.strip()
        else:
            values[name] = ' '.join(text.split())
    return values


def detect_image_type(data):
    if data.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    return None


def format_duration(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f'{mins}:{secs:02d}'


def validate_fields(values):
    for name in FIELD_NAMES:
        if len(values[name]) > MAX_LENGTHS.get(name, 200):
            title = name.replace('_', ' ').capitalize()
            return f'{title} is too long (maximum {MAX_LENGTHS.get(name, 200)} characters).'
    if values['year'] and not re.fullmatch(r'\d{4}', values['year']):
        return 'Year must have 4 digits, for example 2024.'
    if values['track'] and not re.fullmatch(r'\d{1,3}(/\d{1,3})?', values['track']):
        return 'Track number must look like 3 or 3/12.'
    return None


def make_download_name(fields, original_name):
    extension = Path(original_name).suffix
    if not fields['title']:
        return original_name

    name = fields['title']
    if fields['artist']:
        name = f"{fields['artist']} - {fields['title']}"

    # Remove the characters that are not allowed in file names
    name = re.sub(r'[\\/:*?"<>|]', '', name).strip()
    return f'{name}{extension}' if name else original_name


# ==========================================================================
# Reading
# ==========================================================================
def read_id3_text(id3_tags, frame_id):
    frame = id3_tags.get(frame_id)
    if frame is None or not frame.text:
        return ''
    if frame_id == 'TCON':
        return ', '.join(frame.genres)
    return ', '.join(str(item) for item in frame.text)


def read_id3_fields(audio):
    fields = {name: '' for name in FIELD_NAMES}
    cover_data = None
    cover_mime = None

    if audio.tags is None:
        return fields, cover_data, cover_mime

    for name, frame_class in ID3_FRAMES.items():
        fields[name] = read_id3_text(audio.tags, frame_class.__name__)
    fields['year'] = fields['year'][:4]

    for frame in audio.tags.getall('COMM'):
        if frame.desc == '':
            fields['comment'] = str(frame.text[0]) if frame.text else ''
            break

    lyrics_frames = audio.tags.getall('USLT')
    if lyrics_frames:
        fields['lyrics'] = lyrics_frames[0].text

    cover_frames = audio.tags.getall('APIC')
    if cover_frames:
        # Prefer the front cover (type 3), otherwise the first picture
        frame = next((item for item in cover_frames if item.type == 3), cover_frames[0])
        cover_data = frame.data
        cover_mime = frame.mime

    return fields, cover_data, cover_mime


def read_flac_fields(audio):
    fields = {name: '' for name in FIELD_NAMES}
    cover_data = None
    cover_mime = None

    for name, key in FLAC_KEYS.items():
        values = audio.get(key)
        if values:
            fields[name] = values[0]
    fields['year'] = fields['year'][:4]

    if not fields['lyrics']:
        values = audio.get('unsyncedlyrics')
        if values:
            fields['lyrics'] = values[0]

    if audio.pictures:
        picture = next((item for item in audio.pictures if item.type == 3), audio.pictures[0])
        cover_data = picture.data
        cover_mime = picture.mime

    return fields, cover_data, cover_mime


def read_tags(file_path):
    audio = open_audio(file_path)

    if isinstance(audio, FLAC):
        fields, cover_data, cover_mime = read_flac_fields(audio)
    else:
        fields, cover_data, cover_mime = read_id3_fields(audio)

    # The same cleaning as for the saved values, so unchanged fields are really "unchanged"
    fields = clean_fields(fields)

    info = {
        'format': FORMAT_NAMES.get(type(audio).__name__, file_path.suffix.lstrip('.').upper()),
        'duration': format_duration(audio.info.length),
        'bitrate': round(getattr(audio.info, 'bitrate', 0) / 1000),
        'size': round(file_path.stat().st_size / (1024 * 1024), 1),
    }

    return {
        'fields': fields,
        'cover_data': cover_data,
        'cover_mime': cover_mime,
        'info': info,
    }


# ==========================================================================
# Writing
# ==========================================================================
def write_id3_fields(audio, values, old_values, cover_data, cover_mime, remove_cover):
    if audio.tags is None:
        audio.add_tags()
    id3_tags = audio.tags

    for name, frame_class in ID3_FRAMES.items():
        if values[name] == old_values[name]:
            continue
        id3_tags.delall(frame_class.__name__)
        if values[name]:
            id3_tags.add(frame_class(encoding=3, text=values[name]))

    if values['comment'] != old_values['comment']:
        for frame in id3_tags.getall('COMM'):
            if frame.desc == '':
                id3_tags.delall(frame.HashKey)
        if values['comment']:
            id3_tags.add(COMM(encoding=3, lang='eng', desc='', text=values['comment']))

    if values['lyrics'] != old_values['lyrics']:
        id3_tags.delall('USLT')
        if values['lyrics']:
            id3_tags.add(USLT(encoding=3, lang='eng', desc='', text=values['lyrics']))

    if remove_cover or cover_data:
        id3_tags.delall('APIC')
    if cover_data:
        id3_tags.add(APIC(encoding=3, mime=cover_mime, type=3, desc='Cover', data=cover_data))

    audio.save(v2_version=3)


def write_flac_fields(audio, values, old_values, cover_data, cover_mime, remove_cover):
    if audio.tags is None:
        audio.add_tags()

    for name, key in FLAC_KEYS.items():
        if values[name] == old_values[name]:
            continue
        if values[name]:
            audio[key] = [values[name]]
        elif key in audio:
            del audio[key]

    if remove_cover or cover_data:
        audio.clear_pictures()
    if cover_data:
        picture = Picture()
        picture.type = 3
        picture.mime = cover_mime
        picture.desc = 'Cover'
        picture.data = cover_data
        audio.add_picture(picture)

    audio.save()


def save_tags(file_path, values, cover_data=None, cover_mime=None, remove_cover=False):
    old_values = read_tags(file_path)['fields']

    # A copy of the file: if something goes wrong while saving, the original is restored
    backup_path = file_path.with_name(file_path.name + '.bak')
    shutil.copy2(file_path, backup_path)

    try:
        audio = open_audio(file_path)

        if isinstance(audio, FLAC):
            write_flac_fields(audio, values, old_values, cover_data, cover_mime, remove_cover)
        else:
            write_id3_fields(audio, values, old_values, cover_data, cover_mime, remove_cover)
    except Exception:
        shutil.copy2(backup_path, file_path)
        raise
    finally:
        backup_path.unlink(missing_ok=True)

    # Return the names of the fields that were changed
    return [name for name in FIELD_NAMES if values[name] != old_values[name]]
