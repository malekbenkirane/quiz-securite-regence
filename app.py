from flask import Flask, render_template, request, redirect, session, url_for
import json, sqlite3
from datetime import datetime
from flask import Flask, send_file
from flask_sqlalchemy import SQLAlchemy
from fpdf import FPDF  # ou reportlab/matplotlib selon ta méthode de génération
import os  # ✅ Ajout de l'import os
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = 'quiz_secret'

DB_PATH = "database.db"
ADMIN_CREDENTIALS = {"username": "Reg", "password": "Saouda2025!!"}

# Ta fonction pour générer le rapport
def generate_report():
    # Crée un objet PDF
    pdf = FPDF()
    pdf.add_page()

    # Titre du document
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(200, 10, txt="Rapport de Test de Phishing", ln=True, align='C')

    # Ajouter des informations dans le rapport
    pdf.set_font('Arial', '', 12)
    pdf.ln(10)
    pdf.cell(200, 10, txt="Détails des résultats", ln=True)

    # Charger les résultats de la base de données
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT user_email, score, date_taken FROM results")
    rows = c.fetchall()
    conn.close()

    # Vérification si des résultats ont été trouvés
    if not rows:
        print("Aucun résultat trouvé.")
        pdf.cell(200, 10, txt="Aucun résultat trouvé.", ln=True)
        pdf.output(os.path.join(os.getcwd(), "rapport_regence.pdf"))
        return os.path.join(os.getcwd(), "rapport_regence.pdf")

    # Log des résultats récupérés
    print("Résultats récupérés de la base de données :")
    for row in rows:
        print(f"Utilisateur : {row[0]}, Score : {row[1]}, Date : {row[2]}")

    # Convertir les résultats en dictionnaires
    results = [{"user_email": row[0], "score": row[1], "date_taken": row[2]} for row in rows]

    # Comptage des réussites et des échecs
    successful_count = sum(1 for r in results if r["score"] >= 6)
    failed_count = sum(1 for r in results if r["score"] < 6)

    # Ajouter les statistiques des scores
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Nombre de réussites : {successful_count}", ln=True)
    pdf.cell(200, 10, txt=f"Nombre d'échecs : {failed_count}", ln=True)

    # Répartition des scores
    low_scores = sum(1 for r in results if r["score"] <= 3)
    mid_scores = sum(1 for r in results if 4 <= r["score"] <= 6)
    high_scores = sum(1 for r in results if 7 <= r["score"] <= 8)
    perfect_scores = sum(1 for r in results if r["score"] >= 9)

    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Scores faibles (0-3) : {low_scores}", ln=True)
    pdf.cell(200, 10, txt=f"Scores moyens (4-6) : {mid_scores}", ln=True)
    pdf.cell(200, 10, txt=f"Scores élevés (7-8) : {high_scores}", ln=True)
    pdf.cell(200, 10, txt=f"Scores parfaits (9-10) : {perfect_scores}", ln=True)

    # Ajouter les résultats détaillés des utilisateurs
    pdf.ln(10)
    pdf.cell(200, 10, txt="Détails des utilisateurs :", ln=True)
    for result in results:
        pdf.cell(200, 10, txt=f"{result['user_email']} - Score: {result['score']} - Date: {result['date_taken']}", ln=True)

    # Créer un graphique des scores
    scores = [r['score'] for r in results]
    plt.figure(figsize=(8, 6))
    plt.hist(scores, bins=10, color='skyblue', edgecolor='black')
    plt.title('Répartition des Scores des Utilisateurs')
    plt.xlabel('Score')
    plt.ylabel('Nombre d\'utilisateurs')

    # Sauvegarder le graphique
    graph_path = os.path.join(os.getcwd(), 'scores_distribution.png')
    plt.savefig(graph_path)
    plt.close()

    # Ajouter le graphique dans le PDF
    pdf.ln(10)
    pdf.image(graph_path, x=10, y=pdf.get_y(), w=180)

    # Sauvegarder le fichier PDF
    report_path = os.path.join(os.getcwd(), "rapport_regence.pdf")
    pdf.output(report_path)

    # Supprimer le fichier de graphique
    os.remove(graph_path)

    return report_path

# ---------------- Initialisation base de données ---------------- #
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            score INTEGER,
            date_taken TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ------------------- ROUTES ------------------- #

@app.route('/')
def index():
    return render_template("login_user.html")

@app.route('/login', methods=["POST"])
def login_user():
    email = request.form['email']
    if email:
        session['user_email'] = email
        session['question_index'] = 0  # Initialiser l'index des questions
        session['score'] = 0  # Initialiser le score
        return redirect("/quiz")
    return redirect("/")

@app.route('/quiz', methods=["GET", "POST"])
def quiz():
    if 'user_email' not in session:
        return redirect("/")  # Rediriger si l'utilisateur n'est pas connecté

    # Charger les questions depuis le fichier JSON
    with open("questions.json", encoding="utf-8") as f:
        questions = json.load(f)

    # Obtenir l'index de la question actuelle depuis la session
    question_index = session.get('question_index', 0)
    total_questions = len(questions)

    # Si l'utilisateur a déjà répondu à toutes les questions, rediriger vers /submit
    if question_index >= total_questions:
        return redirect("/submit")

    question = questions[question_index]

    if request.method == "POST":
        user_answer = request.form.get(f"q{question_index}")  # Récupérer la réponse de l'utilisateur
        
        # Si la réponse est correcte, augmenter le score
        if user_answer and int(user_answer) == question["answer"]:
            session['score'] += 1
        
        # Avancer à la question suivante
        session['question_index'] = question_index + 1

        # Rediriger vers la prochaine question
        return redirect("/quiz")

    return render_template("quiz.html", question=question, question_index=question_index, total_questions=total_questions)

@app.route('/submit', methods=["GET", "POST"])
def submit():
    if 'user_email' not in session:
        return redirect("/")  # Rediriger si l'utilisateur n'est pas connecté

    # Charger les questions et calculer le score final
    with open("questions.json", encoding="utf-8") as f:
        questions = json.load(f)

    score = session.get('score', 0)

    # Enregistrer le score dans la base de données
    email = session.get('user_email')
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO results (user_email, score, date_taken) VALUES (?, ?, ?)", (email, score, now))
    conn.commit()
    conn.close()

    # Réinitialiser l'index de question dans la session pour un futur quiz
    session['question_index'] = 0

    # Rediriger vers une page de résultats ou un tableau de bord
    return render_template("result.html", score=score, total=len(questions))

@app.route('/login_admin', methods=["GET", "POST"])
def login_admin():
    if request.method == "GET":
        return render_template("login_admin.html")
    username = request.form['username']
    password = request.form['password']
    if username == ADMIN_CREDENTIALS["username"] and password == ADMIN_CREDENTIALS["password"]:
        session['admin'] = True
        return redirect("/dashboard")
    return render_template("login_admin.html", error="Identifiants invalides")

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_email, score, date_taken FROM results")
    rows = c.fetchall()
    conn.close()

    # Convertir les résultats en dictionnaires
    results = [{"user_email": row[0], "score": row[1], "date_taken": row[2]} for row in rows]

    # Comptage réussite / échec
    successful_count = sum(1 for r in results if r["score"] >= 6)
    failed_count = sum(1 for r in results if r["score"] < 6)

    # Statistiques des scores
    low_scores = sum(1 for r in results if r["score"] <= 3)
    mid_scores = sum(1 for r in results if 4 <= r["score"] <= 6)
    high_scores = sum(1 for r in results if 7 <= r["score"] <= 8)
    perfect_scores = sum(1 for r in results if r["score"] >= 9)

    return render_template('dashboard.html',
                           results=results,
                           successful_count=successful_count,
                           failed_count=failed_count,
                           low_scores=low_scores,
                           mid_scores=mid_scores,
                           high_scores=high_scores,
                           perfect_scores=perfect_scores)

@app.route('/reset-stats', methods=['POST'])
def reset_stats():
    # Code pour réinitialiser les données
    db.session.query(PhishingResult).delete()
    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/download-report')
def download_report():
    # Génère le rapport si il n'existe pas déjà
    report_path = os.path.join(os.getcwd(), "rapport_regence.pdf")
    
    # Si le fichier n'existe pas, on le génère
    if not os.path.exists(report_path):
        generate_report()  # Appelle la fonction pour générer le rapport

    # Vérifie si le fichier a été créé avec succès
    if not os.path.exists(report_path):
        return "Erreur dans la génération du rapport.", 500

    return send_file(report_path, as_attachment=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
