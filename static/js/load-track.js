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