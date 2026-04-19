/**
 * Kitap Keşif Sistemi — Frontend Logic
 * Hikaye tabanlı kitap keşif akışı
 */

const API_BASE = window.location.origin;

// ── State ──────────────────────────────────────────────────
const state = {
    selectedBooks: new Map(),
    searchTimeout: null,
    // Discovery session
    sessionBooks: [],    // list of book IDs from vector search
    currentAttempt: 0,
    maxAttempts: 6,
    isLoading: false,
};

// ── DOM Elements ───────────────────────────────────────────
const $searchInput = document.getElementById("searchInput");
const $searchResults = document.getElementById("searchResults");
const $searchSpinner = document.getElementById("searchSpinner");
const $selectedBooks = document.getElementById("selectedBooks");
const $selectedCount = document.getElementById("selectedCount");
const $promptInput = document.getElementById("promptInput");
const $btnDiscover = document.getElementById("btnDiscover");
const $storyArea = document.getElementById("storyArea");
const $attemptBadge = document.getElementById("attemptBadge");

// ── Search ─────────────────────────────────────────────────
$searchInput.addEventListener("input", () => {
    clearTimeout(state.searchTimeout);
    const q = $searchInput.value.trim();
    if (q.length < 2) { hideSearchResults(); return; }
    $searchSpinner.classList.add("active");
    state.searchTimeout = setTimeout(() => searchBooks(q), 300);
});

document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-wrapper")) hideSearchResults();
});

async function searchBooks(query) {
    try {
        const res = await fetch(`${API_BASE}/api/books/search?q=${encodeURIComponent(query)}`);
        const books = await res.json();
        renderSearchResults(books);
    } catch (err) {
        console.error("Search error:", err);
    } finally {
        $searchSpinner.classList.remove("active");
    }
}

function renderSearchResults(books) {
    if (!books.length) {
        $searchResults.innerHTML = `<div style="padding:1rem;text-align:center;color:var(--text-muted);font-size:0.9rem;">Sonuç bulunamadı</div>`;
        $searchResults.classList.add("visible");
        return;
    }

    $searchResults.innerHTML = books.map(book => {
        const isSelected = state.selectedBooks.has(book.id);
        return `
            <div class="search-result-item ${isSelected ? "selected" : ""}"
                 data-id="${book.id}"
                 data-title="${escapeAttr(book.title)}"
                 data-author="${escapeAttr(book.author_name)}"
                 data-img="${escapeAttr(book.image_url)}">
                <img class="search-result-img" src="${escapeAttr(book.image_url)}" alt=""
                     onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 36 50%22><rect fill=%22%23374151%22 width=%2236%22 height=%2250%22 rx=%224%22/><text x=%2218%22 y=%2228%22 fill=%22%239ca3af%22 font-size=%2210%22 text-anchor=%22middle%22>📖</text></svg>'">
                <div class="search-result-info">
                    <div class="search-result-title">${escapeHtml(book.title)}</div>
                    <div class="search-result-author">${escapeHtml(book.author_name)}</div>
                </div>
                <span class="search-result-add">${isSelected ? "✓" : "+"}</span>
            </div>`;
    }).join("");

    $searchResults.classList.add("visible");

    $searchResults.querySelectorAll(".search-result-item:not(.selected)").forEach(el => {
        el.addEventListener("click", () => {
            addBook({
                id: el.dataset.id,
                title: el.dataset.title,
                author_name: el.dataset.author,
                image_url: el.dataset.img,
            });
            el.classList.add("selected");
            el.querySelector(".search-result-add").textContent = "✓";
        });
    });
}

function hideSearchResults() {
    $searchResults.classList.remove("visible");
}

// ── Book Selection ─────────────────────────────────────────
function addBook(book) {
    if (state.selectedBooks.has(book.id)) return;
    state.selectedBooks.set(book.id, book);
    renderSelectedBooks();
    updateDiscoverButton();
}

function removeBook(id) {
    state.selectedBooks.delete(id);
    renderSelectedBooks();
    updateDiscoverButton();
}

function renderSelectedBooks() {
    $selectedCount.textContent = state.selectedBooks.size;
    if (state.selectedBooks.size === 0) {
        $selectedBooks.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">🔍</span>
                <p>Henüz kitap seçmediniz</p>
                <p class="empty-hint">Yukarıdan arayarak sevdiğiniz kitapları ekleyin</p>
            </div>`;
        return;
    }

    $selectedBooks.innerHTML = "";
    state.selectedBooks.forEach((book, id) => {
        const chip = document.createElement("div");
        chip.className = "book-chip";
        chip.innerHTML = `
            <img class="chip-img" src="${escapeAttr(book.image_url)}" alt=""
                 onerror="this.style.display='none'">
            <span class="chip-title">${escapeHtml(book.title)}</span>
            <button class="chip-remove" title="Kaldır">&times;</button>`;
        chip.querySelector(".chip-remove").addEventListener("click", () => removeBook(id));
        $selectedBooks.appendChild(chip);
    });
}

function updateDiscoverButton() {
    const hasBooks = state.selectedBooks.size > 0;
    const hasPrompt = $promptInput.value.trim().length > 0;
    $btnDiscover.disabled = !(hasBooks || hasPrompt) || state.isLoading;
}

$promptInput.addEventListener("input", updateDiscoverButton);

// ── Discovery Flow ─────────────────────────────────────────
$btnDiscover.addEventListener("click", startDiscovery);

async function startDiscovery() {
    const bookIds = Array.from(state.selectedBooks.keys());
    const prompt = $promptInput.value.trim();
    if (!bookIds.length && !prompt) return;

    setLoading(true);
    showStoryLoading();

    try {
        const res = await fetch(`${API_BASE}/api/discover`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ book_ids: bookIds, prompt }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();
        state.sessionBooks = data.session_books;
        state.currentAttempt = data.attempt;
        state.maxAttempts = data.max_attempts;

        showStory(data.story);
    } catch (err) {
        console.error("Discover error:", err);
        showError(err.message);
    } finally {
        setLoading(false);
    }
}

async function handleDislike() {
    if (state.currentAttempt >= state.maxAttempts) {
        showFailState();
        return;
    }

    setLoading(true);
    showStoryLoading();

    try {
        const res = await fetch(`${API_BASE}/api/story/next`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_books: state.sessionBooks,
                current_attempt: state.currentAttempt,
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        const data = await res.json();
        state.currentAttempt = data.attempt;
        showStory(data.story);
    } catch (err) {
        console.error("Next story error:", err);
        showError(err.message);
    } finally {
        setLoading(false);
    }
}

async function handleLike() {
    setLoading(true);

    try {
        const res = await fetch(`${API_BASE}/api/story/reveal`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_books: state.sessionBooks,
                current_attempt: state.currentAttempt,
            }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || `HTTP ${res.status}`);
        }

        const book = await res.json();
        showReveal(book);
    } catch (err) {
        console.error("Reveal error:", err);
        showError(err.message);
    } finally {
        setLoading(false);
    }
}

// ── UI Renderers ───────────────────────────────────────────
function showStoryLoading() {
    $storyArea.innerHTML = `
        <div class="story-loading">
            <span class="story-loading-icon">✍️</span>
            <p>Hikaye yazılıyor...</p>
            <p class="empty-hint">Bu birkaç saniye sürebilir</p>
        </div>`;
    $attemptBadge.style.display = "none";
}

function showStory(storyText) {
    // Format story with paragraphs
    const paragraphs = storyText.split(/\n\n+/).filter(p => p.trim());
    const formattedStory = paragraphs.map(p => `<p>${escapeHtml(p.trim())}</p>`).join("");

    $attemptBadge.textContent = `${state.currentAttempt} / ${state.maxAttempts}`;
    $attemptBadge.style.display = "inline-block";

    $storyArea.innerHTML = `
        <div class="story-card">
            <div class="story-label">
                <span>📜</span> Bu hikaye hoşuna gider mi?
            </div>
            <div class="story-text">${formattedStory}</div>
            <div class="story-actions">
                <button class="btn-action btn-like" id="btnLike">
                    <span class="action-icon">👍</span>
                    <span>Beğendim!</span>
                </button>
                <button class="btn-action btn-dislike" id="btnDislike">
                    <span class="action-icon">👎</span>
                    <span>Başka bak</span>
                </button>
            </div>
            ${renderProgressDots()}
        </div>`;

    document.getElementById("btnLike").addEventListener("click", handleLike);
    document.getElementById("btnDislike").addEventListener("click", handleDislike);
}

function renderProgressDots() {
    let dots = "";
    for (let i = 1; i <= state.maxAttempts; i++) {
        let cls = "progress-dot";
        if (i === state.currentAttempt) cls += " active";
        else if (i < state.currentAttempt) cls += " disliked";
        dots += `<div class="${cls}"></div>`;
    }
    return `<div class="progress-dots">${dots}</div>`;
}

function showReveal(book) {
    $attemptBadge.style.display = "none";

    $storyArea.innerHTML = `
        <div class="reveal-card">
            <div class="reveal-inner">
                <div class="reveal-header">🎉 İşte bu hikayenin arkasındaki kitap!</div>
                <div class="reveal-book">
                    <img class="reveal-img" src="${escapeAttr(book.image_url)}" alt="${escapeAttr(book.title)}"
                         onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 120 175%22><rect fill=%22%23374151%22 width=%22120%22 height=%22175%22 rx=%228%22/><text x=%2260%22 y=%2295%22 fill=%22%239ca3af%22 font-size=%2224%22 text-anchor=%22middle%22>📖</text></svg>'">
                    <div class="reveal-info">
                        <div class="reveal-title">${escapeHtml(book.title)}</div>
                        <div class="reveal-author">${escapeHtml(book.author_name)}</div>
                        <div class="reveal-desc">${escapeHtml(book.description)}</div>
                        <div class="reveal-rating">⭐ ${book.average_rating.toFixed(1)}</div>
                    </div>
                </div>
                <button class="btn-restart" id="btnRestart">🔄 Yeni Keşif Başlat</button>
            </div>
        </div>`;

    document.getElementById("btnRestart").addEventListener("click", resetSession);
}

function showFailState() {
    $attemptBadge.style.display = "none";

    $storyArea.innerHTML = `
        <div class="fail-card">
            <span class="fail-icon">😔</span>
            <div class="fail-title">Maalesef istediğin kitabı bulamadık</div>
            <div class="fail-text">6 farklı hikaye denedik ama hiçbiri ilgini çekmedi.<br>Farklı kitaplar seçerek veya başka bir açıklama yazarak tekrar deneyebilirsin!</div>
            <button class="btn-restart" id="btnRestart">🔄 Tekrar Dene</button>
        </div>`;

    document.getElementById("btnRestart").addEventListener("click", resetSession);
}

function showError(message) {
    $storyArea.innerHTML = `
        <div class="empty-state">
            <span class="empty-icon">❌</span>
            <p>Bir hata oluştu</p>
            <p class="empty-hint">${escapeHtml(message)}</p>
        </div>`;
}

function resetSession() {
    state.sessionBooks = [];
    state.currentAttempt = 0;
    $attemptBadge.style.display = "none";
    $storyArea.innerHTML = `
        <div class="empty-state">
            <span class="empty-icon">💡</span>
            <p>Kitap seçin veya ne istediğinizi yazın</p>
            <p class="empty-hint">"Hikaye Keşfet" butonuna tıklayın</p>
        </div>`;
    updateDiscoverButton();
}

function setLoading(loading) {
    state.isLoading = loading;
    $btnDiscover.classList.toggle("loading", loading);
    updateDiscoverButton();
}

// ── Utilities ──────────────────────────────────────────────
function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function escapeAttr(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/'/g, "&#39;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
