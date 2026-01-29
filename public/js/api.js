const API_BASE_URL = window.API_BASE_URL || '';

const api = {
  async getCompanies() {
    const response = await fetch(`${API_BASE_URL}/api/companies`);
    if (!response.ok) throw new Error('Failed to fetch companies');
    return response.json();
  },

  async getCompany(name) {
    const response = await fetch(`${API_BASE_URL}/api/companies/${encodeURIComponent(name)}`);
    if (!response.ok) throw new Error('Failed to fetch company');
    return response.json();
  },

  async getExperiences(filters = {}) {
    const params = new URLSearchParams();
    if (filters.company) params.set('company', filters.company);
    if (filters.theme) params.set('theme', filters.theme);
    if (filters.search) params.set('search', filters.search);
    const response = await fetch(`${API_BASE_URL}/api/experiences?${params}`);
    if (!response.ok) throw new Error('Failed to fetch experiences');
    return response.json();
  },

  async getExperience(id) {
    const response = await fetch(`${API_BASE_URL}/api/experiences/${id}`);
    if (!response.ok) throw new Error('Failed to fetch experience');
    return response.json();
  },

  async submitExperience(data) {
    const response = await fetch(`${API_BASE_URL}/api/experiences`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      credentials: 'include'
    });
    if (!response.ok) throw new Error('Failed to submit experience');
    return response.json();
  },

  async getApplications() {
    const response = await fetch(`${API_BASE_URL}/api/applications`, {
      credentials: 'include'
    });
    if (!response.ok) throw new Error('Failed to fetch applications');
    return response.json();
  },

  async createApplication(data) {
    const response = await fetch(`${API_BASE_URL}/api/applications`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      credentials: 'include'
    });
    if (!response.ok) throw new Error('Failed to create application');
    return response.json();
  },

  async updateApplication(id, data) {
    const response = await fetch(`${API_BASE_URL}/api/applications/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      credentials: 'include'
    });
    if (!response.ok) throw new Error('Failed to update application');
    return response.json();
  },

  async deleteApplication(id) {
    const response = await fetch(`${API_BASE_URL}/api/applications/${id}`, {
      method: 'DELETE',
      credentials: 'include'
    });
    if (!response.ok) throw new Error('Failed to delete application');
    return response.json();
  },

  async getCurrentUser() {
    const response = await fetch(`${API_BASE_URL}/api/user`, {
      credentials: 'include'
    });
    if (!response.ok) return null;
    return response.json();
  },

  async getLawMatch(data) {
    const response = await fetch(`${API_BASE_URL}/api/law-match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error('Failed to get law match');
    return response.json();
  },

  async getFirmUniversityData() {
    const response = await fetch(`${API_BASE_URL}/api/firm-university-data`);
    if (!response.ok) throw new Error('Failed to fetch firm university data');
    return response.json();
  }
};

window.api = api;
