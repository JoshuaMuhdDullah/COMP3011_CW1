// details.js

// Helper to get CSRF token from cookies (needed for POST/DELETE)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener('DOMContentLoaded', function() {
    const container = document.getElementById('detail-container');
    const movieId = container.dataset.movieId;
    const isAuthenticated = container.dataset.userAuthenticated === 'true';
    const loadingOverlay = document.getElementById('loading-overlay');

    function loadMovieData() {
        fetch(`/api/v1/movies/${movieId}/`)
            .then(response => {
                if (!response.ok) throw new Error('Network response was not ok');
                return response.json();
            })
            .then(data => {
                // 1. Update Basic Info
                document.getElementById('movie-title').textContent = data.title;
                document.getElementById('movie-overview').textContent = data.overview;
                document.getElementById('movie-rating').textContent = `⭐ ${data.rating}`;
                document.getElementById('movie-year').textContent = `(${data.released_year})`;
                document.getElementById('movie-director').textContent = data.director;
                document.getElementById('movie-genre').textContent = data.genre;

                // 2. Handle Watchlist Button State (THE TOGGLE)
                const authActions = document.getElementById('auth-actions');
                if (isAuthenticated) {
                    const isIn = data.is_in_watchlist; 
                    
                    // 1. Create the button HTML WITHOUT an onclick attribute
                    authActions.innerHTML = `
                        <button id="watchlist-btn" 
                                class="btn ${isIn ? 'btn-danger' : 'btn-outline-danger'} fw-bold px-4 py-2">
                            ${isIn ? '− Remove from Watchlist' : '+ Add to Watchlist'}
                        </button>
                    `;

                    // 2. Immediately find that button in the DOM and attach the listener
                    const btn = document.getElementById('watchlist-btn');
                    btn.addEventListener('click', async function() {
                        // Disable button briefly to prevent double-clicks
                        btn.disabled = true;
                        btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';

                        const method = isIn ? 'DELETE' : 'POST';
                        const response = await fetch(`/api/v1/watchlist/${data.id}/`, {
                            method: method,
                            headers: { 
                                'X-CSRFToken': getCookie('csrftoken'),
                                'Content-Type': 'application/json'
                            }
                        });

                        if (response.ok) {
                            // SUCCESS: Re-run the main data loader to flip the button state
                            console.log("Success! Re-loading movie data...");
                            loadMovieData(); 
                        } else {
                            console.error("Failed to update watchlist");
                            loadMovieData(); // Reset button state
                        }
                    });
                }

                // 3. Handle Poster
                const posterImg = document.getElementById('movie-poster');
                posterImg.src = data.poster;
                posterImg.onload = () => posterImg.style.opacity = 1;

                // 4. Inject Recommendations
                const recContainer = document.getElementById('recommendations-grid');
                if (data.recommendations.length > 0) {
                    recContainer.innerHTML = data.recommendations.map(rec => `
                        <div class="col">
                            <div class="rec-card card h-100 bg-dark border-0 shadow-sm" onclick="location.href='/movie/${rec.id}/'">
                                <img src="${rec.poster}" class="card-img-top" alt="${rec.title}">
                                <div class="card-body p-2 text-center">
                                    <p class="small text-truncate mb-0 text-white">${rec.title}</p>
                                    <span class="text-muted extra-small">★ ${rec.rating}</span>
                                </div>
                            </div>
                        </div>
                    `).join('');
                }

                // 5. Inject Comment Form
                const formContainer = document.getElementById('comment-form-container');
                if (isAuthenticated) {
                    formContainer.innerHTML = `
                        <div class="mb-4">
                            <textarea id="comment-text" class="form-control bg-dark text-white border-secondary mb-2" rows="3" placeholder="Write a comment..."></textarea>
                            <div class="d-flex justify-content-end">
                                <button onclick="submitComment(${data.id})" class="btn btn-danger px-4 btn-sm fw-bold">Post Comment</button>
                            </div>
                        </div>`;
                }

                // 6. Render Comments
                if (typeof renderComments === 'function') {
                    renderComments(data.comments);
                }

                if (loadingOverlay) loadingOverlay.style.display = 'none';
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }

    // Assign to window so other scripts can call it
    window.loadMovieData = loadMovieData;
    loadMovieData();
});

// --- WATCHLIST FUNCTIONS ---

async function addToWatchlist(movieId) {
    console.log("API CALL: Adding...", movieId);
    const response = await fetch(`/api/v1/watchlist/${movieId}/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    });
    if (response.ok) window.loadMovieData();
}

async function deleteFromWatchlist(movieId) {
    console.log("API CALL: Removing...", movieId);
    const response = await fetch(`/api/v1/watchlist/${movieId}/`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    });
    if (response.ok) window.loadMovieData();
}