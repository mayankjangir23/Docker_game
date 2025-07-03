from flask import Flask, request, jsonify, session, redirect, url_for, render_template_string, render_template
from openai import OpenAI
import re
import time
import random
from functools import wraps

app = Flask(__name__)
app.secret_key = ""  # Replace with a stronger secret in production

# Initialize Gemini/OpenAI (your config here)
model = OpenAI(
    api_key="",  # Replace with your actual key
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

# Load users from file
def load_users(filepath="username_and_pw.txt"):
    users = {}
    try:
        with open(filepath, "r") as f:
            for line in f:
                if "," in line:
                    username, password = line.strip().split(",", 1)
                    users[username.strip()] = password.strip()
    except FileNotFoundError:
        print("User file not found.")
    return users

users_db = load_users()

# Auth protection
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return wrapper

# Parse MCQ format into question, options, explanation, trick
def parse_mcq_output(output_text):
    try:
        answer_match = re.search(r"Answer:\s*([A-Da-d])", output_text)
        explanation_match = re.search(r"Explanation:\s*(.*?)Memory Trick:", output_text, re.DOTALL)
        memory_trick_match = re.search(r"Memory Trick:\s*(.*)", output_text, re.DOTALL)

        answer = answer_match.group(1).upper() if answer_match else ""
        explanation = explanation_match.group(1).strip() if explanation_match else "No explanation found."
        memory_trick = memory_trick_match.group(1).strip() if memory_trick_match else "No memory trick."

        # Extract question and options
        question_match = re.search(r"Question:\s*(.*?)\n[A-D]\)", output_text, re.DOTALL)
        question = question_match.group(1).strip() if question_match else "No question found."

        options = {}
        for option in ['A', 'B', 'C', 'D']:
            match = re.search(rf"{option}\)\s*(.*)", output_text)
            options[option] = match.group(1).strip() if match else ""

        return question, options, answer, explanation, memory_trick
    except Exception as e:
        print(f"[Parse Error]: {e}")
        return "Error parsing question", {}, "", "Could not parse explanation.", "No memory trick."

# MCQ generator using OpenAI
def docker_mcq_quiz(level):
    timestamp = int(time.time())
    topics = ["Dockerfile", "images", "volumes", "networks", "containers", "build", "compose"]
    topic = random.choice(topics)

    prompt = (
        f"Generate a {level}-level Docker MCQ about '{topic}', unique to timestamp {timestamp}.\n"
        "Use this format:\n"
        "Question: <your question>\n"
        "A) option1\n"
        "B) option2\n"
        "C) option3\n"
        "D) option4\n"
        "Answer: <A/B/C/D>\n"
        "Explanation: <why this is correct>\n"
        "Memory Trick: <a tip to remember this>"
    )

    response = model.chat.completions.create(
        model="gemini-1.5-flash",
        temperature=0.9,
        messages=[
            {"role": "system", "content": "You are a Docker MCQ generator."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# Routes
@app.route("/")
def index():
    if session.get('logged_in'):
        return redirect(url_for('quiz_page'))
    return redirect(url_for('login_page'))

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username in users_db and users_db[username] == password:
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("quiz_page"))
        return "Invalid username or password", 401

    # Login form with button to create account
    return '''
    <h2>Login</h2>
    <form method="POST" action="/login">
        Username: <input type="text" name="username" required><br><br>
        Password: <input type="password" name="password" required><br><br>
        <input type="submit" value="Login">
    </form>
    <br>
    <form action="/create_account" method="get">
        <button type="submit">Create Account</button>
    </form>
    '''

@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        new_username = request.form.get("new_username", "").strip()
        new_password = request.form.get("new_password", "").strip()

        if not new_username or not new_password:
            return "Username and password are required.", 400

        if new_username in users_db:
            return "Username already exists.", 400

        # Save to file
        with open("username_and_pw.txt", "a") as f:
            f.write(f"{new_username},{new_password}\n")

        # Update in-memory DB
        users_db[new_username] = new_password

        return redirect(url_for("login_page"))

    # GET request returns your inline styled create account page using render_template_string
    create_account_html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <title>Create Account - Docker Quiz</title>
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(to right, #e0eafc, #cfdef3); height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; margin:0;">

      <h1 style="position: absolute; top: 20px; width: 100%; text-align: center; font-size: 26px; color: #222; margin:0;">Create Your Account</h1>

      <div style="background-color: #ffffff; padding: 40px 30px; border-radius: 12px; box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12); width: 100%; max-width: 400px; animation: fadeIn 0.8s ease;">
        <h2 style="text-align: center; margin-bottom: 25px; font-size: 22px; color: #333;">Sign Up</h2>
        <form method="POST" action="/create_account">
          <label for="new_username" style="display: block; margin-bottom: 6px; font-weight: 500; color: #444;">Username:</label>
          <input type="text" name="new_username" id="new_username" required
                 style="width: 100%; padding: 12px 14px; margin-bottom: 20px; border: 1px solid #ccc; border-radius: 6px; font-size: 15px; outline:none;"
                 onfocus="this.style.borderColor='#007bff'; this.style.boxShadow='0 0 0 3px rgba(0, 123, 255, 0.2)';"
                 onblur="this.style.borderColor='#ccc'; this.style.boxShadow='none';"
          />

          <label for="new_password" style="display: block; margin-bottom: 6px; font-weight: 500; color: #444;">Password:</label>
          <input type="password" name="new_password" id="new_password" required
                 style="width: 100%; padding: 12px 14px; margin-bottom: 20px; border: 1px solid #ccc; border-radius: 6px; font-size: 15px; outline:none;"
                 onfocus="this.style.borderColor='#007bff'; this.style.boxShadow='0 0 0 3px rgba(0, 123, 255, 0.2)';"
                 onblur="this.style.borderColor='#ccc'; this.style.boxShadow='none';"
          />

          <button type="submit" 
                  style="width: 100%; padding: 12px; background-color: #007bff; color: #fff; font-size: 16px; border: none; border-radius: 6px; cursor: pointer; transition: background-color 0.3s ease;"
                  onmouseover="this.style.backgroundColor='#0056b3';"
                  onmouseout="this.style.backgroundColor='#007bff';"
          >
            Create Account
          </button>
        </form>
      </div>

      <style>
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      </style>

    </body>
    </html>
    '''
    return render_template_string(create_account_html)

@app.route("/quiz")
@login_required
def quiz_page():
    username = session.get("username")
    return render_template("quiz.html", username=username)

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login_page"))

@app.route("/new_question", methods=["GET"])
@login_required
def new_question():
    level = request.args.get("level", "basic")
    raw_mcq = docker_mcq_quiz(level)
    question, options, correct_answer, explanation, memory_trick = parse_mcq_output(raw_mcq)

    return jsonify({
        "question": question,
        "options": options,
        "correct_answer": correct_answer,
        "explanation": explanation,
        "memory_trick": memory_trick
    })

@app.route("/submit_answer", methods=["POST"])
@login_required
def submit_answer():
    data = request.json
    user_answer = data.get("user_answer", "").strip().upper()
    correct_answer = data.get("correct_answer", "").strip().upper()
    explanation = data.get("explanation", "")
    memory_trick = data.get("memory_trick", "")

    if user_answer == correct_answer:
        result = f"✅ Correct! Option {correct_answer} is right!"
    else:
        result = f"❌ Incorrect. Correct answer was: {correct_answer}"

    return jsonify({
        "result": result,
        "explanation": explanation,
        "memory_trick": memory_trick
    })

if __name__ == "__main__":
    app.run(debug=True)
