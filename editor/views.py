import base64
from django.conf import settings
from mutagen import File
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render, redirect

def load_track(request):
    if request.method == "POST":
        uploaded_file = request.FILES.get('track')
        if uploaded_file:
            fs = FileSystemStorage()
            filename = fs.save(uploaded_file.name, uploaded_file)
            request.session['filename'] = filename
        return redirect('edit-tags')

    return render(request, 'load-track.html')

def edit_tags(request):
    filename = request.session.get('filename')
    file_path = settings.MEDIA_ROOT / filename
    audio = File(file_path)
    apic_frames = audio.tags.getall('APIC') if audio and audio.tags else []

    cover_image = None
    if apic_frames:
        frame = apic_frames[0]
        encoded_data = base64.b64encode(frame.data).decode('utf-8')
        cover_image = f'data:{frame.mime};base64,{encoded_data}'

    context = {
        'cover_image': cover_image
    }

    return render(request, 'edit-tags.html', context)
