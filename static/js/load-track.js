const inputPlace = document.getElementById('input-place');
const trackName = document.getElementById('track-name');
const trackMeta = document.getElementById('track-meta');
const inputLabel = document.getElementById('input-label');
const playerContainer = document.getElementById('player-container');
const audioPlayer = document.getElementById('audio-player');
const continueBtn = document.getElementById('continue-btn');
const continueText = document.getElementById('continue-text');
const uploadForm = document.getElementById('upload-form');

const allowedTypes = ['mp3', 'wav', 'flac'];
const maxSizeMb = 100;

// Returns true if the file is ok, otherwise shows an error
function checkFile(file) {
    const fileType = file.name.split('.').pop().toLowerCase();

    if (!allowedTypes.includes(fileType)) {
        showToast('Only MP3, WAV and FLAC files are supported.', 'error');
        return false;
    }

    if (file.size > maxSizeMb * 1024 * 1024) {
        showToast('The file is too big. The maximum size is ' + maxSizeMb + ' MB.', 'error');
        return false;
    }

    return true;
}

inputPlace.addEventListener('change', () => {
    const file = inputPlace.files[0];
    if (!file) {
        return;
    }

    if (!checkFile(file)) {
        inputPlace.value = '';
        return;
    }

    const fileType = file.name.split('.').pop().toUpperCase();
    const fileSize = (file.size / (1024 * 1024)).toFixed(1);

    trackName.textContent = file.name;
    trackMeta.textContent = fileType + ' · ' + fileSize + ' MB';
    inputLabel.classList.add('hidden');
    playerContainer.classList.remove('hidden');
    continueBtn.disabled = false;
    audioPlayer.src = URL.createObjectURL(file);
});

// Drag and drop
inputLabel.addEventListener('dragover', (event) => {
    event.preventDefault();
    inputLabel.classList.add('dragover');
});

inputLabel.addEventListener('dragleave', () => {
    inputLabel.classList.remove('dragover');
});

inputLabel.addEventListener('drop', (event) => {
    event.preventDefault();
    inputLabel.classList.remove('dragover');

    if (event.dataTransfer.files.length > 0) {
        inputPlace.files = event.dataTransfer.files;
        inputPlace.dispatchEvent(new Event('change'));
    }
});

const playBtn = document.getElementById('play-btn');
const iconPlay = document.getElementById('icon-play');

function showPlayIcon() {
    iconPlay.src = iconPlay.src.replace('pause.svg', 'play.svg');
    playerContainer.classList.remove('playing');
}

function showPauseIcon() {
    iconPlay.src = iconPlay.src.replace('play.svg', 'pause.svg');
    playerContainer.classList.add('playing');
}

playBtn.addEventListener('click', () => {
    if (audioPlayer.paused) {
        audioPlayer.play();
    } else {
        audioPlayer.pause();
    }
});

// The icon follows the real state of the audio
audioPlayer.addEventListener('play', showPauseIcon);
audioPlayer.addEventListener('pause', showPlayIcon);
audioPlayer.addEventListener('ended', showPlayIcon);

const slider = document.getElementById('slider');
const currentTime = document.getElementById('current-time');
const totalTime = document.getElementById('total-time');

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

// Paints the filled part of the slider
function updateSliderColor() {
    const percent = slider.max > 0 ? (slider.value / slider.max) * 100 : 0;
    slider.style.setProperty('--progress', percent + '%');
}

audioPlayer.addEventListener('loadedmetadata', () => {
    slider.max = audioPlayer.duration;
    totalTime.textContent = formatTime(audioPlayer.duration);
});

audioPlayer.addEventListener('timeupdate', () => {
    slider.value = audioPlayer.currentTime;
    currentTime.textContent = formatTime(audioPlayer.currentTime);
    updateSliderColor();
});

slider.addEventListener('input', () => {
    audioPlayer.currentTime = slider.value;
    currentTime.textContent = formatTime(slider.value);
    updateSliderColor();
});

const deleteBtn = document.getElementById('delete-btn');

deleteBtn.addEventListener('click', () => {
    audioPlayer.pause();
    audioPlayer.src = '';
    inputPlace.value = '';
    slider.value = 0;
    updateSliderColor();
    currentTime.textContent = '0:00';
    totalTime.textContent = '0:00';
    showPlayIcon();
    playerContainer.classList.add('hidden');
    inputLabel.classList.remove('hidden');
    continueBtn.disabled = true;
});

// Upload with a progress bar
let isUploading = false;

function resetUploadButton() {
    isUploading = false;
    continueBtn.classList.remove('loading');
    continueBtn.style.removeProperty('--upload');
    continueText.textContent = 'Continue';
}

uploadForm.addEventListener('submit', (event) => {
    event.preventDefault();

    if (isUploading || !inputPlace.files[0]) {
        return;
    }

    isUploading = true;
    audioPlayer.pause();
    continueBtn.classList.add('loading');
    continueText.textContent = 'Uploading 0%';

    const request = new XMLHttpRequest();
    request.open('POST', window.location.href);
    request.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

    request.upload.addEventListener('progress', (progressEvent) => {
        if (progressEvent.lengthComputable) {
            const percent = Math.round((progressEvent.loaded / progressEvent.total) * 100);
            continueBtn.style.setProperty('--upload', percent + '%');
            continueText.textContent = percent < 100 ? 'Uploading ' + percent + '%' : 'Processing...';
        }
    });

    request.addEventListener('load', () => {
        let data = null;
        try {
            data = JSON.parse(request.responseText);
        } catch (error) {
            data = null;
        }

        if (data && data.ok) {
            window.location.href = data.redirect;
            return;
        }

        resetUploadButton();
        showToast(data && data.error ? data.error : 'Upload failed. Refresh the page and try again.', 'error');
    });

    request.addEventListener('error', () => {
        resetUploadButton();
        showToast('Connection problem. Check the internet and try again.', 'error');
    });

    request.send(new FormData(uploadForm));
});

// The browser can show the page from its memory when the user presses "Back"
window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
        resetUploadButton();
    }
});

// Space = play / pause
document.addEventListener('keydown', (event) => {
    const tag = document.activeElement.tagName;

    if (event.code === 'Space' && !playerContainer.classList.contains('hidden') && tag !== 'BUTTON' && tag !== 'TEXTAREA') {
        event.preventDefault();
        playBtn.click();
    }
});

// Visitors counter
const visitors = document.getElementById('visitors');
const visitorsCount = document.getElementById('visitors-count');

// The number runs from 0 to the real value
function countUp(total) {
    const duration = 1000;
    const startTime = performance.now();

    function step(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        const easing = 1 - Math.pow(1 - progress, 3);
        visitorsCount.textContent = Math.round(total * easing).toLocaleString();

        if (progress < 1) {
            requestAnimationFrame(step);
        }
    }

    requestAnimationFrame(step);
}

fetch(visitors.dataset.url)
    .then((response) => response.json())
    .then((data) => {
        if (data.total === null) {
            visitors.classList.add('hidden');
            return;
        }
        visitorsCount.classList.remove('loading');
        countUp(data.total);
    })
    .catch(() => visitors.classList.add('hidden'));
