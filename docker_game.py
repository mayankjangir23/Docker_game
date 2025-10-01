from flask import Flask, request, jsonify, session, redirect, url_for, render_template
import google.generativeai as genai
import re
import time
import random
from functools import wraps

app = Flask(__name__)
app.secret_key = "something@something1234"

# Initialize Google Gemini Model
genai.configure(api_key="AIzaSyC40Oh57SQA9_mwLcjWsgd0IJ9wAg030xY")
model = genai.GenerativeModel("models/gemini-flash-latest")

# Load user credentials
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

# Authentication decorator
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return wrapper

# Parse MCQ AI response
def parse_mcq_output(output_text):
    try:
        answer_match = re.search(r"Answer:\s*([A-Da-d])", output_text)
        explanation_match = re.search(r"Explanation:\s*(.*?)Memory Trick:", output_text, re.DOTALL)
        memory_trick_match = re.search(r"Memory Trick:\s*(.*)", output_text, re.DOTALL)

        answer = answer_match.group(1).upper() if answer_match else ""
        explanation = explanation_match.group(1).strip() if explanation_match else "No explanation found."
        memory_trick = memory_trick_match.group(1).strip() if memory_trick_match else "No memory trick."

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

# AI Quiz Generator
def docker_mcq_quiz(level):
    timestamp = int(time.time())
    topics = ["Dockerfile", "images", "volumes", "networks", "containers", "build", "compose"]
    topic = random.choice(topics)

    prompt = (
    f"Generate a {level}-level Docker MCQ on '{topic}' (be original using timestamp {timestamp}).\n"
    "Respond in exactly the following format without repeating anything:\n\n"
    "Question: What is ...?\n"
    "A) ...\n"
    "B) ...\n"
    "C) ...\n"
    "D) ...\n"
    "Answer: A\n"
    "Explanation: ...\n"
    "Memory Trick: ..."
)

    response = model.generate_content(
        f"You are a Docker MCQ generator.\n\n{prompt}",
        generation_config={"temperature": 0.9}
    )
    return response.text

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

    return render_template("login.html")

@app.route("/create_account", methods=["GET", "POST"])
def create_account():
    if request.method == "POST":
        new_username = request.form.get("new_username", "").strip()
        new_password = request.form.get("new_password", "").strip()

        if not new_username or not new_password:
            return "Username and password are required.", 400

        if new_username in users_db:
            return "Username already exists.", 400

        with open("username_and_pw.txt", "a") as f:
            f.write(f"{new_username},{new_password}\n")

        users_db[new_username] = new_password
        return redirect(url_for("login_page"))

    return render_template("create_account.html")

@app.route("/quiz")
@login_required
def quiz_page():
    return render_template("quiz.html", username=session.get("username"))

@app.route("/learn")
@login_required
def learn_page():
    return render_template("learn.html", username=session.get("username"))

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

    if "score" not in session:
        session["score"] = 0
        session["total"] = 0

    session["total"] += 1
    
    if user_answer == correct_answer:
        session["score"] += 1
        result = f"✅ Correct! Option {correct_answer} is right!"
    else:
        result = f"❌ Incorrect. Correct answer was: {correct_answer}"

    return jsonify({
        "result": result,
        "explanation": explanation,
        "memory_trick": memory_trick,
        "score": session["score"],
        "total": session["total"]
    })

@app.route("/reset_score", methods=["POST"])
@login_required
def reset_score():
    session["score"] = 0
    session["total"] = 0
    return jsonify({"message": "Score reset successfully."})

# 🚀 AI Learning Endpoint
@app.route("/learn_topic", methods=["POST"])
@login_required
def learn_topic():
    query = request.json.get("query", "").strip()
    if not query:
        return jsonify({"error": "No topic provided."}), 400

    prompt = (
        f"The user wants to learn about the Docker topic: '{query}'.\n"
        "Provide a structured, easy-to-understand guide that includes:\n"
        "1. A clear and concise explanation of the topic.\n"
        "2. At least 2-3 commonly used Docker commands related to the topic with brief examples.\n"
        "3. A memory trick or analogy to help remember the concept.\n"
        "4. Keep it beginner-friendly and structured.\n\n"
        "Respond in this format:\n\n"
        "🔍 Topic: <topic>\n\n"
        "📘 Explanation:\n<detailed explanation here>\n\n"
        "🛠️ Common Docker Commands:\n- command 1\n- command 2\n...\n\n"
        "🧠 Learning Trick:\n<tip or analogy to remember>\n"
    )

    try:
        response = model.generate_content(
            f"You are a Docker tutor for beginners.\n\n{prompt}",
            generation_config={"temperature": 0.7}
        )
        reply = response.text
        return jsonify({"content": reply})
    except Exception as e:
        print(f"[AI Error]: {e}")
        return jsonify({"error": "Failed to fetch learning content"}), 500

if __name__ == "__main__":
    app.run(debug=True)
