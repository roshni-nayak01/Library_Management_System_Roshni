from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from pymongo import MongoClient
import json
import os
import random

app = Flask(__name__)

# =========================================================
# APP CONFIGURATION
# =========================================================

app.secret_key = "library_secret_key"

bcrypt = Bcrypt(app)

# =========================================================
# MONGODB CONFIGURATION
# =========================================================

books_collection = None

try:
    client = MongoClient(
        "mongodb://localhost:27017/",
        serverSelectionTimeoutMS=3000
    )

    client.admin.command("ping")

    db = client["library_management"]

    books_collection = db["books"]

    print("MongoDB connected successfully.")

except Exception as e:
    print("MongoDB is not connected:", e)
    print("Book Management database functions will not work until MongoDB is available.")


# =========================================================
# EMAIL CONFIGURATION
# =========================================================

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True

app.config["MAIL_USERNAME"] = "YOUR_GMAIL_USERNAME"
app.config["MAIL_PASSWORD"] = "YOUR_GMAIL_APP_PASSWORD"

mail = Mail(app)

USERS_FILE = "users.json"


# =========================================================
# CREATE USERS FILE IF IT DOES NOT EXIST
# =========================================================

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump([], f, indent=4)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)

    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)


def find_user(email):
    users = load_users()

    email = email.strip().lower()

    for user in users:
        if user.get("email", "").strip().lower() == email:
            return user

    return None


def generate_otp():
    return str(random.randint(100000, 999999))


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("home.html")


# =========================================================
# DASHBOARD SELECTION
# =========================================================

@app.route("/dashboard-selection")
def dashboard_selection():

    if "email" not in session:
        return redirect(url_for("login"))

    user_role = session.get("role", "user").lower()

    return render_template(
        "dashboard_selection.html",
        user_role=user_role
    )


# =========================================================
# SELECT ROLE
# =========================================================

@app.route("/select-role/<role>")
def select_role(role):

    allowed_roles = ["user", "librarian", "admin"]

    if role not in allowed_roles:
        return redirect(url_for("dashboard_selection"))

    if "email" not in session:
        return redirect(url_for("login"))

    user_role = session.get("role", "user").lower()

    if user_role == "admin":

        if role == "admin":
            return redirect(url_for("admin_dashboard"))

        if role == "librarian":
            return redirect(url_for("librarian_dashboard"))

        if role == "user":
            return redirect(url_for("dashboard"))

    elif user_role == "librarian":

        if role == "librarian":
            return redirect(url_for("librarian_dashboard"))

        if role == "user":
            return redirect(url_for("dashboard"))

    elif user_role == "user":

        if role == "user":
            return redirect(url_for("dashboard"))

    flash(
        "You are not authorized to access this dashboard.",
        "error"
    )

    return redirect(url_for("dashboard_selection"))


# =========================================================
# COMMON BOOK PAGES
# =========================================================

@app.route("/search-books")
def search_books():

    if "email" not in session:
        return redirect(url_for("login"))

    return render_template("search_books.html")


@app.route("/view-books")
def view_books():


    if "email" not in session:
        return redirect(url_for("login"))

    return render_template("view_books.html")


# =========================================================
# USER MANAGEMENT
# =========================================================

@app.route("/user-management")
def user_management():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") not in ["admin", "librarian"]:

        flash(
            "You are not authorized to access User Management.",
            "error"
        )

        return redirect(
            url_for("back_to_dashboard")
        )

    users = load_users()

    managed_users = []

    for user in users:

        if user.get("role") in ["user", "librarian"]:
            managed_users.append(user)

    return render_template(
        "user_management.html",
        users=managed_users
    )


# =========================================================
# OLD MEMBER MANAGEMENT URL
# =========================================================

@app.route("/member-management")
def member_management():
    return redirect(url_for("user_management"))


# =========================================================
# EDIT USER
# =========================================================

@app.route("/edit-user/<path:email>", methods=["GET", "POST"])
def edit_user(email):

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") not in ["admin", "librarian"]:

        flash(
            "You are not authorized to edit users.",
            "error"
        )

        return redirect(
            url_for("back_to_dashboard")
        )

    users = load_users()

    selected_user = None

    for user in users:

        if (
            user.get("email", "").strip().lower()
            == email.strip().lower()
        ):
            selected_user = user
            break

    if selected_user is None:

        flash(
            "User not found.",
            "error"
        )

        return redirect(
            url_for("user_management")
        )

    if (
        session.get("role") == "librarian"
        and selected_user.get("role") == "admin"
    ):

        flash(
            "Librarians cannot edit admin accounts.",
            "error"
        )

        return redirect(
            url_for("user_management")
        )

    if request.method == "POST":

        new_name = request.form.get(
            "name",
            ""
        ).strip()

        new_email = request.form.get(
            "email",
            ""
        ).strip().lower()

        new_role = request.form.get(
            "role",
            selected_user.get(
                "role",
                "user"
            )
        ).strip().lower()

        if not new_name:

            flash(
                "Name cannot be empty.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_user",
                    email=email
                )
            )

        if not new_email:

            flash(
                "Email cannot be empty.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_user",
                    email=email
                )
            )

        if new_role not in ["user", "librarian"]:

            new_role = selected_user.get(
                "role",
                "user"
            )

        if (
            session.get("role") == "librarian"
            and new_role == "admin"
        ):

            flash(
                "Librarians cannot assign admin role.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_user",
                    email=email
                )
            )

        old_email = selected_user.get(
            "email",
            ""
        ).strip().lower()

        for user in users:

            existing_email = user.get(
                "email",
                ""
            ).strip().lower()

            if (
                existing_email == new_email
                and existing_email != old_email
            ):

                flash(
                    "Another account already uses this email.",
                    "error"
                )

                return redirect(
                    url_for(
                        "edit_user",
                        email=email
                    )
                )

        selected_user["name"] = new_name
        selected_user["email"] = new_email
        selected_user["role"] = new_role

        save_users(users)

        if (
            session.get(
                "email",
                ""
            ).strip().lower()
            == old_email
        ):

            session["email"] = new_email
            session["name"] = new_name
            session["role"] = new_role

        flash(
            "User updated successfully.",
            "success"
        )

        return redirect(
            url_for("user_management")
        )

    return render_template(
        "edit_user.html",
        user=selected_user
    )


# =========================================================
# DELETE USER
# =========================================================

@app.route("/delete-user/<path:email>", methods=["GET", "POST"])
def delete_user(email):

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") not in ["admin", "librarian"]:

        flash(
            "You are not authorized to delete users.",
            "error"
        )

        return redirect(
            url_for("back_to_dashboard")
        )

    users = load_users()

    target_user = None

    for user in users:

        if (
            user.get(
                "email",
                ""
            ).strip().lower()
            == email.strip().lower()
        ):

            target_user = user
            break

    if target_user is None:

        flash(
            "User not found.",
            "error"
        )

        return redirect(
            url_for("user_management")
        )

    target_email = target_user.get(
        "email",
        ""
    ).strip().lower()

    logged_in_email = session.get(
        "email",
        ""
    ).strip().lower()

    if target_email == logged_in_email:

        flash(
            "You cannot delete your own account.",
            "error"
        )

        return redirect(
            url_for("user_management")
        )

    if (
        session.get("role") == "librarian"
        and target_user.get("role") == "admin"
    ):

        flash(
            "Librarians cannot delete admin accounts.",
            "error"
        )

        return redirect(
            url_for("user_management")
        )

    users = [
        user
        for user in users
        if user.get(
            "email",
            ""
        ).strip().lower() != target_email
    ]

    save_users(users)

    flash(
        "User deleted successfully.",
        "success"
    )

    return redirect(
        url_for("user_management")
    )


# =========================================================
# BOOK MANAGEMENT
# =========================================================

@app.route("/book-management")
def book_management():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") not in ["admin", "librarian"]:
        return redirect(url_for("login"))

    books = []

    try:

        if books_collection is not None:

            books = list(
                books_collection.find(
                    {},
                    {
                        "_id": 0
                    }
                )
            )

        else:

            flash(
                "MongoDB is not connected.",
                "error"
            )

    except Exception as e:

        print(
            "Error loading books:",
            e
        )

        books = []

        flash(
            "Unable to load books.",
            "error"
        )

    return render_template(
        "book_management.html",
        books=books
    )


# =========================================================
# ADD BOOK
# =========================================================

@app.route("/add_book", methods=["POST"])
def add_book():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") not in ["admin", "librarian"]:
        return redirect(url_for("login"))

    if books_collection is None:

        flash(
            "MongoDB is not connected.",
            "error"
        )

        return redirect(
            url_for("book_management")
        )

    try:

        book_id = request.form.get(
            "book_id",
            ""
        ).strip()

        book_name = request.form.get(
            "book_name",
            ""
        ).strip()

        author = request.form.get(
            "author",
            ""
        ).strip()

        publisher = request.form.get(
            "publisher",
            ""
        ).strip()

        isbn = request.form.get(
            "isbn",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        copies = request.form.get(
            "copies",
            "0"
        ).strip()

        if (
            not book_id
            or not book_name
            or not author
            or not category
        ):

            flash(
                "Please fill all required fields.",
                "error"
            )

            return redirect(
                url_for("book_management")
            )

        try:
            copies = int(copies)
        except (ValueError, TypeError):
            copies = 0

        if copies < 0:
            copies = 0

        existing_book = books_collection.find_one({
            "book_id": book_id
        })

        if existing_book:

            flash(
                "Book ID already exists.",
                "error"
            )

            return redirect(
                url_for("book_management")
            )

        new_book = {
            "book_id": book_id,
            "book_name": book_name,
            "author": author,
            "publisher": publisher,
            "isbn": isbn,
            "category": category,
            "copies": copies
        }

        books_collection.insert_one(
            new_book
        )

        flash(
            "Book added successfully.",
            "success"
        )

    except Exception as e:

        print(
            "Error adding book:",
            e
        )

        flash(
            "Error adding book.",
            "error"
        )

    return redirect(
        url_for("book_management")
    )


# =========================================================
# EDIT BOOK
# =========================================================

@app.route(
    "/edit_book/<book_id>",
    methods=["GET", "POST"]
)
def edit_book(book_id):

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") not in ["admin", "librarian"]:
        return redirect(url_for("login"))

    if books_collection is None:

        flash(
            "MongoDB is not connected.",
            "error"
        )

        return redirect(
            url_for("book_management")
        )

    try:

        book = books_collection.find_one({
            "book_id": book_id
        })

        if not book:

            flash(
                "Book not found.",
                "error"
            )

            return redirect(
                url_for("book_management")
            )

        if request.method == "POST":

            book_name = request.form.get(
                "book_name",
                ""
            ).strip()

            author = request.form.get(
                "author",
                ""
            ).strip()

            publisher = request.form.get(
                "publisher",
                ""
            ).strip()

            isbn = request.form.get(
                "isbn",
                ""
            ).strip()

            category = request.form.get(
                "category",
                ""
            ).strip()

            copies = request.form.get(
                "copies",
                "0"
            ).strip()

            try:
                copies = int(copies)
            except (ValueError, TypeError):
                copies = 0

            if copies < 0:
                copies = 0

            books_collection.update_one(
                {
                    "book_id": book_id
                },
                {
                    "$set": {
                        "book_name": book_name,
                        "author": author,
                        "publisher": publisher,
                        "isbn": isbn,
                        "category": category,
                        "copies": copies
                    }
                }
            )

            flash(
                "Book updated successfully.",
                "success"
            )

            return redirect(
                url_for("book_management")
            )

        return render_template(
            "edit_book.html",
            book=book
        )

    except Exception as e:

        print(
            "Error editing book:",
            e
        )

        flash(
            "Error editing book.",
            "error"
        )

        return redirect(
            url_for("book_management")
        )


# =========================================================
# DELETE BOOK
# =========================================================

@app.route("/delete_book/<book_id>")
def delete_book(book_id):

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") not in ["admin", "librarian"]:
        return redirect(url_for("login"))

    if books_collection is None:

        flash(
            "MongoDB is not connected.",
            "error"
        )

        return redirect(
            url_for("book_management")
        )

    try:

        result = books_collection.delete_one({
            "book_id": book_id
        })

        if result.deleted_count > 0:

            flash(
                "Book deleted successfully.",
                "success"
            )

        else:

            flash(
                "Book not found.",
                "error"
            )

    except Exception as e:

        print(
            "Error deleting book:",
            e
        )

        flash(
            "Error deleting book.",
            "error"
        )

    return redirect(
        url_for("book_management")
    )


# =========================================================
# LIBRARIAN MANAGEMENT
# =========================================================

@app.route("/librarian-management")
def librarian_management():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    users = load_users()

    librarians = [
        user
        for user in users
        if user.get("role") == "librarian"
    ]

    return render_template(
        "librarian_management.html",
        librarians=librarians
    )


# =========================================================
# EDIT LIBRARIAN
# =========================================================

@app.route(
    "/edit-librarian/<path:email>",
    methods=["GET", "POST"]
)
def edit_librarian(email):

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    users = load_users()

    librarian = None

    for user in users:

        if (
            user.get(
                "email",
                ""
            ).strip().lower()
            == email.strip().lower()
            and user.get("role") == "librarian"
        ):

            librarian = user
            break

    if librarian is None:

        flash(
            "Librarian not found.",
            "error"
        )

        return redirect(
            url_for("librarian_management")
        )

    if request.method == "POST":

        new_name = request.form.get(
            "name",
            ""
        ).strip()

        new_email = request.form.get(
            "email",
            ""
        ).strip().lower()

        if not new_name or not new_email:

            flash(
                "Name and email are required.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_librarian",
                    email=email
                )
            )

        for user in users:

            if user is librarian:
                continue

            if (
                user.get(
                    "email",
                    ""
                ).strip().lower()
                == new_email
            ):

                flash(
                    "Email already exists.",
                    "error"
                )

                return redirect(
                    url_for(
                        "edit_librarian",
                        email=email
                    )
                )

        librarian["name"] = new_name
        librarian["email"] = new_email

        save_users(users)

        flash(
            "Librarian updated successfully.",
            "success"
        )

        return redirect(
            url_for("librarian_management")
        )

    return render_template(
        "edit_librarian.html",
        librarian=librarian
    )


# =========================================================
# DELETE LIBRARIAN
# =========================================================

@app.route("/delete-librarian/<path:email>")
def delete_librarian(email):

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    users = load_users()

    new_users = []

    deleted = False

    for user in users:

        if (
            user.get(
                "email",
                ""
            ).strip().lower()
            == email.strip().lower()
            and user.get("role") == "librarian"
        ):

            deleted = True
            continue

        new_users.append(user)

    if deleted:

        save_users(new_users)

        flash(
            "Librarian deleted successfully.",
            "success"
        )

    else:

        flash(
            "Librarian not found.",
            "error"
        )

    return redirect(
        url_for("librarian_management")
    )


# =========================================================
# LIBRARIAN FUNCTIONS
# =========================================================

@app.route("/issue-books")
def issue_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template(
        "issue_books.html"
    )


@app.route("/librarian-return-books")
def librarian_return_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template(
        "librarian_return_books.html"
    )


@app.route("/librarian-renew-books")
def librarian_renew_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template(
        "renew_books.html"
    )


@app.route("/waitlist-management")
def waitlist_management():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template(
        "waitlist_management.html"
    )


@app.route("/fine-management")
def fine_management():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template(
        "fine_management.html"
    )


@app.route("/book-availability")
def book_availability():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template(
        "book_availability.html"
    )


@app.route("/borrow-records")
def borrow_records():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template(
        "borrow_records.html"
    )


# =========================================================
# ADMIN RENEW BOOKS
# =========================================================

@app.route("/admin-renew-books")
def admin_renew_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    return render_template(
        "renew_books.html"
    )


# =========================================================
# REPORTS
# =========================================================

@app.route("/reports")
def reports():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") not in ["admin", "librarian"]:
        return redirect(url_for("login"))

    return render_template(
        "reports.html"
    )


# =========================================================
# CATEGORIES
# =========================================================

@app.route("/categories")
def categories():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") not in ["admin", "librarian"]:
        return redirect(url_for("login"))

    return render_template(
        "categories.html"
    )


# =========================================================
# USER - BORROW BOOKS
# =========================================================

@app.route("/borrow_books")
def borrow_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "user":
        return redirect(url_for("login"))

    return render_template(
        "borrow_books.html"
    )


# =========================================================
# USER - RETURN BOOKS
# =========================================================

@app.route("/return_books")
def return_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "user":
        return redirect(url_for("login"))

    return render_template(
        "return_books.html"
    )


# =========================================================
# USER - RENEW BOOKS
# =========================================================

@app.route(
    "/renew-books",
    methods=["GET", "POST"]
)
def renew_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "user":
        return redirect(url_for("login"))

    if request.method == "POST":

        book_id = request.form.get(
            "book_id",
            ""
        ).strip()

        if not book_id:

            flash(
                "Please enter a Book ID.",
                "error"
            )

            return redirect(
                url_for("renew_books")
            )

        flash(
            f"Renew request received for Book ID {book_id}.",
            "success"
        )

        return redirect(
            url_for("renew_books")
        )

    return render_template(
        "renew_books.html"
    )


# =========================================================
# USER - RESERVE BOOKS
# =========================================================

@app.route(
    "/reserve-books",
    methods=["GET", "POST"]
)
def reserve_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "user":
        return redirect(url_for("login"))

    if request.method == "POST":

        book_id = request.form.get(
            "book_id",
            ""
        ).strip()

        if not book_id:

            flash(
                "Please enter a Book ID.",
                "error"
            )

            return redirect(
                url_for("reserve_books")
            )

        flash(
            f"Reservation request received for Book ID {book_id}.",
            "success"
        )

        return redirect(
            url_for("reserve_books")
        )

    return render_template(
        "reserve_books.html"
    )


# =========================================================
# USER - BORROW HISTORY
# =========================================================

@app.route("/borrow_history")
def borrow_history():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "user":
        return redirect(url_for("login"))

    return render_template(
        "borrow_history.html"
    )


# =========================================================
# BACK TO CORRESPONDING DASHBOARD
# =========================================================

@app.route("/back-to-dashboard")
def back_to_dashboard():

    if "email" not in session:
        return redirect(url_for("login"))

    role = session.get("role")

    if role == "admin":
        return redirect(
            url_for("admin_dashboard")
        )

    if role == "librarian":
        return redirect(
            url_for("librarian_dashboard")
        )

    if role == "user":
        return redirect(
            url_for("dashboard")
        )

    return redirect(
        url_for("login")
    )


# =========================================================
# GO DASHBOARD
# =========================================================

@app.route("/go-dashboard")
def go_dashboard():
    return back_to_dashboard()


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        role = request.form.get(
            "role",
            "user"
        ).strip().lower()

        if not name or not email or not password:

            flash(
                "All fields are required.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        if role not in [
            "user",
            "librarian",
            "admin"
        ]:

            role = "user"

        users = load_users()

        for user in users:

            if (
                user.get(
                    "email",
                    ""
                ).strip().lower()
                == email
            ):

                flash(
                    "Email already exists.",
                    "error"
                )

                return redirect(
                    url_for("register")
                )

        hashed_password = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

        users.append({
            "name": name,
            "email": email,
            "password": hashed_password,
            "role": role
        })

        save_users(users)

        session["selected_role"] = role

        flash(
            "Registration Successful!",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        selected_role = session.get(
            "selected_role"
        )

        user = find_user(email)

        if user is None:

            flash(
                "Invalid Email or Password",
                "error"
            )

            return render_template(
                "login.html"
            )

        stored_password = user.get(
            "password",
            ""
        )

        try:

            password_match = bcrypt.check_password_hash(
                stored_password,
                password
            )

        except Exception:

            password_match = False

        if not password_match:

            flash(
                "Invalid Email or Password",
                "error"
            )

            return render_template(
                "login.html"
            )

        user_role = user.get(
            "role",
            "user"
        ).lower()

        if (
            selected_role is not None
            and user_role != selected_role
        ):

            flash(
                "Selected role does not match your account.",
                "error"
            )

            return render_template(
                "login.html"
            )

        session["email"] = user.get(
            "email"
        )

        session["name"] = user.get(
            "name"
        )

        session["role"] = user_role

        session.pop(
            "selected_role",
            None
        )

        return redirect(
            url_for("dashboard_selection")
        )

    return render_template(
        "login.html"
    )


# =========================================================
# USER DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "user":
        return redirect(url_for("login"))

    return render_template(
        "user_dashboard.html",
        name=session.get(
            "name",
            "User"
        )
    )


# =========================================================
# LIBRARIAN DASHBOARD
# =========================================================

@app.route("/librarian-dashboard")
def librarian_dashboard():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template(
        "librarian_dashboard.html",
        name=session.get(
            "name",
            "Librarian"
        )
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin-dashboard")
def admin_dashboard():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    return render_template(
        "admin_dashboard.html",
        name=session.get(
            "name",
            "Admin"
        )
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================================================
# PROFILE
# =========================================================

@app.route(
    "/profile",
    methods=["GET", "POST"]
)
def profile():

    if "email" not in session:
        return redirect(url_for("login"))

    users = load_users()

    current_user = None

    for user in users:

        if (
            user.get(
                "email",
                ""
            ).strip().lower()
            == session.get(
                "email",
                ""
            ).strip().lower()
        ):

            current_user = user
            break

    if current_user is None:

        session.clear()

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        new_name = request.form.get(
            "name",
            ""
        ).strip()

        if not new_name:

            flash(
                "Name cannot be empty.",
                "error"
            )

            return redirect(
                url_for("profile")
            )

        current_user["name"] = new_name

        session["name"] = new_name

        save_users(users)

        flash(
            "Profile Updated Successfully.",
            "success"
        )

        return redirect(
            url_for("profile")
        )

    return render_template(
        "profile.html",
        user=current_user
    )


# =========================================================
# CHANGE PASSWORD
# =========================================================

@app.route(
    "/change-password",
    methods=["GET", "POST"]
)
def change_password():

    if "email" not in session:
        return redirect(url_for("login"))

    users = load_users()

    current_user = None

    for user in users:

        if (
            user.get(
                "email",
                ""
            ).strip().lower()
            == session.get(
                "email",
                ""
            ).strip().lower()
        ):

            current_user = user
            break

    if current_user is None:

        session.clear()

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        old_password = request.form.get(
            "old_password",
            ""
        )

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not bcrypt.check_password_hash(
            current_user["password"],
            old_password
        ):

            flash(
                "Old Password is Incorrect.",
                "error"
            )

            return redirect(
                url_for("change_password")
            )

        if new_password != confirm_password:

            flash(
                "New Password and Confirm Password do not match.",
                "error"
            )

            return redirect(
                url_for("change_password")
            )

        if bcrypt.check_password_hash(
            current_user["password"],
            new_password
        ):

            flash(
                "New Password cannot be the same as the current password.",
                "error"
            )

            return redirect(
                url_for("change_password")
            )

        current_user["password"] = bcrypt.generate_password_hash(
            new_password
        ).decode("utf-8")

        save_users(users)

        flash(
            "Password Changed Successfully.",
            "success"
        )

        return redirect(
            url_for("back_to_dashboard")
        )

    return render_template(
        "change_password.html"
    )


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.route(
    "/forgot-password",
    methods=["GET", "POST"]
)
def forgot_password():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        user = find_user(email)

        if user is None:

            flash(
                "No account found with this email.",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

        otp = generate_otp()

        session["reset_email"] = email
        session["otp"] = otp

        try:

            msg = Message(
                subject="Library Password Reset OTP",
                sender=app.config["MAIL_USERNAME"],
                recipients=[email]
            )

            msg.body = f"""
Hello,

Your OTP for resetting the password is:

{otp}

This OTP is valid for one use.

Thank You
Library Management System
"""

            mail.send(msg)

            flash(
                "OTP Sent Successfully.",
                "success"
            )

        except Exception as e:

            print(
                "EMAIL ERROR:",
                e
            )

            flash(
                "Unable to Send OTP.",
                "error"
            )

        return redirect(
            url_for("verify_otp")
        )

    return render_template(
        "forgot_password.html"
    )


# =========================================================
# VERIFY OTP
# =========================================================

@app.route(
    "/verify-otp",
    methods=["GET", "POST"]
)
def verify_otp():

    if request.method == "POST":

        entered_otp = request.form.get(
            "otp",
            ""
        ).strip()

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if (
            "otp" not in session
            or "reset_email" not in session
        ):

            flash(
                "OTP Expired.",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

        if entered_otp != session.get(
            "otp"
        ):

            flash(
                "Invalid OTP.",
                "error"
            )

            return redirect(
                url_for("verify_otp")
            )

        if new_password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("verify_otp")
            )

        users = load_users()

        reset_email = session.get(
            "reset_email"
        )

        user_found = False

        for user in users:

            if (
                user.get(
                    "email",
                    ""
                ).strip().lower()
                == reset_email
            ):

                user["password"] = bcrypt.generate_password_hash(
                    new_password
                ).decode("utf-8")

                user_found = True

                break

        if not user_found:

            flash(
                "User account not found.",
                "error"
            )

            return redirect(
                url_for("forgot_password")
            )

        save_users(users)

        session.pop(
            "otp",
            None
        )

        session.pop(
            "reset_email",
            None
        )

        flash(
            "Password Reset Successful.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "verify_otp.html"
    )


# =========================================================
# PRINT ROUTES
# =========================================================

print("\n========== FLASK ROUTES ==========")

for rule in app.url_map.iter_rules():
    print(rule)

print("==================================\n")


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)