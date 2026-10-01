const inputPlace = document.getElementById('input-place');
const trackName = document.getElementById('track-name');
const inputLabel = document.getElementById('input-label');
const playerContainer = document.getElementById('player-container');
const audioPlayer = document.getElementById('audio-player');

inputPlace.addEventListener('change', () => {
    const file = inputPlace.files[0];
    if (file) {
        trackName.textContent = file.name;
        inputLabel.classList.add('hidden');
        playerContainer.classList.remove('hidden');
        audioPlayer.src = URL.createObjectURL(file);
    }
});

const playBtn = document.getElementById('play-btn');
const iconPlay = document.getElementById('icon-play');

playBtn.addEventListener('click', () => {
    if (audioPlayer.paused) {
        audioPlayer.play();
        iconPlay.src = iconPlay.src.replace('play.svg', 'pause.svg');
    } else {
        audioPlayer.pause();
        iconPlay.src = iconPlay.src.replace('pause.svg', 'play.svg');
    }
});

const slider = document.getElementById('slider');

audioPlayer.addEventListener('loadedmetadata', () => {
    slider.max = audioPlayer.duration;
});

audioPlayer.addEventListener('timeupdate', () => {
    slider.value = audioPlayer.currentTime;
});

slider.addEventListener('input', () => {
    audioPlayer.currentTime = slider.value;
});

const durationTime = document.getElementById('duration-time');

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

audioPlayer.addEventListener('timeupdate', () => {
    slider.value = audioPlayer.currentTime;
    durationTime.textContent = formatTime(audioPlayer.currentTime);
});

const deleteBtn = document.getElementById('delete-btn');

deleteBtn.addEventListener('click', () => {
    audioPlayer.pause();
    audioPlayer.src = '';
    inputPlace.value = '';
    slider.value = 0;
    durationTime.textContent = '0:00';
    iconPlay.src = iconPlay.src.replace('pause.svg', 'play.svg');
    playerContainer.classList.add('hidden');
    inputLabel.classList.remove('hidden');
});