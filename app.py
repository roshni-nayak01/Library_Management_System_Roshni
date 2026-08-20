from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
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
# EMAIL CONFIGURATION
# =========================================================

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True

# PUT YOUR EXISTING GMAIL DETAILS HERE
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

    # User must already be logged in
    if "email" not in session:
        return redirect(url_for("login"))

    user_role = session.get("role", "user").lower()

    # =====================================================
    # ADMIN
    # Admin can select Admin, Librarian or User
    # =====================================================

    if user_role == "admin":

        if role == "admin":
            return redirect(url_for("admin_dashboard"))

        if role == "librarian":
            return redirect(url_for("librarian_dashboard"))

        if role == "user":
            return redirect(url_for("dashboard"))


    # =====================================================
    # LIBRARIAN
    # Librarian can select Librarian or User
    # =====================================================

    elif user_role == "librarian":

        if role == "librarian":
            return redirect(url_for("librarian_dashboard"))

        if role == "user":
            return redirect(url_for("dashboard"))


    # =====================================================
    # USER
    # User can select only User
    # =====================================================

    elif user_role == "user":

        if role == "user":
            return redirect(url_for("dashboard"))


    # =====================================================
    # UNAUTHORIZED
    # =====================================================

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

    # Load books from books.json
    if os.path.exists("books.json"):

        with open("books.json", "r") as file:
            books = json.load(file)

    else:

        books = []

    return render_template(
        "view_books.html",
        books=books
    )

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
        return redirect(url_for("back_to_dashboard"))

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
        flash("You are not authorized to edit users.", "error")
        return redirect(url_for("back_to_dashboard"))

    users = load_users()

    selected_user = None

    for user in users:

        if user.get("email", "").strip().lower() == email.strip().lower():

            selected_user = user
            break

    if selected_user is None:

        flash("User not found.", "error")

        return redirect(url_for("user_management"))

    # Librarian cannot edit admin
    if (
        session.get("role") == "librarian"
        and selected_user.get("role") == "admin"
    ):

        flash("Librarians cannot edit admin accounts.", "error")

        return redirect(url_for("user_management"))

    # =====================================================
    # SAVE EDITED USER
    # =====================================================

    if request.method == "POST":

        new_name = request.form.get("name", "").strip()

        new_email = request.form.get("email", "").strip().lower()

        new_role = request.form.get(
            "role",
            selected_user.get("role", "user")
        ).strip().lower()

        # Name validation
        if not new_name:

            flash("Name cannot be empty.", "error")

            return redirect(
                url_for(
                    "edit_user",
                    email=email
                )
            )

        # Email validation
        if not new_email:

            flash("Email cannot be empty.", "error")

            return redirect(
                url_for(
                    "edit_user",
                    email=email
                )
            )

        # Only these roles can be assigned here
        if new_role not in ["user", "librarian"]:

            new_role = selected_user.get(
                "role",
                "user"
            )

        # Librarian cannot create admin
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

        # =================================================
        # CHECK DUPLICATE EMAIL
        # =================================================

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

        # =================================================
        # UPDATE USER
        # =================================================

        selected_user["name"] = new_name

        selected_user["email"] = new_email

        selected_user["role"] = new_role

        save_users(users)

        # Update session if current user edited themselves
        if (
            session.get("email", "").strip().lower()
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

    # =====================================================
    # OPEN EDIT PAGE
    # =====================================================

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
            user.get("email", "").strip().lower()
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

    # Cannot delete yourself
    if target_email == logged_in_email:

        flash(
            "You cannot delete your own account.",
            "error"
        )

        return redirect(
            url_for("user_management")
        )

    # Librarian cannot delete admin
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

    # =====================================================
    # DELETE
    # =====================================================

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


# =========================================================
# BOOK MANAGEMENT
# =========================================================
@app.route("/book-management")
def book_management():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") not in ["admin", "librarian"]:
        return redirect(url_for("login"))

    # Load books from books.json
    if os.path.exists("books.json"):

        with open("books.json", "r") as file:
            books = json.load(file)

    else:
        books = []

    return render_template(
        "book_management.html",
        books=books
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
        user for user in users
        if user.get("role") == "librarian"
    ]

    return render_template(
        "librarian_management.html",
        librarians=librarians
    )


# =========================================================
# EDIT LIBRARIAN
# =========================================================

@app.route("/edit-librarian/<path:email>", methods=["GET", "POST"])
def edit_librarian(email):

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    users = load_users()

    librarian = None

    for user in users:

        if (
            user.get("email", "").strip().lower() == email.strip().lower()
            and user.get("role") == "librarian"
        ):
            librarian = user
            break

    if librarian is None:
        flash("Librarian not found.", "error")
        return redirect(url_for("librarian_management"))

    if request.method == "POST":

        new_name = request.form.get("name", "").strip()
        new_email = request.form.get("email", "").strip().lower()

        if not new_name or not new_email:
            flash("Name and email are required.", "error")
            return redirect(url_for("edit_librarian", email=email))

        for user in users:

            if user is librarian:
                continue

            if user.get("email", "").strip().lower() == new_email:
                flash("Email already exists.", "error")
                return redirect(url_for("edit_librarian", email=email))

        librarian["name"] = new_name
        librarian["email"] = new_email

        save_users(users)

        flash("Librarian updated successfully.", "success")

        return redirect(url_for("librarian_management"))

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
            user.get("email", "").strip().lower() == email.strip().lower()
            and user.get("role") == "librarian"
        ):
            deleted = True
            continue

        new_users.append(user)

    if deleted:
        save_users(new_users)
        flash("Librarian deleted successfully.", "success")
    else:
        flash("Librarian not found.", "error")

    return redirect(url_for("librarian_management"))


# =========================================================
# LIBRARIAN FUNCTIONS
# =========================================================

@app.route("/issue-books")
def issue_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template("issue_books.html")


@app.route("/librarian-return-books")
def librarian_return_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template("librarian_return_books.html")


@app.route("/librarian-renew-books")
def librarian_renew_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template("renew_books.html")


@app.route("/waitlist-management")
def waitlist_management():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template("waitlist_management.html")


@app.route("/fine-management")
def fine_management():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template("fine_management.html")


@app.route("/book-availability")
def book_availability():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template("book_availability.html")


@app.route("/borrow-records")
def borrow_records():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        return redirect(url_for("login"))

    return render_template("borrow_records.html")


# =========================================================
# ADMIN RENEW BOOKS
# =========================================================

@app.route("/admin-renew-books")
def admin_renew_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    return render_template("renew_books.html")

@app.route("/add-book", methods=["POST"])
def add_book():

    if "email" not in session:
        return redirect(url_for("login"))

    book_id = request.form.get("book_id", "").strip()
    book_name = request.form.get("book_name", "").strip()
    author = request.form.get("author", "").strip()
    publisher = request.form.get("publisher", "").strip()
    isbn = request.form.get("isbn", "").strip()
    category = request.form.get("category", "").strip()
    copies = request.form.get("copies", "0").strip()

    if not book_id or not book_name or not author or not category:
        flash("Please fill all required fields.", "error")
        return redirect(url_for("book_management"))

    try:
        copies = int(copies)
    except ValueError:
        flash("Copies must be a number.", "error")
        return redirect(url_for("book_management"))

    # Load existing books
    if os.path.exists("books.json"):
        with open("books.json", "r") as file:
            books = json.load(file)
    else:
        books = []

    # Check duplicate Book ID
    for book in books:
        if book.get("book_id") == book_id:
            flash("Book ID already exists.", "error")
            return redirect(url_for("book_management"))

    # Create new book
    new_book = {
        "book_id": book_id,
        "book_name": book_name,
        "author": author,
        "publisher": publisher,
        "isbn": isbn,
        "category": category,
        "copies": copies
    }

    # Add book
    books.append(new_book)

    # Save book
    with open("books.json", "w") as file:
        json.dump(books, file, indent=4)

    flash("Book added successfully!", "success")

    return redirect(url_for("book_management"))


@app.route("/edit-book/<book_id>", methods=["GET", "POST"])
def edit_book(book_id):

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") not in ["admin", "librarian"]:
        return redirect(url_for("login"))

    # Load books
    if os.path.exists("books.json"):
        with open("books.json", "r") as file:
            books = json.load(file)
    else:
        books = []

    # Find the selected book
    book = None

    for item in books:
        if item.get("book_id") == book_id:
            book = item
            break

    # Book not found
    if book is None:
        flash("Book not found.", "error")
        return redirect(url_for("book_management"))

    # Save edited book
    if request.method == "POST":

        book["book_name"] = request.form.get(
            "book_name", ""
        ).strip()

        book["author"] = request.form.get(
            "author", ""
        ).strip()

        book["publisher"] = request.form.get(
            "publisher", ""
        ).strip()

        book["isbn"] = request.form.get(
            "isbn", ""
        ).strip()

        book["category"] = request.form.get(
            "category", ""
        ).strip()

        copies = request.form.get(
            "copies", "0"
        ).strip()

        try:
            book["copies"] = int(copies)
        except ValueError:
            flash("Copies must be a number.", "error")
            return redirect(
                url_for("edit_book", book_id=book_id)
            )

        # Save changes to books.json
        with open("books.json", "w") as file:
            json.dump(books, file, indent=4)

        flash("Book updated successfully!", "success")

        return redirect(url_for("book_management"))

    # Show edit page
    return render_template(
        "edit_book.html",
        book=book
    )



@app.route("/delete-book/<book_id>")
def delete_book(book_id):

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") not in ["admin", "librarian"]:
        return redirect(url_for("login"))

    # Load books
    if os.path.exists("books.json"):
        with open("books.json", "r") as file:
            books = json.load(file)
    else:
        books = []

    # Remove selected book
    updated_books = []

    book_found = False

    for book in books:

        if book.get("book_id") == book_id:
            book_found = True
        else:
            updated_books.append(book)

    if not book_found:
        flash("Book not found.", "error")
        return redirect(url_for("book_management"))

    # Save updated books
    with open("books.json", "w") as file:
        json.dump(updated_books, file, indent=4)

    flash("Book deleted successfully!", "success")

    return redirect(url_for("book_management"))

# =========================================================
# REPORTS
# =========================================================

@app.route("/reports")
def reports():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") not in ["admin", "librarian"]:
        return redirect(url_for("login"))

    return render_template("reports.html")


# =========================================================
# CATEGORIES
# =========================================================

@app.route("/categories")
def categories():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") not in ["admin", "librarian"]:
        return redirect(url_for("login"))

    return render_template("categories.html")


# =========================================================
# USER - BORROW BOOKS
# =========================================================

@app.route("/borrow_books")
def borrow_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "user":
        return redirect(url_for("login"))

    return render_template("borrow_books.html")


# =========================================================
# USER - RETURN BOOKS
# =========================================================

@app.route("/return_books")
def return_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "user":
        return redirect(url_for("login"))

    return render_template("return_books.html")


# =========================================================
# USER - RENEW BOOKS
# =========================================================

@app.route("/renew-books", methods=["GET", "POST"])
def renew_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "user":
        return redirect(url_for("login"))

    if request.method == "POST":

        book_id = request.form.get("book_id", "").strip()

        if not book_id:
            flash("Please enter a Book ID.", "error")
            return redirect(url_for("renew_books"))

        flash(
            f"Renew request received for Book ID {book_id}.",
            "success"
        )

        return redirect(url_for("renew_books"))

    return render_template("renew_books.html")


# =========================================================
# USER - RESERVE BOOKS
# =========================================================

@app.route("/reserve-books", methods=["GET", "POST"])
def reserve_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "user":
        return redirect(url_for("login"))

    if request.method == "POST":

        book_id = request.form.get("book_id", "").strip()

        if not book_id:
            flash("Please enter a Book ID.", "error")
            return redirect(url_for("reserve_books"))

        flash(
            f"Reservation request received for Book ID {book_id}.",
            "success"
        )

        return redirect(url_for("reserve_books"))

    return render_template("reserve_books.html")


# =========================================================
# USER - BORROW HISTORY
# =========================================================

@app.route("/borrow_history")
def borrow_history():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "user":
        return redirect(url_for("login"))

    return render_template("borrow_history.html")


# =========================================================
# BACK TO CORRESPONDING DASHBOARD
# =========================================================

@app.route("/back-to-dashboard")
def back_to_dashboard():

    if "email" not in session:
        return redirect(url_for("login"))

    role = session.get("role")

    if role == "admin":
        return redirect(url_for("admin_dashboard"))

    if role == "librarian":
        return redirect(url_for("librarian_dashboard"))

    if role == "user":
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


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

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "user").strip().lower()

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        if role not in ["user", "librarian", "admin"]:
            role = "user"

        users = load_users()

        for user in users:

            if user.get("email", "").strip().lower() == email:
                flash("Email already exists.", "error")
                return redirect(url_for("register"))

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

        flash("Registration Successful!", "success")

        return redirect(url_for("login"))

    return render_template("register.html")

# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        selected_role = session.get("selected_role")

        user = find_user(email)

        if user is None:
            flash("Invalid Email or Password", "error")
            return render_template("login.html")

        stored_password = user.get("password", "")

        try:
            password_match = bcrypt.check_password_hash(
                stored_password,
                password
            )
        except Exception:
            password_match = False

        if not password_match:
            flash("Invalid Email or Password", "error")
            return render_template("login.html")

        user_role = user.get("role", "user").lower()

        # If a role was selected before login,
        # make sure it matches the actual account role.
        if selected_role is not None and user_role != selected_role:
            flash(
                "Selected role does not match your account.",
                "error"
            )
            return render_template("login.html")

        # Store logged-in user information
        session["email"] = user.get("email")
        session["name"] = user.get("name")
        session["role"] = user_role

        # Remove temporary selected role
        session.pop("selected_role", None)

        # Redirect based on actual account role
        if user_role == "user":
            return redirect(url_for("dashboard"))

        elif user_role == "librarian":
            return redirect(url_for("dashboard_selection"))

        elif user_role == "admin":
            return redirect(url_for("dashboard_selection"))

        return redirect(url_for("login"))

    return render_template("login.html")


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
        name=session.get("name", "User")
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
        name=session.get("name", "Librarian")
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
        name=session.get("name", "Admin")
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("home"))


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "email" not in session:
        return redirect(url_for("login"))

    users = load_users()

    current_user = None

    for user in users:

        if user.get("email", "").strip().lower() == session.get("email", "").strip().lower():
            current_user = user
            break

    if current_user is None:

        session.clear()

        return redirect(url_for("login"))

    if request.method == "POST":

        new_name = request.form.get("name", "").strip()

        if not new_name:
            flash("Name cannot be empty.", "error")
            return redirect(url_for("profile"))

        current_user["name"] = new_name

        session["name"] = new_name

        save_users(users)

        flash("Profile Updated Successfully.", "success")

        return redirect(url_for("profile"))

    return render_template(
        "profile.html",
        user=current_user
    )


# =========================================================
# CHANGE PASSWORD
# =========================================================

@app.route("/change-password", methods=["GET", "POST"])
def change_password():

    if "email" not in session:
        return redirect(url_for("login"))

    users = load_users()

    current_user = None

    for user in users:

        if user.get("email", "").strip().lower() == session.get("email", "").strip().lower():
            current_user = user
            break

    if current_user is None:
        session.clear()
        return redirect(url_for("login"))

    if request.method == "POST":

        old_password = request.form.get("old_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not bcrypt.check_password_hash(
            current_user["password"],
            old_password
        ):
            flash("Old Password is Incorrect.", "error")
            return redirect(url_for("change_password"))

        if new_password != confirm_password:
            flash(
                "New Password and Confirm Password do not match.",
                "error"
            )
            return redirect(url_for("change_password"))

        if bcrypt.check_password_hash(
            current_user["password"],
            new_password
        ):
            flash(
                "New Password cannot be the same as the current password.",
                "error"
            )
            return redirect(url_for("change_password"))

        current_user["password"] = bcrypt.generate_password_hash(
            new_password
        ).decode("utf-8")

        save_users(users)

        flash("Password Changed Successfully.", "success")

        return redirect(url_for("back_to_dashboard"))

    return render_template("change_password.html")


# =========================================================
# FORGOT PASSWORD
# =========================================================

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()

        user = find_user(email)

        if user is None:
            flash("No account found with this email.", "error")
            return redirect(url_for("forgot_password"))

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

            flash("OTP Sent Successfully.", "success")

        except Exception as e:

            print("EMAIL ERROR:", e)

            flash("Unable to Send OTP.", "error")

        return redirect(url_for("verify_otp"))

    return render_template("forgot_password.html")


# =========================================================
# VERIFY OTP
# =========================================================

@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "POST":

        entered_otp = request.form.get("otp", "").strip()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if "otp" not in session or "reset_email" not in session:
            flash("OTP Expired.", "error")
            return redirect(url_for("forgot_password"))

        if entered_otp != session.get("otp"):
            flash("Invalid OTP.", "error")
            return redirect(url_for("verify_otp"))

        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("verify_otp"))

        users = load_users()

        reset_email = session.get("reset_email")

        user_found = False

        for user in users:

            if user.get("email", "").strip().lower() == reset_email:

                user["password"] = bcrypt.generate_password_hash(
                    new_password
                ).decode("utf-8")

                user_found = True

                break

        if not user_found:
            flash("User account not found.", "error")
            return redirect(url_for("forgot_password"))

        save_users(users)

        session.pop("otp", None)
        session.pop("reset_email", None)

        flash("Password Reset Successful.", "success")

        return redirect(url_for("login"))

    return render_template("verify_otp.html")


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