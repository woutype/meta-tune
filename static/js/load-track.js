const audio = document.getElementById('audio');
const fileInput = document.getElementById('input-file');
const uploadBox = document.getElementById('upload-block');
const playerBox = document.getElementById('player-block');
const trackTitle = document.getElementById('track-name');
const closeButton = document.getElementById('cancel');
const playButton = document.getElementById('play');
const playIcon = playButton.querySelector('img');
const timeText = document.getElementById('time');
const bar = document.getElementById('slider');
const filled = document.getElementById('progress');
const handle = document.getElementById('thumb');

let isDragging = false;

function setBar(percent) {
    filled.style.width = percent + '%';
    handle.style.left = percent + '%';
}

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const rest = Math.floor(seconds % 60);
    return minutes + ':' + String(rest).padStart(2, '0');
}

function rewindTo(clientX) {
    const rect = bar.getBoundingClientRect();
    let percent = ((clientX - rect.left) / rect.width) * 100;
    percent = Math.max(0, Math.min(100, percent));

    setBar(percent);
    if (audio.duration) {
        audio.currentTime = (percent / 100) * audio.duration;
    }
}

function stopDragging() {
    isDragging = false;
    handle.classList.remove('active');
}

fileInput.addEventListener('change', () => {
    const file = fileInput.files[0];
    if (!file) return;

    trackTitle.textContent = file.name;
    audio.src = URL.createObjectURL(file);
    uploadBox.classList.add('hidden');
    playerBox.classList.remove('hidden');
});

closeButton.addEventListener('click', () => {
    audio.pause();
    audio.removeAttribute('src');
    fileInput.value = '';
    setBar(0);
    timeText.textContent = '0:00';
    uploadBox.classList.remove('hidden');
    playerBox.classList.add('hidden');
});

playButton.addEventListener('click', () => {
    audio.paused ? audio.play() : audio.pause();
});

audio.addEventListener('play', () => {
    playIcon.src = playIcon.src.replace('play.svg', 'pause.svg');
});

audio.addEventListener('pause', () => {
    playIcon.src = playIcon.src.replace('pause.svg', 'play.svg');
});

audio.addEventListener('timeupdate', () => {
    timeText.textContent = formatTime(audio.currentTime);

    if (!isDragging && audio.duration) {
        setBar((audio.currentTime / audio.duration) * 100);
    }
});

audio.addEventListener('ended', () => {
    setBar(0);
    timeText.textContent = '0:00';
});

bar.addEventListener('pointerdown', (e) => {
    isDragging = true;
    bar.setPointerCapture(e.pointerId);
    handle.classList.add('active');
    rewindTo(e.clientX);
});

bar.addEventListener('pointermove', (e) => {
    if (isDragging) rewindTo(e.clientX);
});

bar.addEventListener('pointerup', stopDragging);
bar.addEventListener('pointercancel', stopDragging);