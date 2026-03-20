// watchlist.js

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

async function loadWatchlist() {
    try {
        const response = await fetch('/api/v1/watchlist/');
        const data = await response.json();
        
        const watchlistGrid = document.getElementById('watchlist-grid');
        const suggestionsGrid = document.getElementById('suggestions-grid');
        
        watchlistGrid.innerHTML = ''; 
        suggestionsGrid.innerHTML = '';

        if (data.watchlist.length === 0) {
            watchlistGrid.innerHTML = '<div class="col-12 text-center text-muted"><h4>Your watchlist is empty</h4></div>';
        } else {
            data.watchlist.forEach(movie => {
                watchlistGrid.innerHTML += renderMovieCard(movie, 'watchlist');
            });
        }

        if (data.suggestions.length === 0) {
            suggestionsGrid.innerHTML = '<p class="text-muted ps-3">Add more movies to see suggestions!</p>';
        } else {
            data.suggestions.forEach(movie => {
                suggestionsGrid.innerHTML += renderMovieCard(movie, 'suggestion');
            });
        }
        
        document.getElementById('watchlist-count').innerText = `${data.watchlist.length} movies saved for later.`;
    } catch (err) {
        console.error("API Error:", err);
    }
}

function renderMovieCard(movie, type) {
    if (type === 'watchlist') {
        return `
            <div class="col" id="movie-card-${movie.id}">
                <div class="card shadow-sm h-100">
                    <img src="${movie.poster}" class="card-img-top" onclick="location.href='/movie/${movie.id}/'" style="cursor:pointer">
                    <div class="card-body">
                        <h5 class="card-title text-truncate" style="font-size: 0.9rem; color: #b3b3b3;">${movie.title}</h5>
                        <button onclick="deleteFromWatchlist(${movie.id})" class="btn btn-sm btn-outline-secondary w-100">Remove</button>
                    </div>
                </div>
            </div>`;
    } else {
        return `
            <div class="col" id="rec-card-${movie.id}">
                <div class="card bg-dark border-0 shadow-lg h-100">
                    <img src="${movie.poster}" class="card-img-top" onclick="location.href='/movie/${movie.id}/'" style="cursor:pointer">
                    <div class="card-body p-2">
                        <h6 class="card-title text-truncate small mb-1 text-white" style="color: #b3b3b3;">${movie.title}</h6>
                        <button onclick="addToWatchlist(${movie.id}, this)" class="btn btn-sm btn-danger w-100">+ Add</button>
                    </div>
                </div>
            </div>`;
    }
}

async function deleteFromWatchlist(movieId) {
    const response = await fetch(`/api/v1/watchlist/${movieId}/`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    });
    if (response.ok) loadWatchlist(); // Refresh the UI
}

async function addToWatchlist(movieId, btn) {
    // Put the ID in the URL path to match /api/v1/watchlist/<int:movie_id>/
    const response = await fetch(`/api/v1/watchlist/${movieId}/`, {
        method: 'POST',
        headers: { 
            'X-CSRFToken': getCookie('csrftoken') 
        }
    });
    
    if (response.ok) {
        loadWatchlist(); // This will refresh the grids automatically
    } else {
        console.error("Failed to add movie");
    }
}

function handleWatchlistUIUpdate() {
    // 1. If we are on the Watchlist Page (grids exist)
    if (document.getElementById('watchlist-grid')) {
        loadWatchlist();
    } 
    // 2. If we are on the Detail Page (loadMovieData exists)
    else if (typeof loadMovieData === 'function') {
        loadMovieData(); 
    }
}

// Start the app
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('watchlist-grid')) {
        loadWatchlist();
    }
});