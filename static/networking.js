const networkCards = new Map();

function networkLines(id) {
    return document.getElementById(id).value.split(/[\n,]/).map(value => value.trim()).filter(Boolean);
}

function safeLinkedInLink(value) {
    try {
        const url = new URL(value);
        return ['linkedin.com', 'www.linkedin.com'].includes(url.hostname) && url.protocol === 'https:' ? url.href : '';
    } catch (_) {
        return '';
    }
}

function prepareNetworkDefaults(config) {
    const job = config.job || {};
    const personal = config.personal || {};
    const mode = document.getElementById('networkSearchMode');
    updateNetworkModeHint(mode.value);
    if (!document.getElementById('networkLocations').value) {
        document.getElementById('networkLocations').value = personal.location || '';
    }
    if (!document.getElementById('networkTitles').value) {
        const titles = (job.roles || []).map(role => role.customTitle || role.role).filter(Boolean);
        if (!titles.length) titles.push(job.customTitle || job.role || '');
        document.getElementById('networkTitles').value = titles.filter(Boolean).join('\n');
    }
    if (!document.getElementById('networkSkills').value) {
        const terms = job.searchTerms || job.roles?.flatMap(role => role.searchTerms || []) || [];
        document.getElementById('networkSkills').value = terms.slice(0, 5).join(', ');
    }
}

function updateNetworkModeHint(mode) {
    document.getElementById('networkModeHint').textContent = mode === 'referral_contacts'
        ? 'One target role, alternate-title, or skill word in the headline is enough. About, experience, and location are ignored.'
        : 'Loose headline match: one related word is enough. About, experience, and location are ignored.';
}

async function startNetworkSearch() {
    const payload = {
        searchMode: document.getElementById('networkSearchMode').value,
        locations: networkLines('networkLocations'),
        titles: networkLines('networkTitles'),
        alternateTitles: networkLines('networkAlternateTitles'),
        skills: networkLines('networkSkills'),
        hiringText: document.getElementById('networkHiringText').value.trim()
    };
    const email = document.getElementById('linkedinEmail').value.trim();
    const password = document.getElementById('linkedinPassword').value;
    if (email && password) payload.linkedin = {email, password};
    try {
        const response = await fetch('/api/network/search', {
            method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Search could not start');
        networkCards.clear();
        document.getElementById('networkJobs').replaceChildren();
        document.getElementById('networkPeople').replaceChildren();
        renderNetworkState(result);
        showNotification('info', 'Networking search started', 'LinkedIn is opening in a browser.');
    } catch (error) {
        document.getElementById('networkStatus').textContent = error.message;
        showNotification('error', 'Search failed', error.message);
    }
}

async function stopNetworkSearch() {
    try {
        const response = await fetch('/api/network/stop', {method: 'POST'});
        renderNetworkState(await response.json());
    } catch (error) {
        showNotification('error', 'Could not close browser', error.message);
    }
}

function appendLinkedInLink(parent, label, url) {
    const safe = safeLinkedInLink(url);
    if (!safe) return;
    const link = document.createElement('a');
    link.href = safe;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.className = 'result-link';
    link.textContent = label;
    parent.append(link);
}

function renderNetworkJobs(jobs) {
    const container = document.getElementById('networkJobs');
    container.replaceChildren();
    if (!jobs.length) {
        container.innerHTML = '<p class="empty-copy">No matching jobs found yet.</p>';
        return;
    }
    for (const job of jobs) {
        const card = document.createElement('div');
        card.className = 'job-item';
        const heading = document.createElement('div');
        heading.className = 'job-title';
        appendLinkedInLink(heading, job.title, job.url);
        const details = document.createElement('p');
        details.textContent = [job.company, job.location, job.posted].filter(Boolean).join(' · ');
        const match = document.createElement('p');
        match.className = 'job-match';
        match.textContent = `${job.score}% match${job.reasons?.length ? ' · ' + job.reasons.join(' · ') : ''}`;
        card.append(heading, details, match);
        container.append(card);
    }
}

function renderNetworkPeople(people, state = {}) {
    const container = document.getElementById('networkPeople');
    if (!people.length) {
        networkCards.clear();
        const scan = state.profileScan || {};
        const emptyText = state.status === 'searching'
            ? (scan.discovered ? `Checking profile ${scan.checked || 0} of ${scan.discovered}; ${scan.qualified || 0} matched so far...` : 'Searching LinkedIn for profiles...')
            : 'No profiles matched this search mode.';
        const empty = document.createElement('p');
        empty.className = 'empty-copy';
        empty.textContent = emptyText;
        container.replaceChildren(empty);
        return;
    }
    if (container.querySelector('.empty-copy')) container.replaceChildren();
    for (const person of people) {
        let card = networkCards.get(person.id);
        if (!card) {
            card = document.createElement('div');
            card.className = 'person-item';
            card.dataset.candidateId = person.id;
            const heading = document.createElement('div');
            heading.className = 'person-links';
            appendLinkedInLink(heading, person.name && person.name !== 'View' ? person.name : 'View profile', person.profileUrl);
            if (person.postUrl) {
                heading.append(document.createTextNode(' · '));
                appendLinkedInLink(heading, 'View post', person.postUrl);
            }
            const context = document.createElement('p');
            context.className = 'person-meta';
            context.textContent = [person.headline, person.company].filter(Boolean).join(' · ');
            const match = document.createElement('p');
            match.className = 'job-match';
            match.textContent = person.matchReason || person.topic || '';
            const excerpt = document.createElement('p');
            excerpt.className = 'post-context';
            excerpt.textContent = person.excerpt || '';
            excerpt.hidden = !excerpt.textContent;
            const note = document.createElement('textarea');
            note.className = 'note-editor';
            note.rows = 3;
            note.maxLength = 200;
            note.value = person.note;
            note.setAttribute('aria-label', `Reviewed LinkedIn connection note for ${person.name}`);
            const count = document.createElement('span');
            count.className = 'note-count';
            note.addEventListener('input', () => { count.textContent = `${note.value.length}/200 characters`; });
            count.textContent = `${note.value.length}/200 characters`;
            const status = document.createElement('span');
            status.className = 'note-state';
            status.dataset.role = 'status';
            const actions = document.createElement('div');
            actions.className = 'note-actions';
            actions.append(count);
            card.append(heading, context, match, excerpt, note, actions, status);
            networkCards.set(person.id, card);
            container.append(card);
        }
        const status = card.querySelector('[data-role="status"]');
        const note = card.querySelector('.note-editor');
        note.disabled = !['draft', 'error'].includes(person.status);
        const sentLabel = person.status === 'sent'
            ? (person.deliveryMethod === 'direct_message' ? 'LinkedIn message sent' : 'Connection note sent')
            : person.status;
        status.textContent = person.error || (person.warning
            ? `${person.status === 'sent' ? 'Sent with warning' : sentLabel}: ${person.warning}`
            : (state.status !== 'ready' && ['draft', 'error'].includes(person.status)
                ? 'Draft saved. Run a people search and keep the LinkedIn browser open to send it.'
                : sentLabel));
        status.classList.toggle('is-error', ['error', 'uncertain', 'duplicate'].includes(person.status));
        status.classList.toggle('is-sent', person.status === 'sent');
    }
}

function renderNetworkState(state) {
    const status = document.getElementById('networkStatus');
    const last = state.lastProfileCheck || {};
    const checkedHeadline = state.status === 'searching' && (last.headline || last.name || last.reason)
        ? `\nLast checked: ${last.name || 'Name unavailable'} | Headline: ${last.headline || 'not detected'} | ${last.reason || 'checking match'}`
        : '';
    status.textContent = (state.message || state.status) + checkedHeadline;
    document.getElementById('jobsFound').textContent = (state.jobs || []).length;
    document.getElementById('peopleFound').textContent = (state.people || []).length;
    document.getElementById('networkJobCount').textContent = (state.jobs || []).length;
    document.getElementById('networkPersonCount').textContent = (state.people || []).length;
    const terms = document.getElementById('networkSearchTerms');
    terms.replaceChildren();
    for (const query of state.searchTerms || []) {
        const term = document.createElement('span');
        term.className = 'term-chip';
        term.textContent = query;
        terms.append(term);
    }
    renderNetworkJobs(state.jobs || []);
    renderNetworkPeople(state.people || [], state);
    const eligible = (state.people || []).filter(person => ['draft', 'error'].includes(person.status)).length;
    const batchButton = document.getElementById('sendNetworkNotesBtn');
    batchButton.disabled = state.status !== 'ready' || eligible === 0;
    batchButton.textContent = state.status === 'ready'
        ? (eligible ? `Send ${eligible} reviewed invitation${eligible === 1 ? '' : 's'}` : 'No unsent invitations')
        : 'Search to enable sending';
}

async function sendNetworkNote(candidateId, note, button, status) {
    if (!note.trim() || note.length > 200) {
        showNotification('error', 'Check connection note', 'Use 1–200 characters.');
        return;
    }
    button.disabled = true;
    button.textContent = 'Queueing invitation…';
    status.textContent = 'Submitting reviewed connection note to the LinkedIn browser…';
    try {
        const response = await fetch('/api/network/send-note', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({candidateId, note})
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Could not queue invitation');
        renderNetworkState(result);
        showNotification('info', 'Invitation queued', 'The browser will send your reviewed connection note.');
    } catch (error) {
        button.disabled = false;
        button.textContent = 'Send reviewed invitation';
        status.textContent = error.message;
        status.classList.add('is-error');
        showNotification('error', 'Invitation failed', error.message);
    }
}

async function sendNetworkNotes() {
    const batchButton = document.getElementById('sendNetworkNotesBtn');
    const notes = {};
    for (const card of networkCards.values()) {
        const id = card.dataset.candidateId;
        if (id) notes[id] = card.querySelector('.note-editor').value.trim();
    }
    batchButton.disabled = true;
    batchButton.textContent = 'Queueing reviewed invitations...';
    document.getElementById('networkStatus').textContent = 'Opening the separate LinkedIn sending browser and queueing reviewed connection notes in order...';
    try {
        const response = await fetch('/api/network/send-batch', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({notes})
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Could not queue reviewed notes');
        renderNetworkState(result);
        showNotification('info', 'Invitations queued', 'A separate LinkedIn browser will send each reviewed connection note.');
    } catch (error) {
        batchButton.disabled = false;
        batchButton.textContent = 'Retry sending reviewed invitations';
        document.getElementById('networkStatus').textContent = error.message;
        showNotification('error', 'Could not queue invitations', error.message);
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    document.getElementById('networkSearchMode').addEventListener('change', event => updateNetworkModeHint(event.target.value));
    document.getElementById('sendNetworkNotesBtn').addEventListener('click', sendNetworkNotes);
    try {
        const response = await fetch('/api/load-config');
        const result = await response.json();
        prepareNetworkDefaults(result.config || {});
    } catch (_) {
        // Search can run without a resume.
    }
    const poll = async () => {
        try {
            const response = await fetch('/api/network/state');
            if (response.ok) renderNetworkState(await response.json());
        } catch (_) { /* The dashboard's server indicator handles disconnection. */ }
    };
    await poll();
    setInterval(poll, 3000);
});
