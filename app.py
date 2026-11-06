import os
import re
from pathlib import Path
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

# Load private settings from .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)

secret_key = os.environ.get("SECRET_KEY")
if not secret_key or secret_key == "replace_this_with_a_long_random_secret":
    raise RuntimeError("Please set a strong SECRET_KEY in your .env file.")

app.config["SECRET_KEY"] = secret_key
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB upload limit
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

csrf = CSRFProtect(app)




import psycopg
from psycopg.rows import dict_row


class Database:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query, params=()):
        query = query.replace("?", "%s")
        return self.connection.execute(query, params)

    def executescript(self, script):
        for statement in script.split(";"):
            if statement.strip():
                self.connection.execute(statement)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type:
                self.connection.rollback()
            else:
                self.connection.commit()
        finally:
            self.connection.close()


def get_db():
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing!")

    connection = psycopg.connect(
        database_url,
        row_factory=dict_row
    )

    return Database(connection)


def init_db():
    with get_db() as db:
        db.execute("""
            INSERT INTO settings (setting_key, setting_value)
            VALUES (%s, %s)
            ON CONFLICT (setting_key) DO NOTHING
        """, ("applications_open", "1"))

        db.execute("""
            INSERT INTO settings (setting_key, setting_value)
            VALUES (%s, %s)
            ON CONFLICT (setting_key) DO NOTHING
        """, ("application_deadline", ""))


# Initialize the database when the application starts.
init_db()


@app.route("/")
def home():

    with get_db() as db:
        settings = {
            row["setting_key"]: row["setting_value"]
            for row in db.execute(
                "SELECT setting_key, setting_value FROM settings"
            ).fetchall()
        }

        # Retrieve published news for the public website
        news_items = db.execute(
            """
            SELECT id, title, content, created_at
            FROM news
            WHERE published = 1
            ORDER BY created_at DESC
            """
        ).fetchall()

        # Retrieve published projects
        projects = db.execute(
            """
            SELECT id, title, description, status, created_at
            FROM projects
            WHERE published = 1
            ORDER BY created_at DESC
            """
        ).fetchall()

        applications_open = settings.get("applications_open", "1")
        deadline = settings.get("application_deadline", "")

        deadline_passed = False

        if deadline:
            deadline_passed = db.execute(
                """
                SELECT (
                    (CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Addis_Ababa')::date
                    > %s::date
                ) AS deadline_passed
                """,
                (deadline,)
            ).fetchone()["deadline_passed"]

    applications_available = (
        applications_open == "1" and not deadline_passed
    )

    return render_template(
        "index.html",
        applications_available=applications_available,
        application_deadline=deadline,
        news_items=news_items,
        projects=projects
    )

@app.route("/health")
def health():
    return {"status": "ok"}
# Protect private administrator pages
def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        admin_id = session.get("admin_id")

        if not admin_id:
            flash("Please sign in to access the admin area.")
            return redirect(url_for("admin_login"))

        with get_db() as db:
            admin = db.execute(
                "SELECT id, name, role, active FROM admins WHERE id = ?",
                (admin_id,)
            ).fetchone()

        if not admin or not admin["active"]:
            session.clear()
            flash("Your administrator account is inactive.")
            return redirect(url_for("admin_login"))

        return view(*args, **kwargs)

    return wrapped_view


# Administrator login
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        with get_db() as db:
            admin = db.execute(
                """
                SELECT id, name, email, password_hash, role, active
                FROM admins
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

        if (
            admin
            and admin["active"]
            and check_password_hash(admin["password_hash"], password)
        ):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["name"]
            session["admin_role"] = admin["role"]

            return redirect(url_for("admin_dashboard"))

        flash("Invalid email or password.")

    return render_template("admin_login.html")


# Administrator logout
@app.route("/admin/logout")
@admin_required
def admin_logout():
    session.clear()
    flash("You have been signed out successfully.")
    return redirect(url_for("admin_login"))


# Private administrator dashboard
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    with get_db() as db:

        # Count student ideas
        total_ideas = db.execute(
            "SELECT COUNT(*) AS count FROM feedback"
        ).fetchone()["count"]

        # Count reported problems
        total_problems = db.execute(
            "SELECT COUNT(*) AS count FROM school_problems"
        ).fetchone()["count"]

        # Count pending problems
        pending_problems = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM school_problems
            WHERE status = 'Pending'
            """
        ).fetchone()["count"]

        # Count membership applications
        total_applications = db.execute(
            "SELECT COUNT(*) AS count FROM applications"
        ).fetchone()["count"]

        # Count pending applications
        pending_applications = db.execute(
            """
            SELECT COUNT(*) AS count
            FROM applications
            WHERE status = 'Pending'
            """
        ).fetchone()["count"]

        # Retrieve student ideas
        ideas = db.execute(
            """
            SELECT id, message, status, submitted_at
            FROM feedback
            ORDER BY submitted_at DESC
            """
        ).fetchall()

        # Retrieve school problems
        problems = db.execute(
            """
            SELECT id, category, description, status, submitted_at
            FROM school_problems
            ORDER BY submitted_at DESC
            """
        ).fetchall()

        # Retrieve projects
        projects = db.execute(
            """
            SELECT id, title, description, status, published,
                   created_at, updated_at
            FROM projects
            ORDER BY created_at DESC
            """
        ).fetchall()

        # Retrieve news announcements
        news_items = db.execute(
            """
            SELECT id, title, content, published, created_at, updated_at
            FROM news
            ORDER BY created_at DESC
            """
        ).fetchall()

        # Retrieve membership applications
        applications = db.execute(
            """
            SELECT id, full_name, phone, grade_section,
                   email, role, role_reason, motivation,
                   status, submitted_at
            FROM applications
            ORDER BY submitted_at DESC
            """
        ).fetchall()

        # Retrieve membership application settings
        application_settings = {
            row["setting_key"]: row["setting_value"]
            for row in db.execute(
                "SELECT setting_key, setting_value FROM settings"
            ).fetchall()
        }

    return render_template(
        "admin_dashboard.html",
        total_ideas=total_ideas,
        total_problems=total_problems,
        pending_problems=pending_problems,
        total_applications=total_applications,
        pending_applications=pending_applications,
        ideas=ideas,
        problems=problems,
        news_items=news_items,
        projects=projects,
        applications=applications,
        applications_open=application_settings.get("applications_open", "1"),
        application_deadline=application_settings.get("application_deadline", "")
    )
   # Create a news announcement
@app.route("/admin/news/create", methods=["POST"])
@admin_required
def create_news():

    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if not title or not content:
        flash("Please enter both a news title and content.")
        return redirect(url_for("admin_dashboard") + "#news")

    if len(title) > 150 or len(content) > 3000:
        flash("The title or news content is too long.")
        return redirect(url_for("admin_dashboard") + "#news")

    with get_db() as db:
        db.execute(
            """
            INSERT INTO news (title, content, published)
            VALUES (?, ?, 0)
            """,
            (title, content)
        )

    flash("News announcement created successfully. It is currently unpublished.")

    return redirect(url_for("admin_dashboard") + "#news")
# Publish or hide a news announcement
@app.route("/admin/news/<int:news_id>/publish", methods=["POST"])
@admin_required
def toggle_news_publication(news_id):

    with get_db() as db:
        news_item = db.execute(
            "SELECT id, published FROM news WHERE id = ?",
            (news_id,)
        ).fetchone()

        if not news_item:
            flash("News announcement not found.")
            return redirect(url_for("admin_dashboard") + "#news")

        new_status = 0 if news_item["published"] else 1

        db.execute(
            """
            UPDATE news
            SET published = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_status, news_id)
        )

    flash("News publication status updated successfully.")

    return redirect(url_for("admin_dashboard") + "#news")
# Edit a news announcement
@app.route("/admin/news/<int:news_id>/edit", methods=["POST"])
@admin_required
def edit_news(news_id):

    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()

    if not title or not content:
        flash("Please enter both a title and content.")
        return redirect(url_for("admin_dashboard") + "#news")

    if len(title) > 150 or len(content) > 3000:
        flash("The title or news content is too long.")
        return redirect(url_for("admin_dashboard") + "#news")

    with get_db() as db:
        news_item = db.execute(
            "SELECT id FROM news WHERE id = ?",
            (news_id,)
        ).fetchone()

        if not news_item:
            flash("News announcement not found.")
            return redirect(url_for("admin_dashboard") + "#news")

        db.execute(
            """
            UPDATE news
            SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (title, content, news_id)
        )

    flash("News announcement updated successfully.")

    return redirect(url_for("admin_dashboard") + "#news")
# Delete a news announcement
@app.route("/admin/news/<int:news_id>/delete", methods=["POST"])
@admin_required
def delete_news(news_id):

    with get_db() as db:
        news_item = db.execute(
            "SELECT id FROM news WHERE id = ?",
            (news_id,)
        ).fetchone()

        if not news_item:
            flash("News announcement not found.")
            return redirect(url_for("admin_dashboard") + "#news")

        db.execute(
            "DELETE FROM news WHERE id = ?",
            (news_id,)
        )

    flash("News announcement deleted successfully.")

    return redirect(url_for("admin_dashboard") + "#news")

# Create a new project
@app.route("/admin/projects/create", methods=["POST"])
@admin_required
def create_project():

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not title or not description:
        flash("Please enter both a project title and description.")
        return redirect(url_for("admin_dashboard") + "#projects")

    if len(title) > 150 or len(description) > 3000:
        flash("The project title or description is too long.")
        return redirect(url_for("admin_dashboard") + "#projects")

    with get_db() as db:
        db.execute(
            """
            INSERT INTO projects (title, description, status, published)
            VALUES (?, ?, 'Planning', 0)
            """,
            (title, description)
        )

    flash("Project created successfully. It is currently unpublished.")

    return redirect(url_for("admin_dashboard") + "#projects")

# Publish or hide a project
@app.route("/admin/projects/<int:project_id>/publish", methods=["POST"])
@admin_required
def toggle_project_publication(project_id):

    with get_db() as db:
        project = db.execute(
            "SELECT id, published FROM projects WHERE id = ?",
            (project_id,)
        ).fetchone()

        if not project:
            flash("Project not found.")
            return redirect(url_for("admin_dashboard") + "#projects")

        new_status = 0 if project["published"] else 1

        db.execute(
            """
            UPDATE projects
            SET published = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (new_status, project_id)
        )

    flash("Project publication status updated successfully.")

    return redirect(url_for("admin_dashboard") + "#projects")

# Edit an existing project
@app.route("/admin/projects/<int:project_id>/edit", methods=["POST"])
@admin_required
def edit_project(project_id):

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    status = request.form.get("status", "Planning").strip()

    allowed_statuses = ["Planning", "In Progress", "Completed"]

    if not title or not description:
        flash("Please enter both a project title and description.")
        return redirect(url_for("admin_dashboard") + "#projects")

    if len(title) > 150 or len(description) > 3000:
        flash("The project title or description is too long.")
        return redirect(url_for("admin_dashboard") + "#projects")

    if status not in allowed_statuses:
        flash("Invalid project status.")
        return redirect(url_for("admin_dashboard") + "#projects")

    with get_db() as db:
        project = db.execute(
            "SELECT id FROM projects WHERE id = ?",
            (project_id,)
        ).fetchone()

        if not project:
            flash("Project not found.")
            return redirect(url_for("admin_dashboard") + "#projects")

        db.execute(
            """
            UPDATE projects
            SET title = ?, description = ?, status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (title, description, status, project_id)
        )

    flash("Project updated successfully.")

    return redirect(url_for("admin_dashboard") + "#projects")

# Delete a project
@app.route("/admin/projects/<int:project_id>/delete", methods=["POST"])
@admin_required
def delete_project(project_id):

    with get_db() as db:
        project = db.execute(
            "SELECT id FROM projects WHERE id = ?",
            (project_id,)
        ).fetchone()

        if not project:
            flash("Project not found.")
            return redirect(url_for("admin_dashboard") + "#projects")

        db.execute(
            "DELETE FROM projects WHERE id = ?",
            (project_id,)
        )

    flash("Project deleted successfully.")

    return redirect(url_for("admin_dashboard") + "#projects")

# Update membership application settings
@app.route("/admin/application-settings", methods=["POST"])
@admin_required
def update_application_settings():

    applications_open = request.form.get("applications_open", "0")
    deadline = request.form.get("application_deadline", "").strip()

    if applications_open not in {"0", "1"}:
        flash("Invalid application setting.")
        return redirect(url_for("admin_dashboard") + "#applications")

    if deadline:
        try:
            datetime.strptime(deadline, "%Y-%m-%d")
        except ValueError:
            flash("Please enter a valid deadline date.")
            return redirect(url_for("admin_dashboard") + "#applications")

    with get_db() as db:
        db.execute(
            """
            UPDATE settings
            SET setting_value = ?
            WHERE setting_key = 'applications_open'
            """,
            (applications_open,)
        )

        db.execute(
            """
            UPDATE settings
            SET setting_value = ?
            WHERE setting_key = 'application_deadline'
            """,
            (deadline,)
        )

    flash("Membership application settings updated successfully!")

    return redirect(url_for("admin_dashboard") + "#applications")
# Update the status of a membership application
@app.route(
    "/admin/applications/<int:application_id>/status",
    methods=["POST"]
)
@admin_required
def update_application_status(application_id):

    new_status = request.form.get("status", "").strip()

    allowed_statuses = {
        "Pending",
        "Accepted",
        "Rejected"
    }

    if new_status not in allowed_statuses:
        flash("Invalid application status.")
        return redirect(
            url_for("admin_dashboard") + "#applications"
        )

    with get_db() as db:

        application = db.execute(
            "SELECT id FROM applications WHERE id = ?",
            (application_id,)
        ).fetchone()

        if not application:
            flash("Membership application not found.")
            return redirect(
                url_for("admin_dashboard") + "#applications"
            )

        db.execute(
            """
            UPDATE applications
            SET status = ?, reviewed_by = ?
            WHERE id = ?
            """,
            (new_status, session["admin_id"], application_id)
        )

    flash("Membership application status updated successfully.")

    return redirect(
        url_for("admin_dashboard") + "#applications"
    )
# Update the status of a reported school problem
@app.route(
    "/admin/problems/<int:problem_id>/status",
    methods=["POST"]
)
@admin_required
def update_problem_status(problem_id):

    new_status = request.form.get("status", "").strip()

    allowed_statuses = {
        "Pending",
        "In Progress",
        "Solved"
    }

    if new_status not in allowed_statuses:
        flash("Invalid problem status.")
        return redirect(url_for("admin_dashboard") + "#problems")

    with get_db() as db:

        problem = db.execute(
            "SELECT id FROM school_problems WHERE id = ?",
            (problem_id,)
        ).fetchone()

        if not problem:
            flash("School problem not found.")
            return redirect(url_for("admin_dashboard") + "#problems")

        db.execute(
            """
            UPDATE school_problems
            SET status = ?
            WHERE id = ?
            """,
            (new_status, problem_id)
        )

    flash("Problem status updated successfully.")

    return redirect(url_for("admin_dashboard") + "#problems")
# Delete a reported school problem
@app.route(
    "/admin/problems/<int:problem_id>/delete",
    methods=["POST"]
)
@admin_required
def delete_school_problem(problem_id):

    with get_db() as db:

        problem = db.execute(
            "SELECT id FROM school_problems WHERE id = ?",
            (problem_id,)
        ).fetchone()

        if not problem:
            flash("School problem not found.")
            return redirect(
                url_for("admin_dashboard") + "#problems"
            )

        db.execute(
            "DELETE FROM school_problems WHERE id = ?",
            (problem_id,)
        )

    flash("School problem deleted successfully.")

    return redirect(
        url_for("admin_dashboard") + "#problems"
    )

# Update the status of a student idea
@app.route(
    "/admin/ideas/<int:idea_id>/status",
    methods=["POST"]
)
@admin_required
def update_idea_status(idea_id):

    new_status = request.form.get("status", "").strip()

    allowed_statuses = {
        "Pending",
        "Under Review",
        "Accepted",
        "Rejected",
        "Implemented"
    }

    if new_status not in allowed_statuses:
        flash("Invalid idea status.")
        return redirect(url_for("admin_dashboard") + "#feedback")

    with get_db() as db:

        idea = db.execute(
            "SELECT id FROM feedback WHERE id = ?",
            (idea_id,)
        ).fetchone()

        if not idea:
            flash("Student idea not found.")
            return redirect(url_for("admin_dashboard") + "#feedback")

        db.execute(
            """
            UPDATE feedback
            SET status = ?
            WHERE id = ?
            """,
            (new_status, idea_id)
        )

    flash("Student idea status updated successfully.")

    return redirect(url_for("admin_dashboard") + "#feedback")
# Delete a student idea
@app.route(
    "/admin/ideas/<int:idea_id>/delete",
    methods=["POST"]
)
@admin_required
def delete_student_idea(idea_id):

    with get_db() as db:

        idea = db.execute(
            "SELECT id FROM feedback WHERE id = ?",
            (idea_id,)
        ).fetchone()

        if not idea:
            flash("Student idea not found.")
            return redirect(
                url_for("admin_dashboard") + "#feedback"
            )

        db.execute(
            "DELETE FROM feedback WHERE id = ?",
            (idea_id,)
        )

    flash("Student idea deleted successfully.")

    return redirect(
        url_for("admin_dashboard") + "#feedback"
    )
# Submit student feedback
@app.route("/feedback", methods=["POST"])
def submit_feedback():

    message = request.form.get("message", "").strip()

    is_ajax = (
        request.headers.get("X-Requested-With")
        == "XMLHttpRequest"
    )

    def feedback_response(success, text, status=200):
        if is_ajax:
            return {"success": success, "message": text}, status

        flash(text)
        return redirect(url_for("home") + "#feedback")

    if len(message) < 10:
        return feedback_response(
            False, "Please write at least 10 characters.", 400
        )

    if len(message) > 1000:
        return feedback_response(
            False, "Your feedback is too long.", 400
        )

    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO feedback (message) VALUES (?)",
                (message,)
            )

    except psycopg.Error:
        app.logger.exception("Could not save feedback")
        return feedback_response(
            False,
            "We couldn't save your feedback. Please try again.",
            500
        )

    return feedback_response(
        True, "Thank you! Your feedback has been submitted."
    )


# Submit a reported school problem
@app.route("/report-problem", methods=["POST"])
def submit_problem():

    description = request.form.get("description", "").strip()

    is_ajax = (
        request.headers.get("X-Requested-With")
        == "XMLHttpRequest"
    )

    def problem_response(success, message, status=200):
        if is_ajax:
            return {"success": success, "message": message}, status

        flash(message)
        return redirect(url_for("home") + "#report")

    if len(description) < 10:
        return problem_response(
            False,
            "Please describe the problem using at least 10 characters.",
            400
        )

    if len(description) > 1000:
        return problem_response(
            False, "Your description is too long.", 400
        )

    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO school_problems (category, description) VALUES (?, ?)",
                ("General", description)
            )

    except psycopg.Error:
        app.logger.exception("Could not save school problem")
        return problem_response(
            False,
            "We couldn't save your report. Please try again.",
            500
        )

    return problem_response(
        True,
        "Thank you! Your school problem has been reported."
    )
# Submit a membership application
@app.route("/apply", methods=["POST"])
def submit_application():

    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    grade_section = request.form.get("grade_section", "").strip()
    email = request.form.get("email", "").strip()
    role = request.form.get("role", "").strip()
    role_reason = request.form.get("role_reason", "").strip()
    motivation = request.form.get("motivation", "").strip()

    is_ajax = (
        request.headers.get("X-Requested-With")
        == "XMLHttpRequest"
    )

    def application_response(success, message, status=200):
        if is_ajax:
            return {"success": success, "message": message}, status

        flash(message)
        return redirect(url_for("home") + "#join")

    # Check whether membership applications are open
    with get_db() as db:
        settings = {
            row["setting_key"]: row["setting_value"]
            for row in db.execute(
                "SELECT setting_key, setting_value FROM settings"
            ).fetchall()
        }

        applications_open = settings.get("applications_open", "1")
        deadline = settings.get("application_deadline", "")

        deadline_passed = False

        if deadline:
            deadline_passed = db.execute(
                """
                SELECT (
                    (CURRENT_TIMESTAMP AT TIME ZONE 'Africa/Addis_Ababa')::date
                    > %s::date
                ) AS deadline_passed
                """,
                (deadline,)
            ).fetchone()["deadline_passed"]

    if applications_open != "1" or deadline_passed:
        return application_response(
            False,
            "Membership applications are currently closed. Please check again later.",
            403
        )

    # Check required fields
    if not all([
        full_name,
        phone,
        grade_section,
        email,
        role,
        role_reason,
        motivation
    ]):
        return application_response(
            False,
            "Your application is incomplete. Please fill in all required fields.",
            400
        )

    # Validate selected role
    allowed_roles = {
        "Technical Builder / Coder",
        "Problem Identifier / Problem Solver"
    }

    if role not in allowed_roles:
        return application_response(
            False,
            "Please select one valid membership role.",
            400
        )

    # Validate role explanation
    if len(role_reason) < 20 or len(role_reason) > 300:
        return application_response(
            False,
            "Your role explanation must contain between 20 and 300 characters.",
            400
        )

    # Validate full name
    name_parts = full_name.split()

    if (
        len(full_name) > 100
        or len(name_parts) < 2
        or any(
            not part.replace("-", "").replace("'", "").isalpha()
            for part in name_parts
        )
    ):
        return application_response(
            False,
            "Please enter your complete full name, including your first name and last name. Do not use numbers or special characters.",
            400
        )

    # Validate Ethiopian mobile number
    clean_phone = re.sub(r"[\s()-]", "", phone)

    if not re.fullmatch(r"(?:\+251|0)(?:9|7)\d{8}", clean_phone):
        return application_response(
            False,
            "Please enter a valid Ethiopian mobile number, such as 0912345678.",
            400
        )

    # Validate grade
    allowed_grades = {
        "Grade 9",
        "Grade 10",
        "Grade 11",
        "Grade 12"
    }

    if grade_section not in allowed_grades:
        return application_response(
            False,
            "Please select a valid grade.",
            400
        )

    # Validate email
    if len(email) > 254 or not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", email
    ):
        return application_response(
            False,
            "Please enter a valid email address.",
            400
        )

    # Validate motivation length
    if len(motivation) < 50 or len(motivation) > 1000:
        return application_response(
            False,
            "Your motivation must contain between 50 and 1000 characters. Please review your answer.",
            400
        )

    # Save application
    try:
        with get_db() as db:
            db.execute(
                "INSERT INTO applications "
                "(full_name, phone, grade_section, email, role, role_reason, motivation) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    full_name,
                    clean_phone,
                    grade_section,
                    email,
                    role,
                    role_reason,
                    motivation
                )
            )

    except psycopg.Error:
        app.logger.exception("Could not save membership application")
        return application_response(
            False,
            "We couldn't submit your application. Please try again.",
            500
        )

    return application_response(
        True,
        "Application submitted successfully! Thank you for applying to DevSolve Community. Your application is now under review. You will receive the result within one week from the date you applied. Please remember to check both your email inbox and spam/junk folder for our response."
    )
if __name__ == "__main__":
    app.run(debug=os.environ.get("APP_ENV") == "development")