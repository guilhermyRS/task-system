from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import pytz

app = Flask(__name__)

# Configuração para ambiente de produção
PRODUCTION = os.environ.get('VERCEL_ENV') == 'production'

# Configuração de banco de dados - adaptação para Vercel
if PRODUCTION:
    # Na Vercel, usamos o caminho /tmp para armazenamento temporário de SQLite
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/tasks.db"
else:
    # Ambiente local
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tasks.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "5f7898f1dcb24a85b98f3c9c2c09f771")

# Configurações de upload
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if PRODUCTION:
    # Na Vercel, podemos usar /tmp para arquivos temporários durante a execução
    UPLOAD_FOLDER = "/tmp/profile_pics"
else:
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/profile_pics")

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

db = SQLAlchemy(app)

# Ensure upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_current_time():
    return datetime.now(pytz.UTC)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    profile_pic = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=get_current_time)
    last_login = db.Column(db.DateTime)
    lists = db.relationship("List", backref="owner", lazy=True, cascade="all, delete")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def update_last_login(self):
        self.last_login = get_current_time()
        db.session.commit()

class List(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=get_current_time)
    last_modified = db.Column(db.DateTime, default=get_current_time, onupdate=get_current_time)
    tasks = db.relationship("Task", backref="list", cascade="all, delete", lazy=True)

    __table_args__ = (db.UniqueConstraint("name", "user_id", name="unique_list_name_per_user"),)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=get_current_time)
    completed_at = db.Column(db.DateTime)
    list_id = db.Column(db.Integer, db.ForeignKey("list.id"), nullable=False)
    subtasks = db.relationship("SubTask", backref="task", cascade="all, delete", lazy=True)

class SubTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=get_current_time)
    completed_at = db.Column(db.DateTime)
    task_id = db.Column(db.Integer, db.ForeignKey("task.id"), nullable=False)
    steps = db.relationship("Step", backref="subtask", cascade="all, delete", lazy=True)

class Step(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    content = db.Column(db.String(200), nullable=False)
    done = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=get_current_time)
    completed_at = db.Column(db.DateTime)
    subtask_id = db.Column(db.Integer, db.ForeignKey("sub_task.id"), nullable=False)

def login_required(f):
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Por favor, faça login para acessar esta página.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def check_list_ownership(list_id):
    if "user_id" not in session:
        return False
    list_item = List.query.get(list_id)
    return list_item and list_item.user_id == session["user_id"]

# Authentication routes
@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        phone = request.form.get("phone")
        name = request.form.get("name", username)  # Usando o nome ou username como fallback
        
        if User.query.filter_by(username=username).first():
            flash("Nome de usuário já existe", "error")
            return redirect(url_for("register"))
        
        if User.query.filter_by(email=email).first():
            flash("Email já registrado", "error")
            return redirect(url_for("register"))

        profile_pic = None
        if "profile_pic" in request.files:
            file = request.files["profile_pic"]
            if file and file.filename != "" and allowed_file(file.filename):
                filename = secure_filename(f"{username}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)
                profile_pic = filename

        user = User(
            username=username,
            email=email,
            name=name,
            phone=phone,
            profile_pic=profile_pic
        )
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash("Registro realizado com sucesso! Por favor, faça login.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            flash("Erro ao registrar usuário. Por favor, tente novamente.", "error")
            return redirect(url_for("register"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session["user_id"] = user.id
            user.update_last_login()
            flash(f"Bem-vindo de volta, {user.name if user.name else user.username}!", "success")
            return redirect(url_for("index"))
        
        flash("Usuário ou senha inválidos", "error")
        return redirect(url_for("login"))
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Você foi desconectado com sucesso!", "success")
    return redirect(url_for("login"))

# Main routes
@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    user = User.query.get(session["user_id"])
    if not user:
        return redirect(url_for("logout"))

    if request.method == "POST":
        try:
            if "list_name" in request.form:
                name = request.form.get("list_name")
                if name:
                    new_list = List(name=name, user_id=user.id)
                    db.session.add(new_list)
                    db.session.commit()
                    flash("Lista criada com sucesso!", "success")

            elif "task_content" in request.form:
                list_id = int(request.form.get("list_id"))
                content = request.form.get("task_content")
                if content and check_list_ownership(list_id):
                    new_task = Task(content=content, list_id=list_id)
                    db.session.add(new_task)
                    db.session.commit()
                    flash("Tarefa criada com sucesso!", "success")

            elif "subtask_content" in request.form:
                task_id = int(request.form.get("task_id"))
                content = request.form.get("subtask_content")
                task = Task.query.get(task_id)
                if content and task and check_list_ownership(task.list_id):
                    new_subtask = SubTask(content=content, task_id=task_id)
                    db.session.add(new_subtask)
                    db.session.commit()
                    flash("Subtarefa criada com sucesso!", "success")

            elif "step_content" in request.form:
                subtask_id = int(request.form.get("subtask_id"))
                content = request.form.get("step_content")
                subtask = SubTask.query.get(subtask_id)
                if content and subtask and check_list_ownership(subtask.task.list_id):
                    next_number = len(subtask.steps) + 1
                    new_step = Step(
                        number=next_number,
                        content=content,
                        subtask_id=subtask_id
                    )
                    db.session.add(new_step)
                    db.session.commit()
                    flash("Etapa criada com sucesso!", "success")

        except Exception as e:
            db.session.rollback()
            flash("Erro ao processar sua solicitação. Por favor, tente novamente.", "error")

        return redirect(url_for("index"))

    lists = List.query.filter_by(user_id=user.id).order_by(List.created_at.desc()).all()
    return render_template("index.html", lists=lists, user=user)

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = User.query.get(session["user_id"])
    if request.method == "POST":
        try:
            if "profile_pic" in request.files:
                file = request.files["profile_pic"]
                if file and file.filename != "" and allowed_file(file.filename):
                    if user.profile_pic:
                        old_pic_path = os.path.join(app.config["UPLOAD_FOLDER"], user.profile_pic)
                        if os.path.exists(old_pic_path):
                            os.remove(old_pic_path)
                    
                    filename = secure_filename(f"{user.username}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                    user.profile_pic = filename

            user.name = request.form.get("name", user.name)
            user.phone = request.form.get("phone", user.phone)
            
            if request.form.get("new_password"):
                if user.check_password(request.form.get("current_password", "")):
                    user.set_password(request.form.get("new_password"))
                else:
                    flash("Senha atual incorreta", "error")
                    return redirect(url_for("profile"))

            db.session.commit()
            flash("Perfil atualizado com sucesso!", "success")
            return redirect(url_for("profile"))

        except Exception as e:
            db.session.rollback()
            flash("Erro ao atualizar o perfil. Por favor, tente novamente.", "error")

    return render_template("profile.html", user=user)

# Delete routes
@app.route("/delete_list/<int:list_id>")
@login_required
def delete_list(list_id):
    if not check_list_ownership(list_id):
        flash("Você não tem permissão para excluir esta lista.", "error")
        return redirect(url_for("index"))

    try:
        List.query.filter_by(id=list_id).delete()
        db.session.commit()
        flash("Lista excluída com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Erro ao excluir a lista. Por favor, tente novamente.", "error")

    return redirect(url_for("index"))

@app.route("/delete_task/<int:task_id>")
@login_required
def delete_task(task_id):
    task = Task.query.get(task_id)
    if not task or not check_list_ownership(task.list_id):
        flash("Você não tem permissão para excluir esta tarefa.", "error")
        return redirect(url_for("index"))

    try:
        Task.query.filter_by(id=task_id).delete()
        db.session.commit()
        flash("Tarefa excluída com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Erro ao excluir a tarefa. Por favor, tente novamente.", "error")

    return redirect(url_for("index"))

@app.route("/delete_subtask/<int:subtask_id>")
@login_required
def delete_subtask(subtask_id):
    subtask = SubTask.query.get(subtask_id)
    if not subtask or not check_list_ownership(subtask.task.list_id):
        flash("Você não tem permissão para excluir esta subtarefa.", "error")
        return redirect(url_for("index"))

    try:
        SubTask.query.filter_by(id=subtask_id).delete()
        db.session.commit()
        flash("Subtarefa excluída com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Erro ao excluir a subtarefa. Por favor, tente novamente.", "error")

    return redirect(url_for("index"))

@app.route("/delete_step/<int:step_id>")
@login_required
def delete_step(step_id):
    step = Step.query.get(step_id)
    if not step or not check_list_ownership(step.subtask.task.list_id):
        flash("Você não tem permissão para excluir esta etapa.", "error")
        return redirect(url_for("index"))

    try:
        Step.query.filter_by(id=step_id).delete()
        db.session.commit()
        flash("Etapa excluída com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Erro ao excluir a etapa. Por favor, tente novamente.", "error")

    return redirect(url_for("index"))

# Toggle routes
@app.route("/toggle_task/<int:task_id>")
@login_required
def toggle_task(task_id):
    task = Task.query.get(task_id)
    if not task or not check_list_ownership(task.list_id):
        flash("Você não tem permissão para modificar esta tarefa.", "error")
        return redirect(url_for("index"))

    try:
        task.done = not task.done
        task.completed_at = get_current_time() if task.done else None
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("Erro ao atualizar a tarefa. Por favor, tente novamente.", "error")

    return redirect(url_for("index"))

@app.route("/toggle_subtask/<int:subtask_id>")
@login_required
def toggle_subtask(subtask_id):
    subtask = SubTask.query.get(subtask_id)
    if not subtask or not check_list_ownership(subtask.task.list_id):
        flash("Você não tem permissão para modificar esta subtarefa.", "error")
        return redirect(url_for("index"))

    try:
        subtask.done = not subtask.done
        subtask.completed_at = get_current_time() if subtask.done else None
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("Erro ao atualizar a subtarefa. Por favor, tente novamente.", "error")

    return redirect(url_for("index"))

@app.route("/toggle_step/<int:step_id>")
@login_required
def toggle_step(step_id):
    step = Step.query.get(step_id)
    if not step or not check_list_ownership(step.subtask.task.list_id):
        flash("Você não tem permissão para modificar esta etapa.", "error")
        return redirect(url_for("index"))

    try:
        step.done = not step.done
        step.completed_at = get_current_time() if step.done else None
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash("Erro ao atualizar a etapa. Por favor, tente novamente.", "error")

    return redirect(url_for("index"))

@app.route("/create_steps/<int:subtask_id>", methods=["POST"])
@login_required
def create_steps(subtask_id):
    subtask = SubTask.query.get(subtask_id)
    if not subtask or not check_list_ownership(subtask.task.list_id):
        flash("Você não tem permissão para modificar esta subtarefa.", "error")
        return redirect(url_for("index"))

    try:
        steps_count = int(request.form.get("steps_count", 1))
        Step.query.filter_by(subtask_id=subtask_id).delete()
        
        for i in range(1, steps_count + 1):
            step = Step(
                number=i,
                content=f"Etapa {i}",
                subtask_id=subtask_id
            )
            db.session.add(step)
        
        db.session.commit()
        flash(f"{steps_count} etapas criadas com sucesso!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Erro ao criar etapas. Por favor, tente novamente.", "error")

    return redirect(url_for("index"))

# Função para servir arquivos de imagem do diretório temporário
@app.route('/static/profile_pics/<path:filename>')
def serve_profile_pic(filename):
    if PRODUCTION:
        # Em produção, servir do diretório temporário
        return send_from_directory('/tmp/profile_pics', filename)
    else:
        # Em desenvolvimento, usar o diretório estático normal
        return url_for('static', filename=f'profile_pics/{filename}')

# Inicialização do banco de dados
with app.app_context():
    db.create_all()

# Para testes locais
if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)