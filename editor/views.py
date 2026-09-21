from django.shortcuts import render

def load_track(request):
    return render(request, 'load-track.html')
