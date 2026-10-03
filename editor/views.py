import base64
import logging
import threading
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse

from . import tags, telegram, visits

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = ['.mp3', '.wav', '.flac']
MAX_TRACK_SIZE = 100 * 1024 * 1024
VISITOR_COOKIE = 'visitor_id'
GENRES = [
    'Pop', 'Rock', 'Hip-Hop', 'Rap', 'Electronic', 'Dance', 'R&B', 'Jazz', 'Classical',
    'Metal', 'Indie', 'Folk', 'Country', 'Reggae', 'Blues', 'Lo-fi', 'Phonk', 'Soundtrack',
]


def is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def get_visitor_id(request):
    try:
        return str(uuid.UUID(request.COOKIES.get(VISITOR_COOKIE, '')))
    except ValueError:
        return None


def get_track_path(request):
    # Only the name is used, so the path can never leave the media folder
    filename = Path(request.session.get('filename', '')).name
    if not filename:
        return None

    file_path = settings.MEDIA_ROOT / filename
    return file_path if file_path.is_file() else None


def get_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def csrf_failed(request, reason=''):
    error = 'The page was open for too long. Please try again.'

    if is_ajax(request):
        return JsonResponse({'ok': False, 'error': error}, status=403)

    messages.warning(request, error)
    return redirect(request.path)


def save_upload(request):
    """Saves the uploaded track. Returns the text of the error, or None if everything is ok"""
    uploaded_file = request.FILES.get('track')

    if not uploaded_file:
        return 'Choose a track first.'
    if Path(uploaded_file.name).suffix.lower() not in ALLOWED_EXTENSIONS:
        return 'Only MP3, WAV and FLAC files are supported.'
    if uploaded_file.size > MAX_TRACK_SIZE:
        return 'The file is too big. The maximum size is 100 MB.'

    fs = FileSystemStorage()
    try:
        filename = fs.save(uploaded_file.name, uploaded_file)
    except OSError:
        logger.exception('Could not save the uploaded file')
        return 'Could not save the file on the server. Please try again.'

    # Check that the file can be read before the editor opens
    try:
        tags.read_tags(settings.MEDIA_ROOT / filename)
    except Exception:
        logger.warning('Broken file was uploaded: %s', filename)
        fs.delete(filename)
        return 'This file looks broken or is not a real MP3, WAV or FLAC.'

    request.session['filename'] = filename
    return None


def load_track(request):
    if request.method == "POST":
        error = save_upload(request)

        if is_ajax(request):
            if error:
                return JsonResponse({'ok': False, 'error': error}, status=400)
            return JsonResponse({'ok': True, 'redirect': reverse('edit-tags')})

        if error:
            messages.error(request, error)
        else:
            return redirect('edit-tags')

    response = render(request, 'load-track.html')

    # Every browser gets its own id, it is used for the visitors counter
    if not get_visitor_id(request):
        response.set_cookie(VISITOR_COOKIE, str(uuid.uuid4()), max_age=60 * 60 * 24 * 365 * 2, httponly=True, samesite='Lax')

    return response


def visitors(request):
    visitor_id = get_visitor_id(request)
    total = visits.register_visit(visitor_id) if visitor_id else None
    return JsonResponse({'total': total})


def edit_tags(request):
    file_path = get_track_path(request)
    if file_path is None:
        messages.warning(request, 'Upload a track first.')
        return redirect('load-track')

    try:
        track = tags.read_tags(file_path)
    except Exception:
        logger.exception('Could not read the tags of %s', file_path.name)
        messages.error(request, 'This file looks broken, the tags cannot be read.')
        return redirect('load-track')

    fields = track['fields']
    form_changed = False

    if request.method == "POST":
        fields = tags.clean_fields(request.POST)
        remove_cover = request.POST.get('remove_cover') == '1'
        cover_file = request.FILES.get('cover')
        cover_data = None
        cover_mime = None

        error = tags.validate_fields(fields)

        if not error and cover_file:
            if cover_file.size > tags.MAX_COVER_SIZE:
                error = 'The cover is too big. The maximum size is 10 MB.'
            else:
                cover_data = cover_file.read()
                cover_mime = tags.detect_image_type(cover_data)
                if cover_mime is None:
                    error = 'The cover must be a JPEG or PNG image.'

        if not error:
            try:
                changed = tags.save_tags(file_path, fields, cover_data, cover_mime, remove_cover)
            except PermissionError:
                error = 'The file is used by another program. Close it and try again.'
            except Exception:
                logger.exception('Could not save the tags of %s', file_path.name)
                error = 'Could not save the tags. Please try again.'

        if error:
            messages.error(request, error)
            form_changed = True
        else:
            messages.success(request, 'Tags saved successfully.')

            if cover_data or remove_cover:
                changed.append('cover')

            # The cover for the Telegram report: the new one or the old one
            report_cover = cover_data if cover_data else (None if remove_cover else track['cover_data'])
            report_mime = cover_mime if cover_data else track['cover_mime']

            report = {
                'fields': fields,
                'changed': changed,
                'filename': file_path.name,
                'info': track['info'],
                'visitor_id': get_visitor_id(request),
                'ip': get_ip(request),
                'device': telegram.describe_device(request.META.get('HTTP_USER_AGENT', '')),
            }
            threading.Thread(
                target=telegram.send_save_report,
                args=(report, report_cover, report_mime),
                daemon=True,
            ).start()

            return redirect('edit-tags')

    cover_image = None
    if track['cover_data']:
        encoded_data = base64.b64encode(track['cover_data']).decode('utf-8')
        cover_image = f"data:{track['cover_mime']};base64,{encoded_data}"

    context = {
        'fields': fields,
        'cover_image': cover_image,
        'info': track['info'],
        'filename': file_path.name,
        'genres': GENRES,
        'form_changed': form_changed,
    }

    return render(request, 'edit-tags.html', context)


def download_track(request):
    file_path = get_track_path(request)
    if file_path is None:
        messages.warning(request, 'Upload a track first.')
        return redirect('load-track')

    try:
        fields = tags.read_tags(file_path)['fields']
        download_name = tags.make_download_name(fields, file_path.name)
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=download_name)
    except Exception:
        logger.exception('Could not download %s', file_path.name)
        messages.error(request, 'Could not download the file. Please try again.')
        return redirect('edit-tags')
