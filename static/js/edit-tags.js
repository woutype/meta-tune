const form = document.getElementById('tags-container');
const coverInput = document.getElementById('cover-input');
const coverWrap = document.getElementById('cover-wrap');
const removeCoverBtn = document.getElementById('remove-cover-btn');
const removeCoverInput = document.getElementById('remove-cover');
const saveBtn = document.getElementById('save-btn');
const saveText = document.getElementById('save-text');
const unsavedHint = document.getElementById('unsaved-hint');
const lyrics = document.getElementById('track-lyrics');
const lyricsCount = document.getElementById('lyrics-count');
const yearInput = document.getElementById('track-year');
const trackNumberInput = document.getElementById('track-number');
const titleInput = document.getElementById('track-title');
const artistInput = document.getElementById('track-artist');
const genreInput = document.getElementById('track-genre');
const genreChips = document.querySelectorAll('.chip');
const genreCombo = document.getElementById('genre-combo');
const genreMenu = document.getElementById('genre-menu');
const genreToggle = document.getElementById('genre-toggle');
const genreOptions = Array.from(genreMenu.querySelectorAll('.combo-option'));
const fillNameBtn = document.getElementById('fill-name-btn');
const coverContainer = document.getElementById('cover-container');
const downloadBtn = document.getElementById('download-btn');

const maxCoverSizeMb = 10;
const coverTypes = ['image/jpeg', 'image/png'];

let coverChanged = false;
let isSaving = false;

// All the text fields in one string, so it is easy to see if something was changed
function getFormValues() {
    const values = [];
    form.querySelectorAll('.form-input, .form-textarea').forEach((field) => values.push(field.value));
    return values.join('\u0001');
}

// If the server found an error, the form already contains new (not saved) values
const startValues = form.dataset.changed === '1' ? '' : getFormValues();
const startedChanged = form.dataset.changed === '1';

function checkChanges() {
    const changed = startedChanged || coverChanged || getFormValues() !== startValues;
    saveBtn.disabled = !changed;
    unsavedHint.classList.toggle('show', changed);
}

// The button "Fill from file name" is shown only while the track name is empty
function updateFillButton() {
    fillNameBtn.classList.toggle('hidden', titleInput.value !== '');
}

// The chip of the current genre is highlighted
function updateChips() {
    const genre = genreInput.value.trim().toLowerCase();
    genreChips.forEach((chip) => chip.classList.toggle('active', chip.dataset.genre.toLowerCase() === genre));
    genreOptions.forEach((option) => option.classList.toggle('active', option.dataset.genre.toLowerCase() === genre));
}

form.addEventListener('input', () => {
    checkChanges();
    updateFillButton();
    updateChips();
});

// "Author - Name.mp3" becomes the artist and the track name
fillNameBtn.addEventListener('click', () => {
    let name = form.dataset.filename.replace(/\.[^.]+$/, '');
    name = name.replace(/_[A-Za-z0-9]{7}$/, '');
    const parts = name.split(' - ');

    if (parts.length >= 2) {
        if (artistInput.value === '') {
            artistInput.value = parts[0].trim();
        }
        titleInput.value = parts.slice(1).join(' - ').trim();
    } else {
        titleInput.value = name.replace(/_+/g, ' ').trim();
    }

    checkChanges();
    updateFillButton();
});

genreChips.forEach((chip) => {
    chip.addEventListener('click', () => {
        genreInput.value = chip.dataset.genre;
        checkChanges();
        updateChips();
    });
});

updateFillButton();
updateChips();

// Genre dropdown
let highlightedIndex = -1;

function getVisibleOptions() {
    return genreOptions.filter((option) => !option.classList.contains('hidden'));
}

function setHighlight(index) {
    const visibleOptions = getVisibleOptions();
    genreOptions.forEach((option) => option.classList.remove('highlighted'));
    highlightedIndex = index;

    if (index >= 0 && visibleOptions[index]) {
        visibleOptions[index].classList.add('highlighted');
        visibleOptions[index].scrollIntoView({ block: 'nearest' });
    }
}

function closeGenreMenu() {
    genreCombo.classList.remove('open');
    genreInput.setAttribute('aria-expanded', 'false');
    setHighlight(-1);
}

// Shows the genres that fit the typed text (all of them if the text is a ready genre)
function openGenreMenu() {
    const text = genreInput.value.trim().toLowerCase();
    const isReadyGenre = genreOptions.some((option) => option.dataset.genre.toLowerCase() === text);
    const searchText = isReadyGenre ? '' : text;

    genreOptions.forEach((option) => {
        option.classList.toggle('hidden', !option.dataset.genre.toLowerCase().includes(searchText));
    });

    if (getVisibleOptions().length === 0) {
        closeGenreMenu();
        return;
    }

    // Open upwards if there is no free place below (the buttons panel is at the bottom)
    const box = genreInput.getBoundingClientRect();
    const spaceBelow = window.innerHeight - box.bottom - 100;
    genreCombo.classList.toggle('up', spaceBelow < 250 && box.top > spaceBelow);

    genreCombo.classList.add('open');
    genreInput.setAttribute('aria-expanded', 'true');
    setHighlight(-1);
}

function chooseGenre(genre) {
    genreInput.value = genre;
    closeGenreMenu();
    checkChanges();
    updateChips();
}

genreInput.addEventListener('focus', openGenreMenu);
genreInput.addEventListener('click', openGenreMenu);
genreInput.addEventListener('input', openGenreMenu);

genreToggle.addEventListener('click', () => {
    if (genreCombo.classList.contains('open')) {
        closeGenreMenu();
    } else {
        openGenreMenu();
    }
});

genreOptions.forEach((option) => {
    // mousedown must not take the focus away from the field
    option.addEventListener('mousedown', (event) => event.preventDefault());
    option.addEventListener('click', () => chooseGenre(option.dataset.genre));
});

genreInput.addEventListener('keydown', (event) => {
    const isOpen = genreCombo.classList.contains('open');
    const visibleOptions = getVisibleOptions();

    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        if (!isOpen) {
            openGenreMenu();
            return;
        }
        const step = event.key === 'ArrowDown' ? 1 : -1;
        setHighlight((highlightedIndex + step + visibleOptions.length) % visibleOptions.length);
    } else if (event.key === 'Enter' && isOpen) {
        if (highlightedIndex >= 0) {
            event.preventDefault();
            chooseGenre(visibleOptions[highlightedIndex].dataset.genre);
        } else {
            closeGenreMenu();
        }
    } else if (event.key === 'Escape' || event.key === 'Tab') {
        closeGenreMenu();
    }
});

// A click outside of the dropdown closes it
document.addEventListener('click', (event) => {
    if (!genreCombo.contains(event.target)) {
        closeGenreMenu();
    }
});

// Lyrics counter
function updateLyricsCount() {
    lyricsCount.textContent = lyrics.value.length.toLocaleString() + ' characters';
}

lyrics.addEventListener('input', updateLyricsCount);
updateLyricsCount();

// Year and track number accept only the correct symbols
yearInput.addEventListener('input', () => {
    yearInput.value = yearInput.value.replace(/\D/g, '');
});

trackNumberInput.addEventListener('input', () => {
    trackNumberInput.value = trackNumberInput.value.replace(/[^\d/]/g, '');
});

// Cover: show the new image right away
coverInput.addEventListener('change', () => {
    const file = coverInput.files[0];
    if (!file) {
        return;
    }

    if (!coverTypes.includes(file.type)) {
        showToast('The cover must be a JPEG or PNG image.', 'error');
        coverInput.value = '';
        return;
    }

    if (file.size > maxCoverSizeMb * 1024 * 1024) {
        showToast('The cover is too big. The maximum size is ' + maxCoverSizeMb + ' MB.', 'error');
        coverInput.value = '';
        return;
    }

    coverWrap.style.setProperty('--cover', 'url(' + URL.createObjectURL(file) + ')');
    coverWrap.classList.add('has-cover');
    removeCoverInput.value = '0';
    coverChanged = true;
    checkChanges();
});

// Drag and drop an image on the cover
coverContainer.addEventListener('dragover', (event) => {
    event.preventDefault();
    coverContainer.classList.add('dragover');
});

coverContainer.addEventListener('dragleave', () => {
    coverContainer.classList.remove('dragover');
});

coverContainer.addEventListener('drop', (event) => {
    event.preventDefault();
    coverContainer.classList.remove('dragover');

    if (event.dataTransfer.files.length > 0) {
        coverInput.files = event.dataTransfer.files;
        coverInput.dispatchEvent(new Event('change'));
    }
});

// The cover slightly turns to the mouse
coverContainer.addEventListener('mousemove', (event) => {
    const box = coverContainer.getBoundingClientRect();
    const x = (event.clientX - box.left) / box.width - 0.5;
    const y = (event.clientY - box.top) / box.height - 0.5;
    coverContainer.style.setProperty('--ry', (x * 8) + 'deg');
    coverContainer.style.setProperty('--rx', (-y * 8) + 'deg');
});

coverContainer.addEventListener('mouseleave', () => {
    coverContainer.style.removeProperty('--ry');
    coverContainer.style.removeProperty('--rx');
});

removeCoverBtn.addEventListener('click', () => {
    coverInput.value = '';
    coverWrap.style.removeProperty('--cover');
    coverWrap.classList.remove('has-cover');
    removeCoverInput.value = '1';
    coverChanged = true;
    checkChanges();
});

// Show that the saving is in progress
form.addEventListener('submit', () => {
    isSaving = true;
    saveBtn.classList.add('loading');
    saveText.textContent = 'Saving...';
});

// Ctrl + S (or Cmd + S) saves the tags
document.addEventListener('keydown', (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        if (!saveBtn.disabled) {
            form.requestSubmit();
        }
    }
});

// Warn the user if he wants to leave the page with unsaved changes
window.addEventListener('beforeunload', (event) => {
    if (!saveBtn.disabled && !isSaving) {
        event.preventDefault();
    }
});

checkChanges();

// After a successful save the Download button asks for attention
if (document.querySelector('.toast.success')) {
    downloadBtn.classList.add('attention');
}

// The browser can show the page from its memory when the user presses "Back"
window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
        window.location.reload();
    }
});
