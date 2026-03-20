// static/recommender/js/auth.js

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

// RESTful Logout (DELETE)
async function handleLogout() {
    try {
        const response = await fetch('/api/v1/auth/logout/', { 
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });

        if (response.status === 204) {
            window.location.href = '/login/'; // Or wherever your login page is
        }
    } catch (err) {
        console.error("Logout error:", err);
    }
}

// RESTful Login (POST)
async function handleLogin(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData.entries());

    try {
        const response = await fetch('/api/v1/auth/login/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            window.location.href = '/'; 
        } else {
            const errData = await response.json();
            alert(errData.error || "Login failed");
        }
    } catch (err) {
        console.error("Login error:", err);
    }
}

// RESTful Register (POST)
async function handleRegister(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    const data = Object.fromEntries(formData.entries());

    try {
        const response = await fetch('/api/v1/auth/register/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(data)
        });

        if (response.status === 201) {
            window.location.href = '/login/';
        } else {
            const errData = await response.json();
            alert(errData.error || "Registration failed");
        }
    } catch (err) {
        console.error("Registration error:", err);
    }
}