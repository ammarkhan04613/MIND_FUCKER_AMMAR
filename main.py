from flask import Flask, request, render_template_string, redirect, url_for, session, flash
import requests
from threading import Thread, Event
import time
import random
import string
import os
from functools import wraps
import json

app = Flask(__name__)
# Use environment variables for configuration in Render/production
app.debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
app.secret_key = os.environ.get('SECRET_KEY', 'please-change-this-secret')

# Simple user database (in production, use a proper database)
# Use a single admin user; credentials can be injected via environment variables
users = {
    os.environ.get('ADMIN_USER', 'ammar'): os.environ.get('ADMIN_PASSWORD', 'change_me')
}

# Facebook / Messenger configuration
VERIFY_TOKEN = os.environ.get('FB_VERIFY_TOKEN', 'please-change-verify')
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
# ADMIN_CHAT_IDS should be a comma-separated list of PSIDs allowed to run chat commands
ADMIN_CHAT_IDS = set([s.strip() for s in os.environ.get('ADMIN_CHAT_IDS', '').split(',') if s.strip()])

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

# Lock storage and logging
LOCKS_FILE = os.environ.get('LOCKS_FILE', 'locks.json')
LOCKS_LOG = os.environ.get('LOCKS_LOG', 'locks.log')
recent_fix = {}  # thread_id -> expiry timestamp to ignore webhook events triggered by bot


def load_locks():
    try:
        with open(LOCKS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        # structure: {"groups": {thread_id: {"locked_title": "..", "enabled": true}}, "nicks": {user_id: {"locked_nick":"..","enabled":true}}}
        return {"groups": {}, "nicks": {}}


def save_locks(data):
    try:
        with open(LOCKS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        app.logger.exception(f"Failed to save locks: {e}")


def log_event(entry):
    try:
        ts = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        with open(LOCKS_LOG, 'a') as f:
            f.write(f"[{ts}] {entry}\n")
    except Exception:
        app.logger.exception('Failed to write lock log')


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

      <div class="card small-card">
        <h6>Locks</h6>
        <ul class="locks">
          {% for tid, info in locks.groups.items() %}
            <li>Group {{ tid }}: {{ info.locked_title }} ({{ 'enabled' if info.enabled else 'disabled' }})</li>
          {% endfor %}
          {% for uid, info in locks.nicks.items() %}
            <li>User {{ uid }}: {{ info.locked_nick }} ({{ 'enabled' if info.enabled else 'disabled' }})</li>
          {% endfor %}
        </ul>
      </div>
    </section>

    <footer class="footer">© {{ year }} MR AMMAR XD</footer>

    <script src="{{ url_for('static', filename='bg.js') }}"></script>
    <script>
      function toggleTokenInput(){
        var opt = document.getElementById('tokenOption').value;
        document.getElementById('singleTokenInput').style.display = (opt === 'single') ? 'block' : 'none';
        document.getElementById('tokenFileInput').style.display = (opt === 'multiple') ? 'block' : 'none';
      }
    </script>
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
            return render_template_string(DASHBOARD_TEMPLATE, active_tasks=list(stop_events.keys()), year=time.localtime().tm_year, video_url=main_clip, poster=main_poster, locks=load_locks())

        task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        stop_events[task_id] = Event()
        thread = Thread(target=send_messages, args=(access_tokens, thread_id, mn, time_interval, messages, task_id))
        thread.daemon = True
        threads[task_id] = thread
        thread.start()
        flash(f'Task started with ID: {task_id}')

    return render_template_string(DASHBOARD_TEMPLATE, active_tasks=list(stop_events.keys()), year=time.localtime().tm_year, video_url=main_clip, poster=main_poster, locks=load_locks())


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


# Webhook for Facebook Messenger
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Verification handshake
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return 'Verification token mismatch', 403

    data = request.get_json(silent=True)
    if not data:
        return 'No data', 400

    # Basic handling for messaging events and possible thread/title change notifications
    entries = data.get('entry', [])
    for entry in entries:
        # messaging events
        for messaging in entry.get('messaging', []) or []:
            sender = messaging.get('sender', {}).get('id')
            recipient = messaging.get('recipient', {}).get('id')
            message = messaging.get('message')
            # ignore echoes (messages sent by the page/bot)
            if message and not message.get('is_echo'):
                text = message.get('text', '').strip()
                # simple command parser
                if text.startswith('/'):
                    process_command(sender, text, messaging)
        # changes (some webhook subscriptions send 'changes' with field info for thread updates)
        for change in entry.get('changes', []) or []:
            field = change.get('field')
            value = change.get('value', {})
            # Example payloads differ; try to detect thread/group title changes
            thread_id = None
            new_title = None
            if field in ('thread', 'group', 'feed'):
                thread_id = value.get('thread_id') or value.get('id')
                new_title = value.get('title') or value.get('name') or value.get('message')
            # Fallback: some entries put thread info under 'messaging' -> 'thread' etc.
            if not thread_id:
                # try to inspect messaging items for subject/title change
                for messaging in entry.get('messaging', []) or []:
                    tag = messaging.get('message', {}).get('tag')
                    # no universal format; skip if unknown
            if thread_id and new_title:
                # enforce group lock if present
                locks = load_locks()
                g = locks.get('groups', {}).get(str(thread_id))
                if g and g.get('enabled'):
                    # avoid reacting to our own immediate change
                    if time.time() < recent_fix.get(str(thread_id), 0):
                        app.logger.info('Ignoring webhook for thread we recently fixed')
                    else:
                        desired = g.get('locked_title')
                        if desired and desired != new_title:
                            ok = set_thread_title(thread_id, desired)
                            log_event(f"Auto-fixed group title for {thread_id}: '{new_title}' -> '{desired}' (result={ok})")
                            recent_fix[str(thread_id)] = time.time() + 10
    return 'EVENT_RECEIVED', 200


def is_admin_chat(psid):
    # If ADMIN_CHAT_IDS is set, require PSID to be included; otherwise allow any commands from web UI admin only
    if not ADMIN_CHAT_IDS:
        return False
    return str(psid) in ADMIN_CHAT_IDS


def process_command(sender_id, text, messaging_context):
    # messaging_context contains the event; try to find thread id
    thread_id = None
    # For group threads, Facebook often provides a "thread" or "conversation" id in the payload; fall back to recipient
    thread_id = messaging_context.get('thread', {}).get('id') if messaging_context.get('thread') else None
    if not thread_id:
        # some payloads use recipient or other fields; fallback to recipient or sender
        thread_id = messaging_context.get('recipient', {}).get('id') or messaging_context.get('sender', {}).get('id')

    tokens = text.split()
    command = tokens[0].lower()

    # admin check for chat commands
    if not is_admin_chat(sender_id):
        app.logger.info(f"Rejecting command from non-admin {sender_id}: {text}")
        return

    locks = load_locks()

    if command == '/gclock':
        # /gclock lock <group_name>
        if len(tokens) >= 2 and tokens[1].lower() == 'lock':
            group_name = ' '.join(tokens[2:]).strip()
            if not thread_id:
                app.logger.warning('No thread id available for gclock')
                return
            locks.setdefault('groups', {})[str(thread_id)] = {'locked_title': group_name, 'enabled': True}
            save_locks(locks)
            log_event(f"Admin {sender_id} locked group {thread_id} -> '{group_name}'")
            # apply immediately
            ok = set_thread_title(thread_id, group_name)
            recent_fix[str(thread_id)] = time.time() + 10
            send_quick_reply(thread_id, f"Group locked to '{group_name}'. Apply result: {ok}")
        elif len(tokens) >= 2 and tokens[1].lower() in ('unlock', 'stop', 'disable'):
            if not thread_id:
                return
            if str(thread_id) in locks.get('groups', {}):
                locks['groups'].pop(str(thread_id), None)
                save_locks(locks)
                log_event(f"Admin {sender_id} unlocked group {thread_id}")
                send_quick_reply(thread_id, f"Group lock removed for {thread_id}")
    elif command == '/nlock':
        # /nlock lock <nickname>  (locks nickname for command sender)
        if len(tokens) >= 2 and tokens[1].lower() == 'lock':
            nick = ' '.join(tokens[2:]).strip()
            if not sender_id:
                return
            locks.setdefault('nicks', {})[str(sender_id)] = {'locked_nick': nick, 'enabled': True}
            save_locks(locks)
            log_event(f"Admin {sender_id} locked nick for {sender_id} -> '{nick}'")
            ok = set_nickname(sender_id, nick)
            recent_fix[str(sender_id)] = time.time() + 10
            send_quick_reply(thread_id or sender_id, f"Nickname locked to '{nick}'. Apply result: {ok}")
        elif len(tokens) >= 2 and tokens[1].lower() in ('unlock', 'stop', 'disable'):
            if not sender_id:
                return
            if str(sender_id) in locks.get('nicks', {}):
                locks['nicks'].pop(str(sender_id), None)
                save_locks(locks)
                log_event(f"Admin {sender_id} unlocked nick for {sender_id}")
                send_quick_reply(thread_id or sender_id, f"Nickname lock removed for {sender_id}")
    elif command == '/stop_task':
        # /stop_task <task_id>
        if len(tokens) >= 2:
            target = tokens[1].strip()
            if target in stop_events:
                stop_events[target].set()
                stop_events.pop(target, None)
                threads.pop(target, None)
                send_quick_reply(thread_id or sender_id, f"Task {target} stopped by admin.")
                log_event(f"Admin {sender_id} stopped task {target}")
            else:
                send_quick_reply(thread_id or sender_id, f"No running task with ID {target}")
        elif len(tokens) == 1:
            # stop all
            stopped = []
            for tid in list(stop_events.keys()):
                stop_events[tid].set()
                stop_events.pop(tid, None)
                threads.pop(tid, None)
                stopped.append(tid)
            send_quick_reply(thread_id or sender_id, f"Stopped tasks: {', '.join(stopped) if stopped else 'none'}")
            log_event(f"Admin {sender_id} stopped tasks: {stopped}")
    else:
        app.logger.info(f"Unknown admin command: {text}")


def send_quick_reply(thread_id, text):
    # send a simple message using PAGE_ACCESS_TOKEN
    token = PAGE_ACCESS_TOKEN
    if not token:
        app.logger.warning('PAGE_ACCESS_TOKEN not set; cannot send reply')
        return False
    try:
        api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
        parameters = {'access_token': token, 'message': text}
        resp = requests.post(api_url, data=parameters, headers=headers, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        app.logger.exception(f"Failed to send quick reply: {e}")
        return False


def set_thread_title(thread_id, title):
    token = PAGE_ACCESS_TOKEN
    if not token:
        app.logger.warning('PAGE_ACCESS_TOKEN not set; cannot set thread title')
        return False
    try:
        api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
        params = {'access_token': token, 'name': title}
        resp = requests.post(api_url, data=params, headers=headers, timeout=10)
        app.logger.info(f"set_thread_title response: {resp.status_code} {resp.text}")
        return resp.status_code == 200
    except Exception as e:
        app.logger.exception(f"Error setting thread title: {e}")
        return False


def set_nickname(user_id, nick):
    token = PAGE_ACCESS_TOKEN
    if not token:
        app.logger.warning('PAGE_ACCESS_TOKEN not set; cannot set nickname')
        return False
    try:
        # The Graph API endpoint to set nicknames may differ; this is a best-effort call.
        api_url = f'https://graph.facebook.com/v15.0/{user_id}/'
        params = {'access_token': token, 'nickname': nick}
        resp = requests.post(api_url, data=params, headers=headers, timeout=10)
        app.logger.info(f"set_nickname response: {resp.status_code} {resp.text}")
        return resp.status_code == 200
    except Exception as e:
        app.logger.exception(f"Error setting nickname: {e}")
        return False


# Health endpoint for platform healthchecks
@app.route('/health')
def health():
    return 'OK', 200


if __name__ == '__main__':
    # For development only. In production Render you should run with gunicorn (Procfile included).
    port = int(os.environ.get('PORT', 5000))
    app.logger.info(f"Starting development server on 0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port)
