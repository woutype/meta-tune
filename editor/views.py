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
    return render(request, 'edit-tags.html')