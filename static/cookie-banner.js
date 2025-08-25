
// Cookie Banner and Consent Management
class CookieConsent {
  constructor() {
    this.CONSENT_KEY = 'gradvantage_cookie_consent';
    this.ANALYTICS_CONSENT_KEY = 'gradvantage_analytics_consent';
    this.init();
  }

  init() {
    // Check if consent already given
    const consent = localStorage.getItem(this.CONSENT_KEY);
    if (!consent) {
      this.showBanner();
    } else {
      this.loadAnalytics(localStorage.getItem(this.ANALYTICS_CONSENT_KEY) === 'true');
    }
  }

  showBanner() {
    const banner = document.createElement('div');
    banner.id = 'cookie-banner';
    banner.className = 'cookie-banner';
    banner.innerHTML = `
      <div class="cookie-banner-content">
        <div class="cookie-banner-text">
          <h5><i class="bi bi-cookie-bite me-2"></i>Cookie Preferences</h5>
          <p>We use essential cookies to run the site, and optional analytics to improve it. Choose your preference.</p>
        </div>
        <div class="cookie-banner-buttons">
          <button id="accept-all" class="btn btn-primary" data-testid="cookie-accept-all">Accept All</button>
          <button id="reject-optional" class="btn btn-outline-secondary" data-testid="cookie-reject-optional">Reject Non-Essential</button>
          <button id="manage-cookies" class="btn btn-link" data-testid="cookie-manage">Manage</button>
        </div>
      </div>
    `;

    document.body.appendChild(banner);

    // Add event listeners
    document.getElementById('accept-all').addEventListener('click', () => this.acceptAll());
    document.getElementById('reject-optional').addEventListener('click', () => this.rejectOptional());
    document.getElementById('manage-cookies').addEventListener('click', () => this.showSettings());
  }

  acceptAll() {
    localStorage.setItem(this.CONSENT_KEY, 'true');
    localStorage.setItem(this.ANALYTICS_CONSENT_KEY, 'true');
    this.loadAnalytics(true);
    this.hideBanner();
  }

  rejectOptional() {
    localStorage.setItem(this.CONSENT_KEY, 'true');
    localStorage.setItem(this.ANALYTICS_CONSENT_KEY, 'false');
    this.loadAnalytics(false);
    this.hideBanner();
  }

  showSettings() {
    const modal = document.createElement('div');
    modal.className = 'cookie-modal-overlay';
    modal.innerHTML = `
      <div class="cookie-modal">
        <div class="cookie-modal-header">
          <h4>Cookie Settings</h4>
          <button class="btn-close" onclick="this.closest('.cookie-modal-overlay').remove()"></button>
        </div>
        <div class="cookie-modal-body">
          <div class="cookie-category mb-3">
            <div class="form-check form-switch">
              <input class="form-check-input" type="checkbox" id="essential-cookies" checked disabled>
              <label class="form-check-label" for="essential-cookies">
                <strong>Essential Cookies</strong>
              </label>
            </div>
            <p class="text-muted small">Required for the website to function properly. Cannot be disabled.</p>
          </div>
          
          <div class="cookie-category mb-3">
            <div class="form-check form-switch">
              <input class="form-check-input" type="checkbox" id="analytics-cookies">
              <label class="form-check-label" for="analytics-cookies">
                <strong>Analytics Cookies</strong>
              </label>
            </div>
            <p class="text-muted small">Help us understand how visitors use our website via Google Analytics.</p>
          </div>
        </div>
        <div class="cookie-modal-footer">
          <button class="btn btn-primary" onclick="cookieConsent.saveSettings()">Save Preferences</button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Set current state
    const analyticsConsent = localStorage.getItem(this.ANALYTICS_CONSENT_KEY) === 'true';
    document.getElementById('analytics-cookies').checked = analyticsConsent;
  }

  saveSettings() {
    const analyticsConsent = document.getElementById('analytics-cookies').checked;
    localStorage.setItem(this.CONSENT_KEY, 'true');
    localStorage.setItem(this.ANALYTICS_CONSENT_KEY, analyticsConsent.toString());
    this.loadAnalytics(analyticsConsent);
    
    // Remove modal and banner
    document.querySelector('.cookie-modal-overlay')?.remove();
    this.hideBanner();
  }

  hideBanner() {
    const banner = document.getElementById('cookie-banner');
    if (banner) {
      banner.remove();
    }
  }

  loadAnalytics(consent) {
    if (consent && !window.gtag) {
      // Load Google Analytics only if consented
      const script = document.createElement('script');
      script.async = true;
      script.src = 'https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID';
      document.head.appendChild(script);

      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      window.gtag = gtag;
      gtag('js', new Date());
      gtag('config', 'GA_MEASUREMENT_ID');
    }
  }

  // Public method to show settings
  showCookieSettings() {
    this.showSettings();
  }
}

// Initialize cookie consent
const cookieConsent = new CookieConsent();

// Global function for privacy policy link
function showCookieSettings() {
  cookieConsent.showCookieSettings();
}
