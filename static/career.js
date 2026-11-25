const campaignRoles = [];
let credentialStatus = {hasLinkedinPassword: false, hasGmailPassword: false};
let toastTimer;
window.resumeUploadedPath = '';
window.resumeUploadedName = '';

const $ = id => document.getElementById(id);
const value = id => $(id).value.trim();
const lines = id => value(id).split(/[\n,]/).map(item => item.trim()).filter(Boolean);

const rolePresets = {
  playwright_sdet: {
    title: 'Playwright Automation Engineer / SDET',
    subject: 'Application for Playwright Automation Engineer / SDET',
    terms: ['Playwright Automation Engineer', 'SDET', 'QA Automation Engineer'],
    body: `Dear Hiring Manager,

I am writing to express my interest in the Playwright Automation Engineer / SDET position.

I have experience with Playwright, TypeScript, JavaScript, and API testing. My work includes page object models, test case design, and CI integration. I would welcome the opportunity to discuss how these skills could help your team.

I have attached my resume for your review.

Best regards,
[FULL_NAME]
[EMAIL]
[PHONE]`
  },
  frontend: {
    title: 'Frontend Developer',
    subject: 'Application for Frontend Developer',
    terms: ['Frontend Developer', 'React Developer', 'UI Developer'],
    body: `Dear Hiring Manager,

I am interested in the Frontend Developer position. My work spans React, TypeScript, JavaScript, responsive UI development, and API integration. I enjoy building clear, reliable interfaces and collaborating closely with product and engineering teams.

I have attached my resume and would welcome a conversation about the role.

Best regards,
[FULL_NAME]
[EMAIL]
[PHONE]`
  }
};

function showNotification(type, title, message = '') {
  const toast = $('toast');
  toast.textContent = message ? `${title}: ${message}` : title;
  toast.classList.toggle('is-error', type === 'error');
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, type === 'error' ? 7000 : 4800);
}

function setView(view) {
  if (!['overview', 'email', 'network', 'activity'].includes(view)) view = 'overview';
  for (const section of document.querySelectorAll('.view')) {
    const active = section.id === `${view}-view`;
    section.hidden = !active;
    section.classList.toggle('is-active', active);
  }
  for (const button of document.querySelectorAll('.nav-link')) {
    const active = button.dataset.view === view;
    button.classList.toggle('is-active', active);
    button.setAttribute('aria-current', active ? 'page' : 'false');
  }
  history.replaceState(null, '', `#${view}`);
  if (view === 'activity') loadHistory();
  if (view === 'network' && typeof refreshNetworkResumes === 'function') refreshNetworkResumes();
  window.scrollTo({top: 0, behavior: 'smooth'});
}

function usePreset() {
  const preset = rolePresets[value('jobRole')];
  if (!preset) return;
  $('customJobTitle').value = preset.title;
  $('emailSubject').value = preset.subject;
  $('searchTerms').value = preset.terms.join('\n');
  $('emailTemplate').value = preset.body;
}

function currentRole() {
  const title = value('customJobTitle');
  const subject = value('emailSubject');
  const searchTerms = lines('searchTerms');
  const emailTemplate = value('emailTemplate');
  const resumeFile = window.resumeUploadedPath;
  if (!title || !subject || !searchTerms.length || !emailTemplate || !resumeFile) {
    throw new Error('Enter a title, subject, search keywords, email message, and upload a resume.');
  }
  return {role: 'custom', customTitle: title, subject, searchTerms, emailTemplate, resumeFile};
}

function renderCampaignRoles() {
  const list = $('campaignRoleList');
  list.replaceChildren();
  if (!campaignRoles.length) {
    const empty = document.createElement('p');
    empty.className = 'empty-copy';
    empty.textContent = 'No roles added yet. Your current draft can still be sent as a single-role campaign.';
    list.append(empty);
    return;
  }
  campaignRoles.forEach((role, index) => {
    const item = document.createElement('div');
    item.className = 'campaign-item';
    const detail = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = role.customTitle || role.role;
    const resume = document.createElement('span');
    resume.textContent = `${(role.resumeFile || '').split(/[\\/]/).pop()} · ${(role.searchTerms || []).length} search terms`;
    detail.append(title, resume);
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.textContent = 'Remove';
    remove.setAttribute('aria-label', `Remove ${title.textContent}`);
    remove.addEventListener('click', () => {
      campaignRoles.splice(index, 1);
      renderCampaignRoles();
      if (typeof refreshNetworkResumes === 'function') refreshNetworkResumes();
    });
    item.append(detail, remove);
    list.append(item);
  });
}

function addCampaignRole() {
  try {
    const role = currentRole();
    campaignRoles.push(role);
    renderCampaignRoles();
    if (typeof refreshNetworkResumes === 'function') refreshNetworkResumes();
    showNotification('success', 'Role added', `${role.customTitle} has its own resume and email.`);
  } catch (error) {
    showNotification('error', 'Role incomplete', error.message);
  }
}

async function uploadResume(file) {
  if (!file) return;
  const form = new FormData();
  form.append('resume', file);
  form.append('snapshot', '1');
  $('resumeUploadStatus').textContent = 'Uploading resume…';
  try {
    const response = await fetch('/api/upload-resume', {method: 'POST', body: form});
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error || 'Upload failed');
    window.resumeUploadedPath = result.path;
    window.resumeUploadedName = file.name;
    $('currentResumeName').textContent = file.name;
    $('resumeUploadStatus').textContent = 'Resume ready for this role.';
    if (typeof refreshNetworkResumes === 'function') refreshNetworkResumes();
    showNotification('success', 'Resume uploaded', file.name);
  } catch (error) {
    $('resumeUploadStatus').textContent = error.message;
    showNotification('error', 'Resume upload failed', error.message);
  }
}

function buildPayload() {
  const roles = campaignRoles.length ? [...campaignRoles] : [currentRole()];
  const first = roles[0];
  const companies = lines('companyFilter').map(name => ({name}));
  const countries = lines('countryFilter').map(name => ({name, searchTerms: name}));
  return {
    personal: {
      fullName: value('fullName'), email: value('email'), phone: value('phone'),
      location: value('location'), website: value('website')
    },
    linkedin: {
      email: value('linkedinEmail'), password: $('linkedinPassword').value,
      profile: value('linkedinProfile'),
      gmail: {senderEmail: value('senderEmail'), senderPassword: $('senderPassword').value}
    },
    job: {
      roles, role: first.role, customTitle: first.customTitle,
      subject: first.subject, searchTerms: first.searchTerms,
      emailTemplate: first.emailTemplate, resumeFile: first.resumeFile,
      botType: 'email', dateFilter: value('dateFilter'),
      emailsPerHour: value('emailsPerHour'), dailyLimit: value('dailyLimit'),
      skipWeekends: $('skipWeekends').checked,
      companyFilter: {enabled: companies.length > 0, companies},
      countryFilter: {enabled: countries.length > 0, countries}
    }
  };
}

async function postConfiguration(url, button) {
  const payload = buildPayload();
  if (!payload.personal.fullName || !payload.personal.email || !payload.personal.phone || !payload.personal.location) {
    throw new Error('Complete your name, email, phone, and location.');
  }
  if (url.includes('start-email') && !($('senderPassword').value || credentialStatus.hasGmailPassword)) {
    throw new Error('Enter your Gmail app password before starting the email extractor.');
  }
  button.disabled = true;
  try {
    const response = await fetch(url, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
    });
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error || 'Request failed');
    credentialStatus.hasLinkedinPassword = true;
    if (payload.linkedin.gmail.senderPassword) credentialStatus.hasGmailPassword = true;
    return result;
  } finally {
    button.disabled = false;
  }
}

async function saveCampaign() {
  try {
    await postConfiguration('/api/save-config', $('saveConfigBtn'));
    showNotification('success', 'Campaign saved', 'Your roles and settings are ready.');
  } catch (error) {
    showNotification('error', 'Could not save campaign', error.message);
  }
}

async function startEmailExtractor() {
  try {
    await postConfiguration('/api/start-email-extractor', $('startEmailBot'));
    showNotification('success', 'Email extractor started', 'The browser is opening LinkedIn.');
    await updateStats();
  } catch (error) {
    showNotification('error', 'Could not start extractor', error.message);
  }
}

async function stopEmailExtractor() {
  try {
    const response = await fetch('/api/stop-bot', {method: 'POST'});
    const result = await response.json();
    if (!result.success) throw new Error(result.error || 'Could not stop extractor');
    showNotification('info', 'Email extractor stopped', result.message);
    await updateStats();
  } catch (error) {
    showNotification('error', 'Could not stop extractor', error.message);
  }
}

async function previewEmail() {
  const template = value('emailTemplate');
  if (!template) {
    showNotification('error', 'Nothing to preview', 'Write an email message first.');
    return;
  }
  try {
    const response = await fetch('/api/format-email', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
        template,
        personal: {
          fullName: value('fullName'), email: value('email'), phone: value('phone'),
          website: value('website'), location: value('location')
        }
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Preview failed');
    $('previewSubject').textContent = value('emailSubject') || 'Your message';
    $('emailPreviewFrame').srcdoc = result.html;
    $('emailPreviewDialog').showModal();
  } catch (error) {
    showNotification('error', 'Preview failed', error.message);
  }
}

async function loadSavedConfiguration() {
  try {
    const response = await fetch('/api/load-config');
    const result = await response.json();
    if (!response.ok || !result.success) return;
    const personal = result.config?.personal || {};
    for (const key of ['fullName', 'email', 'phone', 'location', 'website']) $(key).value = personal[key] || '';
    const job = result.config?.job || {};
    if (Array.isArray(job.roles) && job.roles.length) campaignRoles.splice(0, campaignRoles.length, ...job.roles);
    renderCampaignRoles();
    const current = job.roles?.[0] || job;
    $('jobRole').value = rolePresets[job.role] ? job.role : 'custom';
    $('customJobTitle').value = current.customTitle || (current.role === 'custom' ? '' : current.role || '');
    $('emailSubject').value = current.subject || '';
    $('searchTerms').value = (current.searchTerms || []).join('\n');
    $('emailTemplate').value = current.emailTemplate || '';
    window.resumeUploadedPath = current.resumeFile || '';
    window.resumeUploadedName = (current.resumeFile || '').split(/[\\/]/).pop();
    if (window.resumeUploadedName) $('currentResumeName').textContent = window.resumeUploadedName;
    $('dateFilter').value = job.dateFilter || 'past-week';
    $('emailsPerHour').value = job.emailsPerHour ?? '20';
    $('dailyLimit').value = job.dailyLimit ?? '100';
    $('skipWeekends').checked = Boolean(job.skipWeekends);
    $('companyFilter').value = (job.companyFilter?.companies || []).map(item => item.name || item).join('\n');
    $('countryFilter').value = (job.countryFilter?.countries || []).map(item => item.name || item).join('\n');
  } catch (error) {
    showNotification('error', 'Could not load saved campaign', error.message);
  }
}

async function loadCredentialStatus() {
  try {
    const response = await fetch('/api/credentials-status');
    if (!response.ok) return;
    credentialStatus = await response.json();
    if (!value('linkedinEmail')) $('linkedinEmail').value = credentialStatus.linkedinEmail || '';
    if (!value('senderEmail')) $('senderEmail').value = credentialStatus.gmailEmail || '';
    $('credentialHint').textContent = credentialStatus.hasLinkedinPassword
      ? 'LinkedIn credentials are saved locally. Leave password fields blank to keep them.'
      : 'Enter your LinkedIn details to save or start a campaign.';
  } catch (_) { /* Status polling will show a disconnected server. */ }
}

async function updateStats() {
  try {
    const response = await fetch('/api/stats');
    if (!response.ok) throw new Error('Server unavailable');
    const stats = await response.json();
    const extractor = stats.email_extractor || {};
    $('emailsSent').textContent = extractor.emails_sent || 0;
    const status = extractor.status || 'stopped';
    $('appStatus').classList.toggle('is-ready', status === 'running');
    $('appStatus').classList.toggle('is-error', status === 'error');
    $('appStatus').lastChild.textContent = status === 'running' ? 'Extractor running' : status === 'error' ? 'Needs attention' : 'Ready';
    $('botStatus').textContent = status === 'running' ? 'Email extractor is running' : status === 'error' ? 'Email extractor needs attention' : 'Email extractor is idle';
    $('botProgressText').textContent = extractor.detailed_status || (status === 'running' ? 'Searching and processing LinkedIn posts.' : 'Your saved campaign is ready when you are.');
  } catch (_) {
    $('appStatus').classList.remove('is-ready');
    $('appStatus').classList.add('is-error');
    $('appStatus').lastChild.textContent = 'Offline';
  }
}

async function loadHistory() {
  try {
    const response = await fetch('/api/history');
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error || 'History unavailable');
    const items = result.applications || [];
    $('historyCount').textContent = `${items.length} recorded application emails`;
    const body = $('historyTableBody');
    body.replaceChildren();
    if (!items.length) {
      const row = body.insertRow();
      const cell = row.insertCell();
      cell.colSpan = 4;
      cell.className = 'empty-copy';
      cell.textContent = 'No application emails have been recorded yet.';
      return;
    }
    for (const item of items.slice(0, 100)) {
      const row = body.insertRow();
      for (const text of [item.date || '', item.subject || item.position || '', item.email || '', item.status || '']) {
        row.insertCell().textContent = text;
      }
    }
  } catch (error) {
    $('historyCount').textContent = error.message;
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  document.querySelectorAll('[data-go]').forEach(button => button.addEventListener('click', event => {
    event.preventDefault();
    setView(button.dataset.go);
  }));
  document.querySelectorAll('.nav-link').forEach(button => button.addEventListener('click', () => setView(button.dataset.view)));
  $('jobRole').addEventListener('change', usePreset);
  $('addCampaignRoleButton').addEventListener('click', addCampaignRole);
  $('resumeFile').addEventListener('change', event => uploadResume(event.target.files[0]));
  $('previewEmailBtn').addEventListener('click', previewEmail);
  $('closePreviewBtn').addEventListener('click', () => $('emailPreviewDialog').close());
  $('saveConfigBtn').addEventListener('click', saveCampaign);
  $('startEmailBot').addEventListener('click', startEmailExtractor);
  $('stopEmailBot').addEventListener('click', stopEmailExtractor);
  $('refreshHistoryBtn').addEventListener('click', loadHistory);
  $('startNetworkBtn').addEventListener('click', () => startNetworkSearch());
  $('stopNetworkBtn').addEventListener('click', () => stopNetworkSearch());
  await loadSavedConfiguration();
  await loadCredentialStatus();
  setView(location.hash.slice(1) || 'overview');
  await updateStats();
  setInterval(updateStats, 5000);
});
