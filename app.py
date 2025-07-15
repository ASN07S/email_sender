from flask import Flask, render_template, request, redirect, session, url_for, flash
import json
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from email.mime.text import MIMEText
import smtplib

app = Flask(__name__)
app.secret_key = 'Todo'

# json files
USER_FILE = 'users.json'
ACTIVATION_FILE = 'activations.json'
LOG_FILE = 'logs.json'

# keys with expiry date
activation_keys = {
    "gmail_api": {"key": "KEY123", "days": 7},
    "app_password": {"key": "KEY456", "days": 30},
    "mix_domain": {"key": "KEY789", "days": 14}
}

#Loading files
def load_json(path, default):
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    else:
        return default

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

users = load_json(USER_FILE, {})
user_activations = load_json(ACTIVATION_FILE, {})
logs = load_json(LOG_FILE, []) if isinstance(load_json(LOG_FILE, []), list) else []

#Routing parts

@app.route('/')
def home():
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')
    user = session['user']
    activated = user_activations.get(user, {})
    return render_template("dashboard.html", user=user, activated=activated)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email in users:
            flash("User already exists.", "danger")
        else:
            users[email] = generate_password_hash(password)
            save_json(USER_FILE, users)
            flash("Registration successful. Please login.", "success")
            return redirect('/login')
    return render_template("register.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email in users and check_password_hash(users[email], password):
            session['user'] = email
            return redirect('/dashboard')
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect('/login')

@app.route('/activate', methods=['POST'])
def activate():
    interface = request.form['interface']
    key = request.form['key']
    user = session['user']
    correct_key = activation_keys.get(interface)

    if correct_key and correct_key['key'] == key:
        expires_at = (datetime.now() + timedelta(days=correct_key['days'])).strftime('%Y-%m-%d')
        user_activations.setdefault(user, {})[interface] = expires_at
        save_json(ACTIVATION_FILE, user_activations)
        flash(f"{interface} activated until {expires_at}.", "success")
    else:
        flash("Invalid activation key.", "danger")
    return redirect('/dashboard')

@app.route('/send_email', methods=['POST'])
def send_email():
    interface = request.form['interface']
    recipient = request.form['recipient']
    subject = request.form['subject']
    body = request.form['body']
    user = session['user']

    expires = user_activations.get(user, {}).get(interface)
    if not expires or datetime.strptime(expires, '%Y-%m-%d') < datetime.now():
        flash("This interface is not active or has expired.", "danger")
        return redirect('/dashboard')

    message_entry = {
        "user": user,
        "to": recipient,
        "subject": subject,
        "body": body,
        "interface": interface,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = 'your_email@gmail.com'
        msg['To'] = recipient

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login('your_email@gmail.com', 'your_app_password')
        server.sendmail(msg['From'], [msg['To']], msg.as_string())
        server.quit()

        message_entry["status"] = "success"
    except Exception:
        message_entry["status"] = "error: hidden"

    logs.append(message_entry)
    save_json(LOG_FILE, logs)
    flash("Email sent successfully.", "success")
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(debug=True)
