from django.core.files.storage import FileSystemStorage
from django.shortcuts import render

def load_track(request):
    if request.method == "POST":
        uploaded_file = request.FILES.get('track')
        if uploaded_file:
            fs = FileSystemStorage()
            filename = fs.save(uploaded_file.name, uploaded_file)
            return render(request, 'edit-tags.html', {'filename': filename})

    return render(request, 'load-track.html')
