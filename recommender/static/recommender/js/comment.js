async function submitComment(movieId) {
    const textarea = document.getElementById('comment-text');
    const content = textarea.value.trim();
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    if (!content) {
        alert("Please enter a comment before posting.");
        return;
    }

    try {
        const response = await fetch(`/api/v1/movies/${movieId}/comments/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ content: content })
        });

        if (response.ok) {
            const data = await response.json();
            textarea.value = ''; // Clear the input
            
            // Refresh the UI
            // Option 1: Full refresh of movie data
            if (typeof loadMovieData === "function") {
                loadMovieData(); 
            } else {
                location.reload(); // Fallback
            }
        } else {
            const errorData = await response.json();
            alert(errorData.error || "Failed to post comment.");
        }
    } catch (error) {
        console.error("Error posting comment:", error);
    }
}

/**
 * Deletes a comment
 * @param {number} commentId - The ID of the comment to delete
 */
async function deleteComment(commentId) {
    if (!confirm("Are you sure you want to delete this comment?")) return;

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    try {
        const response = await fetch(`/api/v1/comments/${commentId}/`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': csrfToken
            }
        });

        if (response.status === 204) {
            // Successfully deleted, refresh the UI
            if (typeof loadMovieData === "function") {
                loadMovieData();
            } else {
                location.reload();
            }
        } else {
            alert("Could not delete comment. You may not have permission.");
        }
    } catch (error) {
        console.error("Error deleting comment:", error);
    }
}

/**
 * Helper to render the comment list (called from detail.js)
 * @param {Array} comments - The list of comments from the API
 */
function renderComments(comments) {
    const container = document.getElementById('comment-list');
    if (!container) return;

    if (comments.length === 0) {
        container.innerHTML = '<p class="text-muted text-center">No comments yet. Be the first to start the discussion!</p>';
        return;
    }

    container.innerHTML = comments.map(c => `
        <div class="card bg-dark border-secondary mb-3 shadow-sm text-white"> <div class="card-body">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="text-danger fw-bold mb-0">@${c.user}</h6>
                        <small class="text-white-50 extra-small">${c.created_at}</small> </div>
                    ${c.is_owner ? `
                        <button onclick="deleteComment(${c.id})" class="btn btn-sm text-white-50 p-0 border-0 bg-transparent" title="Delete">
                            <small>&times; Delete</small>
                        </button>
                    ` : ''}
                </div>
                <p class="mt-2 mb-0" style="white-space: pre-wrap;">${c.content}</p>
            </div>
        </div>
    `).join('');
}