const responseTitle = document.querySelector('#responseTitle');
const responseStatus = document.querySelector('#responseStatus');
const responsePayload = document.querySelector('#responsePayload');

document.querySelectorAll('.endpoint-toggle').forEach((button) => {
  button.addEventListener('click', () => {
    const form = document.querySelector(`#${button.dataset.target}`);
    form.classList.toggle('is-open');
    button.firstChild.textContent = form.classList.contains('is-open') ? 'Close ' : `${button.textContent.startsWith('Run') ? 'Run' : 'Configure'} `;
  });
});

function showResponse(path, response, payload) {
  responseTitle.textContent = path;
  responseStatus.textContent = `${response.status} ${response.ok ? 'OK' : 'Error'}`;
  responseStatus.classList.toggle('response-error', !response.ok);
  responsePayload.textContent = JSON.stringify(payload, null, 2);
}

async function executeRequest(method, path, body) {
  const response = await fetch(path, {method, headers: body ? {'Content-Type': 'application/json'} : {}, body: body ? JSON.stringify(body) : undefined});
  const payload = await response.json().catch(() => ({message: 'No JSON response'}));
  showResponse(path, response, payload);
}

document.querySelectorAll('.api-run').forEach((button) => {
  button.addEventListener('click', async () => {
    button.disabled = true;
    try { await executeRequest(button.dataset.method, button.dataset.path); }
    catch (error) { responseStatus.textContent = 'Network error'; responseStatus.classList.add('response-error'); responsePayload.textContent = error.message; }
    finally { button.disabled = false; }
  });
});

document.querySelectorAll('.api-form').forEach((form) => {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const values = Object.fromEntries(new FormData(form));
    let path = form.dataset.path;
    const body = {};
    if (form.dataset.pathTemplate) {
      path = form.dataset.pathTemplate;
      Object.entries(values).forEach(([key, value]) => {
        if (path.includes(`{${key}}`)) path = path.replace(`{${key}}`, encodeURIComponent(value));
        else if (key !== 'asset_id' && key !== 'check_id' && key !== 'alert_id') body[key] = key === 'site_id' || key === 'interval_seconds' ? Number(value) : value;
      });
    } else if (path === '/api/v1/assets') {
      Object.assign(body, values, {site_id: Number(values.site_id)});
    } else if (path === '/api/v1/collectors/sync') {
      try { body.records = JSON.parse(values.records); } catch { body.records = []; }
    }
    try { await executeRequest(form.dataset.method, path, body); }
    catch (error) { responseStatus.textContent = 'Network error'; responseStatus.classList.add('response-error'); responsePayload.textContent = error.message; }
  });
});
