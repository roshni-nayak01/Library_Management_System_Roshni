from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from datetime import datetime, timedelta
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

@app.route("/issue-books", methods=["GET", "POST"])
def issue_books():

    # =====================================================
    # LIBRARIAN LOGIN CHECK
    # =====================================================

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        flash("Only librarians can issue books.", "error")
        return redirect(url_for("back_to_dashboard"))

    # =====================================================
    # LOAD DATA
    # =====================================================

    users = load_users()
    books = load_books()
    borrow_records = load_borrow_records()

    # Only registered normal users can receive books
    members = [
        user for user in users
        if user.get("role") == "user"
    ]

    # Remove empty objects such as {}
    valid_books = [
        book for book in books
        if book.get("book_id")
    ]

    # =====================================================
    # ISSUE BOOK
    # =====================================================

    if request.method == "POST":

        user_email = request.form.get(
            "user_email",
            ""
        ).strip().lower()

        book_id = request.form.get(
            "book_id",
            ""
        ).strip()

        # -------------------------------------------------
        # BASIC VALIDATION
        # -------------------------------------------------

        if not user_email or not book_id:

            flash(
                "Please select both a member and a book.",
                "error"
            )

            return redirect(url_for("issue_books"))

        # -------------------------------------------------
        # FIND USER
        # -------------------------------------------------

        selected_user = None

        for user in members:

            if (
                user.get("email", "").strip().lower()
                == user_email
            ):

                selected_user = user
                break

        if selected_user is None:

            flash(
                "Selected member was not found.",
                "error"
            )

            return redirect(url_for("issue_books"))

        # -------------------------------------------------
        # FIND BOOK
        # -------------------------------------------------

        selected_book = None

        for book in valid_books:

            if str(book.get("book_id")) == str(book_id):

                selected_book = book
                break

        if selected_book is None:

            flash(
                "Selected book was not found.",
                "error"
            )

            return redirect(url_for("issue_books"))

        # -------------------------------------------------
        # CHECK AVAILABLE COPIES
        # -------------------------------------------------

        try:
            copies = int(selected_book.get("copies", 0))
        except (TypeError, ValueError):
            copies = 0

        if copies <= 0:

            flash(
                "This book is currently unavailable.",
                "error"
            )

            return redirect(url_for("issue_books"))

        # -------------------------------------------------
        # PREVENT DUPLICATE ACTIVE BORROWING
        # -------------------------------------------------

        already_borrowed = False

        for record in borrow_records:

            if not isinstance(record, dict):
                continue

            if (
                record.get("user_email", "").strip().lower()
                == user_email
                and str(record.get("book_id"))
                == str(book_id)
                and record.get("returned") is False
            ):

                already_borrowed = True
                break

        if already_borrowed:

            flash(
                "This member already has this book issued.",
                "error"
            )

            return redirect(url_for("issue_books"))

        # =================================================
        # CREATE BORROW RECORD
        # =================================================

        from datetime import datetime, timedelta

        issue_datetime = datetime.now()

        due_datetime = (
            issue_datetime
            + timedelta(days=BORROW_DAYS)
        )

        borrow_record = {

            "user_email": user_email,

            "book_id": str(
                selected_book.get("book_id")
            ),

            "book_name": selected_book.get(
                "book_name",
                ""
            ),

            "author": selected_book.get(
                "author",
                ""
            ),

            "category": selected_book.get(
                "category",
                ""
            ),

            "borrowed_date": issue_datetime.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            "due_date": due_datetime.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

            "returned": False,

            "returned_date": None
        }

        borrow_records.append(borrow_record)

        # -------------------------------------------------
        # DECREASE AVAILABLE COPIES
        # -------------------------------------------------

        selected_book["copies"] = copies - 1

        # -------------------------------------------------
        # SAVE BOTH FILES
        # -------------------------------------------------

        save_borrow_records(borrow_records)
        save_books(books)

        flash(
            f"Book '{selected_book.get('book_name')}' "
            f"issued successfully to {selected_user.get('name')}. "
            f"Due date: {due_datetime.strftime('%d-%m-%Y')}.",
            "success"
        )

        return redirect(url_for("issue_books"))

    # =====================================================
    # DISPLAY CURRENTLY ISSUED BOOKS
    # =====================================================

    active_records = []

    for record in borrow_records:

        if not isinstance(record, dict):
            continue

        if record.get("returned") is False:

            active_records.append(record)

    return render_template(
        "issue_books.html",
        members=members,
        books=valid_books,
        issued_books=active_records
    )


@app.route(
    "/librarian-return-books",
    methods=["GET", "POST"]
)
def librarian_return_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":

        flash(
            "Only librarians can return books.",
            "error"
        )

        return redirect(
            url_for("back_to_dashboard")
        )

    books = load_books()
    borrow_records = load_borrow_records()
    users = load_users()

    # =====================================================
    # RETURN BOOK
    # =====================================================

    if request.method == "POST":

        record_index = request.form.get(
            "record_index",
            ""
        ).strip()

        condition = request.form.get(
            "book_condition",
            "good"
        ).strip().lower()

        # -------------------------------------------------
        # VALIDATE RECORD INDEX
        # -------------------------------------------------

        if not record_index.isdigit():

            flash(
                "Invalid borrowing record.",
                "error"
            )

            return redirect(
                url_for("librarian_return_books")
            )

        index = int(record_index)

        if (
            index < 0
            or index >= len(borrow_records)
        ):

            flash(
                "Borrowing record not found.",
                "error"
            )

            return redirect(
                url_for("librarian_return_books")
            )

        record = borrow_records[index]

        if not isinstance(record, dict):

            flash(
                "Invalid borrowing record.",
                "error"
            )

            return redirect(
                url_for("librarian_return_books")
            )

        # -------------------------------------------------
        # ALREADY RETURNED?
        # -------------------------------------------------

        if record.get("returned") is True:

            flash(
                "This book has already been returned.",
                "error"
            )

            return redirect(
                url_for("librarian_return_books")
            )

        # -------------------------------------------------
        # VALIDATE CONDITION
        # -------------------------------------------------

        allowed_conditions = [
            "good",
            "damaged",
            "lost"
        ]

        if condition not in allowed_conditions:

            condition = "good"

        # -------------------------------------------------
        # RETURN DATE
        # -------------------------------------------------

        returned_datetime = datetime.now()

        returned_date = returned_datetime.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # -------------------------------------------------
        # CALCULATE LATE DAYS USING RETURN DATE
        # -------------------------------------------------

        temp_record = record.copy()

        temp_record["returned"] = True

        temp_record["returned_date"] = returned_date

        fine_data = calculate_fine(
            temp_record
        )

        # -------------------------------------------------
        # SAVE FINE INFORMATION IN RECORD
        # -------------------------------------------------

        record["returned"] = True

        record["returned_date"] = returned_date

        record["book_condition"] = condition

        record["days_late"] = (
            fine_data["days_late"]
        )

        record["late_fine"] = (
            fine_data["late_fine"]
        )

        record["damage_fine"] = (
            fine_data["damage_fine"]
        )

        record["lost_fine"] = (
            fine_data["lost_fine"]
        )

        record["total_fine"] = (
            fine_data["total_fine"]
        )

        record["fine_status"] = (
            "Pending"
            if fine_data["total_fine"] > 0
            else "No Fine"
        )

        # -------------------------------------------------
        # FIND BOOK
        # -------------------------------------------------

        book_id = str(
            record.get("book_id", "")
        ).strip()

        selected_book = None

        for book in books:

            if (
                str(
                    book.get("book_id", "")
                ).strip()
                == book_id
            ):

                selected_book = book
                break

        # -------------------------------------------------
        # UPDATE BOOK COPIES
        # -------------------------------------------------

        if selected_book is not None:

            try:

                current_copies = int(
                    selected_book.get(
                        "copies",
                        0
                    )
                )

            except (TypeError, ValueError):

                current_copies = 0

            # Lost book does NOT come back into inventory.
            if condition == "lost":

                selected_book["copies"] = current_copies

            else:

                selected_book["copies"] = (
                    current_copies + 1
                )

        # -------------------------------------------------
        # SAVE DATA
        # -------------------------------------------------

        save_books(books)
        save_borrow_records(
            borrow_records
        )

        # -------------------------------------------------
        # FIND BORROWER NAME
        # -------------------------------------------------

        borrower_email = record.get(
            "user_email",
            ""
        ).strip().lower()

        borrower_name = borrower_email

        for user in users:

            if (
                user.get(
                    "email",
                    ""
                ).strip().lower()
                == borrower_email
            ):

                borrower_name = user.get(
                    "name",
                    borrower_email
                )

                break

        # -------------------------------------------------
        # SUCCESS MESSAGE
        # -------------------------------------------------

        if fine_data["total_fine"] > 0:

            flash(
                f"{record.get('book_name', 'Book')} "
                f"returned by {borrower_name}. "
                f"Fine: ₹{fine_data['total_fine']}.",
                "success"
            )

        else:

            flash(
                f"{record.get('book_name', 'Book')} "
                f"returned successfully by "
                f"{borrower_name}. No fine.",
                "success"
            )

        return redirect(
            url_for("librarian_return_books")
        )

    # =====================================================
    # SHOW CURRENTLY BORROWED BOOKS
    # =====================================================

    active_records = []

    for index, record in enumerate(
        borrow_records
    ):

        if not isinstance(record, dict):
            continue

        if record.get("returned") is not False:
            continue

        record_copy = record.copy()

        record_copy["_index"] = index

        # -------------------------------------------------
        # FIND USER NAME
        # -------------------------------------------------

        user_email = record.get(
            "user_email",
            ""
        ).strip().lower()

        user_name = user_email

        for user in users:

            if (
                user.get(
                    "email",
                    ""
                ).strip().lower()
                == user_email
            ):

                user_name = user.get(
                    "name",
                    user_email
                )

                break

        record_copy["user_name"] = user_name

        # -------------------------------------------------
        # CURRENT FINE IF ALREADY LATE
        # -------------------------------------------------

        current_fine = calculate_fine(
            record
        )

        record_copy["current_days_late"] = (
            current_fine["days_late"]
        )

        record_copy["current_late_fine"] = (
            current_fine["late_fine"]
        )

        active_records.append(
            record_copy
        )

    return render_template(
        "librarian_return_books.html",
        borrowed_books=active_records
    )
    # =====================================================
    # RETURN BOOK
    # =====================================================

    if request.method == "POST":

        record_index = request.form.get(
            "record_index",
            ""
        ).strip()

        if not record_index.isdigit():

            flash(
                "Invalid borrowing record.",
                "error"
            )

            return redirect(
                url_for("librarian_return_books")
            )

        index = int(record_index)

        if index < 0 or index >= len(borrow_records):

            flash(
                "Borrowing record not found.",
                "error"
            )

            return redirect(
                url_for("librarian_return_books")
            )

        record = borrow_records[index]

        if not isinstance(record, dict):

            flash(
                "Invalid borrowing record.",
                "error"
            )

            return redirect(
                url_for("librarian_return_books")
            )

        # -------------------------------------------------
        # CHECK WHETHER ALREADY RETURNED
        # -------------------------------------------------

        if record.get("returned") is True:

            flash(
                "This book has already been returned.",
                "error"
            )

            return redirect(
                url_for("librarian_return_books")
            )

        book_id = str(
            record.get("book_id", "")
        ).strip()

        book_name = record.get(
            "book_name",
            "Book"
        )

        borrower_email = record.get(
            "user_email",
            ""
        ).strip().lower()

        # =================================================
        # MARK ORIGINAL BORROW RECORD AS RETURNED
        # =================================================

        record["returned"] = True

        record["returned_date"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # =================================================
        # FIND BOOK
        # =================================================

        selected_book = None

        for book in books:

            if (
                str(book.get("book_id", "")).strip()
                == book_id
            ):

                selected_book = book
                break

        if selected_book is None:

            save_borrow_records(borrow_records)

            flash(
                f"Borrow record returned, but book "
                f"'{book_id}' was not found in books.json.",
                "error"
            )

            return redirect(
                url_for("librarian_return_books")
            )

        # =================================================
        # INCREASE AVAILABLE COPY
        # =================================================

        try:
            current_copies = int(
                selected_book.get("copies", 0)
            )
        except (TypeError, ValueError):
            current_copies = 0

        selected_book["copies"] = current_copies + 1

        # =================================================
        # FIND FIRST WAITLISTED USER
        # =================================================

        waitlist_position = None

        for position, waiting_user in enumerate(waitlist):

            if not isinstance(waiting_user, dict):
                continue

            if (
                str(
                    waiting_user.get("book_id", "")
                ).strip()
                == book_id
            ):

                waitlist_position = position
                break

        # =================================================
        # AUTOMATIC WAITLIST PROCESSING
        # =================================================

        automatic_issue = False
        waiting_user_name = None
        waiting_user_email = None

        if waitlist_position is not None:

            waiting_user = waitlist.pop(
                waitlist_position
            )

            waiting_user_email = (
                waiting_user.get(
                    "user_email",
                    ""
                ).strip().lower()
            )

            waiting_user_name = waiting_user.get(
                "user_name",
                waiting_user_email
            )

            # -------------------------------------------------
            # VERIFY WAITLIST USER STILL EXISTS
            # -------------------------------------------------

            actual_user = None

            for user in users:

                if (
                    user.get("email", "").strip().lower()
                    == waiting_user_email
                ):

                    actual_user = user
                    break

            if actual_user is not None:

                waiting_user_name = actual_user.get(
                    "name",
                    waiting_user_name
                )

                # ---------------------------------------------
                # CHECK USER DOES NOT ALREADY HAVE THIS BOOK
                # ---------------------------------------------

                already_has_book = False

                for existing_record in borrow_records:

                    if not isinstance(
                        existing_record,
                        dict
                    ):
                        continue

                    if (
                        existing_record.get(
                            "user_email",
                            ""
                        ).strip().lower()
                        == waiting_user_email
                        and str(
                            existing_record.get(
                                "book_id",
                                ""
                            )
                        ).strip()
                        == book_id
                        and existing_record.get(
                            "returned"
                        ) is False
                    ):

                        already_has_book = True
                        break

                # ---------------------------------------------
                # AUTOMATICALLY ISSUE RETURNED COPY
                # ---------------------------------------------

                if not already_has_book:

                    from datetime import timedelta

                    issue_datetime = datetime.now()

                    due_datetime = (
                        issue_datetime
                        + timedelta(days=BORROW_DAYS)
                    )

                    new_borrow_record = {

                        "user_email":
                            waiting_user_email,

                        "book_id":
                            book_id,

                        "book_name":
                            selected_book.get(
                                "book_name",
                                book_name
                            ),

                        "author":
                            selected_book.get(
                                "author",
                                ""
                            ),

                        "category":
                            selected_book.get(
                                "category",
                                ""
                            ),

                        "borrowed_date":
                            issue_datetime.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),

                        "due_date":
                            due_datetime.strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),

                        "returned":
                            False,

                        "returned_date":
                            None
                    }

                    borrow_records.append(
                        new_borrow_record
                    )

                    # The returned copy is immediately
                    # assigned to the waiting user.
                    selected_book["copies"] -= 1

                    automatic_issue = True

        # =================================================
        # SAVE EVERYTHING
        # =================================================

        save_books(books)
        save_borrow_records(borrow_records)
        save_waitlist(waitlist)

        # =================================================
        # SUCCESS MESSAGE
        # =================================================

        if automatic_issue:

            flash(
                f"'{book_name}' returned successfully. "
                f"The book was automatically issued to "
                f"{waiting_user_name} from the waitlist.",
                "success"
            )

        else:

            flash(
                f"'{book_name}' returned successfully.",
                "success"
            )

        return redirect(
            url_for("librarian_return_books")
        )

    # =====================================================
    # DISPLAY CURRENTLY ISSUED BOOKS
    # =====================================================

    active_records = []

    for index, record in enumerate(
        borrow_records
    ):

        if not isinstance(record, dict):
            continue

        if record.get("returned") is not False:
            continue

        record_copy = record.copy()

        record_copy["_index"] = index

        # -------------------------------------------------
        # FIND ACTUAL USER NAME
        # -------------------------------------------------

        user_email = record.get(
            "user_email",
            ""
        ).strip().lower()

        user_name = user_email

        for user in users:

            if (
                user.get("email", "").strip().lower()
                == user_email
            ):

                user_name = user.get(
                    "name",
                    user_email
                )

                break

        record_copy["user_name"] = user_name

        active_records.append(
            record_copy
        )

    return render_template(
        "librarian_return_books.html",
        borrowed_books=active_records
    )
    # =====================================================
    # RETURN BOOK
    # =====================================================

    if request.method == "POST":

        record_index = request.form.get("record_index", "").strip()

        if not record_index.isdigit():
            flash("Invalid borrowing record.", "error")
            return redirect(url_for("librarian_return_books"))

        index = int(record_index)

        if index < 0 or index >= len(borrow_records):
            flash("Borrowing record not found.", "error")
            return redirect(url_for("librarian_return_books"))

        record = borrow_records[index]

        if not isinstance(record, dict):
            flash("Invalid borrowing record.", "error")
            return redirect(url_for("librarian_return_books"))

        # Already returned
        if record.get("returned") is True:
            flash("This book has already been returned.", "error")
            return redirect(url_for("librarian_return_books"))

        book_id = str(record.get("book_id", "")).strip()

        # =================================================
        # MARK BORROW RECORD AS RETURNED
        # =================================================

        record["returned"] = True
        record["returned_date"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # =================================================
        # INCREASE AVAILABLE COPIES
        # =================================================

        book_found = False

        for book in books:

            if str(book.get("book_id", "")).strip() == book_id:

                try:
                    current_copies = int(book.get("copies", 0))
                except (TypeError, ValueError):
                    current_copies = 0

                book["copies"] = current_copies + 1
                book_found = True
                break

        if not book_found:
            flash(
                "Book record was not found, but the borrowing record was updated.",
                "error"
            )

        # =================================================
        # SAVE DATA
        # =================================================

        save_books(books)
        save_borrow_records(borrow_records)

        borrower_name = record.get("user_email", "Unknown User")

        for user in users:
            if (
                user.get("email", "").strip().lower()
                == record.get("user_email", "").strip().lower()
            ):
                borrower_name = user.get("name", borrower_name)
                break

        flash(
            f"'{record.get('book_name', 'Book')}' returned successfully "
            f"by {borrower_name}.",
            "success"
        )

        return redirect(url_for("librarian_return_books"))

    # =====================================================
    # DISPLAY ACTIVE BORROWINGS
    # =====================================================

    active_records = []

    for index, record in enumerate(borrow_records):

        if not isinstance(record, dict):
            continue

        if record.get("returned") is False:

            record_copy = record.copy()
            record_copy["_index"] = index

            # Find actual user name
            user_name = record.get("user_email", "Unknown User")

            for user in users:

                if (
                    user.get("email", "").strip().lower()
                    == record.get("user_email", "").strip().lower()
                ):
                    user_name = user.get("name", user_name)
                    break

            record_copy["user_name"] = user_name

            active_records.append(record_copy)

    return render_template(
        "librarian_return_books.html",
        borrowed_books=active_records
    )

@app.route("/librarian-renew-books", methods=["GET", "POST"])
def librarian_renew_books():

    # =====================================================
    # LIBRARIAN LOGIN CHECK
    # =====================================================

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        flash("Only librarians can renew books.", "error")
        return redirect(url_for("back_to_dashboard"))

    borrow_records = load_borrow_records()

    # =====================================================
    # RENEW BOOK
    # =====================================================

    if request.method == "POST":

        record_index = request.form.get(
            "record_index",
            ""
        ).strip()

        if not record_index.isdigit():

            flash(
                "Invalid borrowing record.",
                "error"
            )

            return redirect(
                url_for("librarian_renew_books")
            )

        index = int(record_index)

        # -------------------------------------------------
        # CHECK INDEX
        # -------------------------------------------------

        if index < 0 or index >= len(borrow_records):

            flash(
                "Borrowing record not found.",
                "error"
            )

            return redirect(
                url_for("librarian_renew_books")
            )

        record = borrow_records[index]

        if not isinstance(record, dict):

            flash(
                "Invalid borrowing record.",
                "error"
            )

            return redirect(
                url_for("librarian_renew_books")
            )

        # -------------------------------------------------
        # CHECK RETURN STATUS
        # -------------------------------------------------

        if record.get("returned") is True:

            flash(
                "A returned book cannot be renewed.",
                "error"
            )

            return redirect(
                url_for("librarian_renew_books")
            )

        # =================================================
        # GET CURRENT DUE DATE
        # =================================================

        from datetime import datetime, timedelta

        due_date_text = record.get("due_date")

        try:

            if due_date_text:

                current_due_date = datetime.strptime(
                    due_date_text,
                    "%Y-%m-%d %H:%M:%S"
                )

            else:

                # Compatibility with old records that
                # don't have a due_date
                borrowed_date = datetime.strptime(
                    record.get("borrowed_date"),
                    "%Y-%m-%d %H:%M:%S"
                )

                current_due_date = (
                    borrowed_date
                    + timedelta(days=BORROW_DAYS)
                )

        except (ValueError, TypeError):

            flash(
                "This borrowing record has an invalid date.",
                "error"
            )

            return redirect(
                url_for("librarian_renew_books")
            )

        # =================================================
        # EXTEND DUE DATE
        # =================================================

        new_due_date = (
            current_due_date
            + timedelta(days=RENEWAL_DAYS)
        )

        record["due_date"] = new_due_date.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # =================================================
        # SAVE
        # =================================================

        save_borrow_records(borrow_records)

        flash(
            f"Book renewed successfully. "
            f"New due date: "
            f"{new_due_date.strftime('%d-%m-%Y')}.",
            "success"
        )

        return redirect(
            url_for("librarian_renew_books")
        )

    # =====================================================
    # SHOW ACTIVE BORROWINGS
    # =====================================================

    active_records = []

    for index, record in enumerate(borrow_records):

        if not isinstance(record, dict):
            continue

        if record.get("returned") is False:

            record_copy = record.copy()

            record_copy["_index"] = index

            # Add missing due date for old records
            if not record_copy.get("due_date"):

                from datetime import datetime, timedelta

                try:

                    borrowed_date = datetime.strptime(
                        record_copy.get("borrowed_date"),
                        "%Y-%m-%d %H:%M:%S"
                    )

                    due_date = (
                        borrowed_date
                        + timedelta(days=BORROW_DAYS)
                    )

                    record_copy["due_date"] = (
                        due_date.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                    )

                except (ValueError, TypeError):

                    record_copy["due_date"] = "Not available"

            active_records.append(record_copy)

    return render_template(
        "renew_books.html",
        borrowed_books=active_records
    )

@app.route("/waitlist-management", methods=["GET", "POST"])
def waitlist_management():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":
        flash("Only librarians can manage the waitlist.", "error")
        return redirect(url_for("back_to_dashboard"))

    waitlist = load_waitlist()
    users = load_users()
    books = load_books()

    # =====================================================
    # REMOVE FROM WAITLIST
    # =====================================================

    if request.method == "POST":

        waitlist_index = request.form.get(
            "waitlist_index",
            ""
        ).strip()

        if not waitlist_index.isdigit():

            flash(
                "Invalid waitlist record.",
                "error"
            )

            return redirect(
                url_for("waitlist_management")
            )

        index = int(waitlist_index)

        if index < 0 or index >= len(waitlist):

            flash(
                "Waitlist record not found.",
                "error"
            )

            return redirect(
                url_for("waitlist_management")
            )

        removed = waitlist.pop(index)

        save_waitlist(waitlist)

        flash(
            f"{removed.get('user_name', 'User')} "
            f"was removed from the waitlist.",
            "success"
        )

        return redirect(
            url_for("waitlist_management")
        )

    # =====================================================
    # BUILD REAL WAITLIST DATA
    # =====================================================

    display_waitlist = []

    for index, entry in enumerate(waitlist):

        if not isinstance(entry, dict):
            continue

        item = entry.copy()

        item["_index"] = index

        # Find actual user
        user_email = entry.get(
            "user_email",
            ""
        ).strip().lower()

        user_name = entry.get(
            "user_name",
            user_email
        )

        for user in users:

            if (
                user.get("email", "").strip().lower()
                == user_email
            ):

                user_name = user.get(
                    "name",
                    user_name
                )

                break

        item["user_name"] = user_name

        # Find actual book
        book_id = str(
            entry.get("book_id", "")
        ).strip()

        book_name = entry.get(
            "book_name",
            book_id
        )

        for book in books:

            if (
                str(book.get("book_id", "")).strip()
                == book_id
            ):

                book_name = book.get(
                    "book_name",
                    book_name
                )

                break

        item["book_name"] = book_name

        display_waitlist.append(item)

    return render_template(
        "waitlist_management.html",
        waitlist=display_waitlist
    )
@app.route(
    "/fine-management",
    methods=["GET", "POST"]
)
def fine_management():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "librarian":

        flash(
            "Only librarians can manage fines.",
            "error"
        )

        return redirect(
            url_for("back_to_dashboard")
        )

    borrow_records = load_borrow_records()
    users = load_users()

    # =====================================================
    # MARK FINE AS PAID
    # =====================================================

    if request.method == "POST":

        record_index = request.form.get(
            "record_index",
            ""
        ).strip()

        if not record_index.isdigit():

            flash(
                "Invalid fine record.",
                "error"
            )

            return redirect(
                url_for("fine_management")
            )

        index = int(record_index)

        if (
            index < 0
            or index >= len(borrow_records)
        ):

            flash(
                "Fine record not found.",
                "error"
            )

            return redirect(
                url_for("fine_management")
            )

        record = borrow_records[index]

        if record.get("returned") is not True:

            flash(
                "A fine cannot be marked paid before the book is returned.",
                "error"
            )

            return redirect(
                url_for("fine_management")
            )

        if float(
            record.get(
                "total_fine",
                0
            )
        ) <= 0:

            flash(
                "This record has no fine.",
                "error"
            )

            return redirect(
                url_for("fine_management")
            )

        record["fine_status"] = "Paid"

        record["fine_paid_date"] = (
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        save_borrow_records(
            borrow_records
        )

        flash(
            "Fine marked as paid successfully.",
            "success"
        )

        return redirect(
            url_for("fine_management")
        )

    # =====================================================
    # BUILD FINE LIST
    # =====================================================

    fines = []

    for index, record in enumerate(
        borrow_records
    ):

        if not isinstance(record, dict):
            continue

        # Calculate current fine dynamically.
        # This means an active overdue book gets
        # ₹50 added for every late day.

        fine_data = calculate_fine(
            record
        )

        total_fine = fine_data["total_fine"]

        # -------------------------------------------------
        # ONLY SHOW RECORDS WITH A FINE
        # -------------------------------------------------

        if total_fine <= 0:
            continue

        user_email = record.get(
            "user_email",
            ""
        ).strip().lower()

        member_name = user_email

        for user in users:

            if (
                user.get(
                    "email",
                    ""
                ).strip().lower()
                == user_email
            ):

                member_name = user.get(
                    "name",
                    user_email
                )

                break

        # -------------------------------------------------
        # CONDITION
        # -------------------------------------------------

        condition = record.get(
            "book_condition",
            "Good"
        )

        condition = str(
            condition
        ).capitalize()

        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        if record.get("fine_status"):

            status = record.get(
                "fine_status"
            )

        else:

            if record.get("returned") is True:

                status = "Pending"

            else:

                status = "Pending"

        fine_item = {

            "_index":
                index,

            "member_name":
                member_name,

            "user_email":
                user_email,

            "book_name":
                record.get(
                    "book_name",
                    "Unknown Book"
                ),

            "book_id":
                record.get(
                    "book_id",
                    ""
                ),

            "due_date":
                record.get(
                    "due_date",
                    "Not available"
                ),

            "returned_date":
                record.get(
                    "returned_date",
                    "Not returned"
                ),

            "days_late":
                fine_data["days_late"],

            "late_fine":
                fine_data["late_fine"],

            "damage_fine":
                fine_data["damage_fine"],

            "lost_fine":
                fine_data["lost_fine"],

            "total_fine":
                total_fine,

            "condition":
                condition,

            "status":
                status,

            "returned":
                record.get(
                    "returned",
                    False
                )
        }

        fines.append(
            fine_item
        )

    return render_template(
        "fine_management.html",
        fines=fines
    )



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

    # Load actual borrow records
    borrow_records = load_borrow_records()

    # Load actual users
    users = load_users()

    # Load actual books
    books = load_books()

    display_records = []

    for index, record in enumerate(borrow_records):

        # Ignore empty/invalid records
        if not isinstance(record, dict):
            continue

        if not record.get("user_email"):
            continue

        item = record.copy()

        item["_index"] = index

        # ============================================
        # FIND ACTUAL USER NAME
        # ============================================

        user_email = str(
            record.get("user_email", "")
        ).strip().lower()

        user_name = user_email

        for user in users:

            if (
                str(
                    user.get("email", "")
                ).strip().lower()
                == user_email
            ):

                user_name = user.get(
                    "name",
                    user_email
                )

                break

        item["user_name"] = user_name

        # ============================================
        # FIND ACTUAL BOOK NAME
        # ============================================

        book_id = str(
            record.get("book_id", "")
        ).strip()

        book_name = record.get(
            "book_name",
            book_id
        )

        for book in books:

            if (
                str(
                    book.get("book_id", "")
                ).strip()
                == book_id
            ):

                book_name = book.get(
                    "book_name",
                    book_name
                )

                break

        item["book_name"] = book_name

        # ============================================
        # STATUS
        # ============================================

        if record.get("returned") is True:

            item["status"] = "Returned"

        else:

            item["status"] = "Borrowed"

        # ============================================
        # DUE DATE FOR OLD RECORDS
        # ============================================

        if not item.get("due_date"):

            try:

                borrowed_date = datetime.strptime(
                    item.get("borrowed_date"),
                    "%Y-%m-%d %H:%M:%S"
                )

                due_date = (
                    borrowed_date
                    + timedelta(days=BORROW_DAYS)
                )

                item["due_date"] = (
                    due_date.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

            except (ValueError, TypeError):

                item["due_date"] = "Not available"

        display_records.append(item)

    return render_template(
        "borrow_records.html",
        borrow_records=display_records
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
@app.route("/borrow_books", methods=["GET", "POST"])
def borrow_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "user":
        return redirect(url_for("login"))

    # Load books
    if os.path.exists("books.json"):

        with open("books.json", "r") as file:
            books = json.load(file)

    else:
        books = []

    # Load borrow records
    if os.path.exists("borrow_records.json"):

        with open("borrow_records.json", "r") as file:
            borrow_records = json.load(file)

    else:
        borrow_records = []

    if request.method == "POST":

        book_id = request.form.get("book_id", "").strip()

        if not book_id:

            flash("Please enter a Book ID.", "error")

            return redirect(url_for("borrow_books"))

        # Check whether user already borrowed this book
        for record in borrow_records:

            if (
                record.get("user_email") == session.get("email")
                and record.get("book_id") == book_id
                and record.get("returned") == False
            ):

                flash(
                    "You have already borrowed this book.",
                    "error"
                )

                return redirect(url_for("borrow_books"))

        # Find book
        book_found = False

        for book in books:

            if str(book.get("book_id", "")).strip() == book_id:

                book_found = True

                copies = int(book.get("copies", 0))

                # Check availability
                if copies <= 0:

                    flash(
                        "This book is currently unavailable.",
                        "error"
                    )

                    return redirect(url_for("borrow_books"))

                # Deduct one copy
                book["copies"] = copies - 1

                # Create borrow record
                new_record = {

                    "user_email": session.get("email"),

                    "book_id": book.get("book_id"),

                    "book_name": book.get("book_name"),

                    "author": book.get("author"),

                    "category": book.get("category"),

                    "borrowed_date": datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),

                    "returned": False

                }

                borrow_records.append(new_record)

                # Save books
                with open("books.json", "w") as file:

                    json.dump(
                        books,
                        file,
                        indent=4
                    )

                # Save borrow records
                with open("borrow_records.json", "w") as file:

                    json.dump(
                        borrow_records,
                        file,
                        indent=4
                    )

                flash(
                    f"'{book.get('book_name')}' borrowed successfully!",
                    "success"
                )

                return redirect(url_for("borrow_books"))

        if not book_found:

            flash(
                "Book ID not found. Please enter a valid Book ID.",
                "error"
            )

    return render_template(
        "borrow_books.html",
        books=books
    )

# =========================================================
# USER - RETURN BOOKS
# =========================================================

@app.route("/return_books", methods=["GET", "POST"])
def return_books():

    if "email" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "user":
        return redirect(url_for("login"))

    # Load books
    if os.path.exists("books.json"):

        with open("books.json", "r") as file:
            books = json.load(file)

    else:
        books = []

    # Load borrow records
    if os.path.exists("borrow_records.json"):

        with open("borrow_records.json", "r") as file:
            borrow_records = json.load(file)

    else:
        borrow_records = []

    if request.method == "POST":

        book_id = request.form.get("book_id", "").strip()

        if not book_id:

            flash(
                "Please enter a Book ID.",
                "error"
            )

            return redirect(url_for("return_books"))

        record_found = False

        # Find user's active borrowed book
        for record in borrow_records:

            if (
                record.get("user_email") == session.get("email")
                and record.get("book_id") == book_id
                and record.get("returned") == False
            ):

                record_found = True

                # Mark as returned
                record["returned"] = True

                record["returned_date"] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                # Increase book copies
                for book in books:

                    if str(book.get("book_id", "")).strip() == book_id:

                        current_copies = int(
                            book.get("copies", 0)
                        )

                        book["copies"] = current_copies + 1

                        break

                break

        if not record_found:

            flash(
                "You have not borrowed this book.",
                "error"
            )

            return redirect(url_for("return_books"))

        # Save books
        with open("books.json", "w") as file:

            json.dump(
                books,
                file,
                indent=4
            )

        # Save records
        with open("borrow_records.json", "w") as file:

            json.dump(
                borrow_records,
                file,
                indent=4
            )

        flash(
            "Book returned successfully!",
            "success"
        )

        return redirect(url_for("return_books"))

    return render_template(
        "return_books.html"
    )
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

    books = load_books()
    waitlist = load_waitlist()
    users = load_users()

    current_email = session.get(
        "email",
        ""
    ).strip().lower()

    current_user = None

    for user in users:

        if (
            user.get("email", "").strip().lower()
            == current_email
        ):

            current_user = user
            break

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

        # =================================================
        # FIND BOOK
        # =================================================

        selected_book = None

        for book in books:

            if (
                str(book.get("book_id", "")).strip()
                == book_id
            ):

                selected_book = book
                break

        if selected_book is None:

            flash(
                "Book ID not found.",
                "error"
            )

            return redirect(
                url_for("reserve_books")
            )

        # =================================================
        # CHECK AVAILABLE COPIES
        # =================================================

        try:
            copies = int(
                selected_book.get("copies", 0)
            )
        except (TypeError, ValueError):
            copies = 0

        if copies > 0:

            flash(
                f"'{selected_book.get('book_name', 'Book')}' "
                f"is currently available. You can borrow it "
                f"from the Borrow Books page.",
                "error"
            )

            return redirect(
                url_for("reserve_books")
            )

        # =================================================
        # CHECK WHETHER ALREADY BORROWED
        # =================================================

        borrow_records = load_borrow_records()

        for record in borrow_records:

            if not isinstance(record, dict):
                continue

            if (
                record.get(
                    "user_email",
                    ""
                ).strip().lower()
                == current_email
                and str(
                    record.get(
                        "book_id",
                        ""
                    )
                ).strip()
                == book_id
                and record.get(
                    "returned"
                ) is False
            ):

                flash(
                    "You already have this book.",
                    "error"
                )

                return redirect(
                    url_for("reserve_books")
                )

        # =================================================
        # CHECK DUPLICATE WAITLIST ENTRY
        # =================================================

        for waiting_user in waitlist:

            if not isinstance(
                waiting_user,
                dict
            ):
                continue

            if (
                waiting_user.get(
                    "user_email",
                    ""
                ).strip().lower()
                == current_email
                and str(
                    waiting_user.get(
                        "book_id",
                        ""
                    )
                ).strip()
                == book_id
            ):

                flash(
                    "You are already on the waitlist for "
                    "this book.",
                    "error"
                )

                return redirect(
                    url_for("reserve_books")
                )

        # =================================================
        # ADD USER TO WAITLIST
        # =================================================

        user_name = session.get(
            "name",
            current_email
        )

        if current_user is not None:

            user_name = current_user.get(
                "name",
                user_name
            )

        waitlist_entry = {

            "user_email":
                current_email,

            "user_name":
                user_name,

            "book_id":
                str(
                    selected_book.get(
                        "book_id"
                    )
                ),

            "book_name":
                selected_book.get(
                    "book_name",
                    ""
                ),

            "requested_date":
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
        }

        waitlist.append(
            waitlist_entry
        )

        save_waitlist(
            waitlist
        )

        flash(
            f"You have been added to the waitlist "
            f"for '{selected_book.get('book_name', 'Book')}'.",
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


USERS_FILE = "users.json"
BOOKS_FILE = "books.json"
BORROW_RECORDS_FILE = "borrow_records.json"
WAITLIST_FILE = "waitlist.json"

BORROW_DAYS = 14
RENEWAL_DAYS = 7

LATE_FINE_PER_DAY = 50
DAMAGE_FINE = 100
LOST_FINE = 1000




def load_books():
    try:
        with open(BOOKS_FILE, "r") as f:
            data = json.load(f)

            if isinstance(data, list):
                return data

            return []

    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_books(books):
    with open(BOOKS_FILE, "w") as f:
        json.dump(books, f, indent=4)


def load_borrow_records():
    try:
        with open(BORROW_RECORDS_FILE, "r") as f:
            data = json.load(f)

            if isinstance(data, list):
                return data

            return []

    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_borrow_records(records):
    with open(BORROW_RECORDS_FILE, "w") as f:
        json.dump(records, f, indent=4)
def load_waitlist():
    try:
        with open(WAITLIST_FILE, "r") as f:
            data = json.load(f)

            if isinstance(data, list):
                return data

            return []

    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_waitlist(waitlist):
    with open(WAITLIST_FILE, "w") as f:
        json.dump(waitlist, f, indent=4)


def calculate_late_days(record, return_datetime=None):
    """
    Calculate the number of days a book is late.

    For returned books:
        due_date -> returned_date

    For active overdue books:
        due_date -> current time
    """

    try:

        due_date_text = record.get("due_date")

        if not due_date_text:

            borrowed_date = datetime.strptime(
                record.get("borrowed_date"),
                "%Y-%m-%d %H:%M:%S"
            )

            due_date = (
                borrowed_date
                + timedelta(days=BORROW_DAYS)
            )

        else:

            due_date = datetime.strptime(
                due_date_text,
                "%Y-%m-%d %H:%M:%S"
            )

        if return_datetime is None:

            if record.get("returned") is True:

                returned_date_text = record.get(
                    "returned_date"
                )

                if returned_date_text:

                    return_datetime = datetime.strptime(
                        returned_date_text,
                        "%Y-%m-%d %H:%M:%S"
                    )

                else:
                    return_datetime = datetime.now()

            else:

                return_datetime = datetime.now()

        difference = return_datetime - due_date

        days_late = difference.days

        if difference.total_seconds() > 0 and days_late == 0:
            days_late = 1

        return max(days_late, 0)

    except (ValueError, TypeError, AttributeError):

        return 0


def calculate_fine(record):

    days_late = calculate_late_days(record)

    late_fine = (
        days_late * LATE_FINE_PER_DAY
    )

    damage_fine = 0
    lost_fine = 0

    condition = str(
        record.get(
            "book_condition",
            "good"
        )
    ).lower().strip()

    if condition == "damaged":
        damage_fine = DAMAGE_FINE

    elif condition == "lost":
        lost_fine = LOST_FINE

    total_fine = (
        late_fine
        + damage_fine
        + lost_fine
    )

    return {
        "days_late": days_late,
        "late_fine": late_fine,
        "damage_fine": damage_fine,
        "lost_fine": lost_fine,
        "total_fine": total_fine
    }
        

# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":
    app.run(debug=True)
