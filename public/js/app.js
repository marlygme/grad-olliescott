let currentUser = null;

async function initApp() {
  try {
    currentUser = await api.getCurrentUser();
    updateAuthUI();
  } catch (e) {
    console.log('Not logged in');
  }
}

function updateAuthUI() {
  const authNav = document.getElementById('auth-nav');
  if (!authNav) return;

  if (currentUser) {
    authNav.innerHTML = `
      <a class="btn btn-primary btn-pill" href="submit.html">
        <i class="bi bi-plus-circle me-1"></i>Share Story
      </a>
      <div class="dropdown">
        <button class="btn btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
          <i class="bi bi-person-circle me-1"></i>${currentUser.username || 'User'}
        </button>
        <ul class="dropdown-menu">
          <li><a class="dropdown-item" href="tracker.html">My Applications</a></li>
          <li><hr class="dropdown-divider"></li>
          <li><a class="dropdown-item" href="#" onclick="logout()">Sign Out</a></li>
        </ul>
      </div>
    `;
  } else {
    authNav.innerHTML = `
      <div class="text-muted">
        <i class="bi bi-info-circle me-1"></i>Sign in to share your story
      </div>
    `;
  }
}

function logout() {
  currentUser = null;
  updateAuthUI();
  window.location.href = 'index.html';
}

function formatCurrency(amount) {
  if (!amount) return 'N/A';
  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(amount);
}

function formatDate(dateString) {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleDateString('en-AU', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

function getOutcomeBadgeClass(outcome) {
  switch (outcome?.toLowerCase()) {
    case 'offer':
    case 'success':
      return 'bg-success';
    case 'rejected':
      return 'bg-danger';
    case 'ghosted':
      return 'bg-secondary';
    default:
      return 'bg-warning';
  }
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function showLoading(containerId) {
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = `
      <div class="text-center py-5">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <p class="mt-3 text-muted">Loading...</p>
      </div>
    `;
  }
}

function showError(containerId, message) {
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = `
      <div class="alert alert-danger" role="alert">
        <i class="bi bi-exclamation-triangle me-2"></i>${escapeHtml(message)}
      </div>
    `;
  }
}

function showEmptyState(containerId, message, actionText, actionUrl) {
  const container = document.getElementById(containerId);
  if (container) {
    container.innerHTML = `
      <div class="empty-state text-center py-5">
        <div class="empty-icon mb-4">
          <i class="bi bi-inbox text-muted" style="font-size: 4rem;"></i>
        </div>
        <h4 class="fw-medium mb-3">${escapeHtml(message)}</h4>
        ${actionText && actionUrl ? `
          <a href="${actionUrl}" class="btn btn-primary btn-pill px-4">${escapeHtml(actionText)}</a>
        ` : ''}
      </div>
    `;
  }
}

document.addEventListener('DOMContentLoaded', initApp);
