from flask import Flask, render_template, request, redirect, session, flash
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
import json
import os
import random

app = Flask(__name__)

app.secret_key = "library_secret_key"

bcrypt = Bcrypt(app)

# ==========================
# Email Configuration
# ==========================

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True

# Replace these with your Gmail
app.config["MAIL_USERNAME"] = "nnm24is189@nmamit.in"

app.config["MAIL_PASSWORD"] = "pcdwrbnleizfzfxn"

mail = Mail(app)

USERS_FILE = "users.json"

# Create users.json automatically
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump([], f)


# ==========================
# Helper Functions
# ==========================

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def find_user(email):
    users = load_users()

    email = email.strip().lower()

    for user in users:
        if user["email"].strip().lower() == email:
            return user

    return None

def generate_otp():
    return str(random.randint(100000, 999999))



# ==========================
# Home
# ==========================


@app.route("/dashboard-selection")
def dashboard_selection():

    return render_template("dashboard_selection.html")



@app.route("/")
def home():

    return render_template("home.html")



@app.route("/search_books")
def search_books():

    return render_template("search_books.html")



@app.route("/view_books")
def view_books():

    return render_template("view_books.html")


# ==========================
# Select Role
# ==========================

@app.route("/select-role/<role>")
def select_role(role):

    session["selected_role"] = role

    return redirect("/login")
# ==========================
# Librarian Routes
# ==========================


@app.route("/issue-books")
def issue_books():

    if "email" not in session:
        return redirect("/login")

    if session.get("role") != "librarian":
        return redirect("/login")

    return render_template("issue_books.html")



@app.route("/librarian-return-books")
def librarian_return_books():

    if "email" not in session:
        return redirect("/login")

    if session.get("role") != "librarian":
        return redirect("/login")

    return render_template("librarian_return_books.html")



@app.route("/member-management")
def member_management():

    if "email" not in session:
        return redirect("/login")

    if session.get("role") != "librarian":
        return redirect("/login")

    return render_template("member_management.html")



@app.route("/book-management")
def book_management():

    if "email" not in session:
        return redirect("/login")

    if session.get("role") != "librarian":
        return redirect("/login")

    return render_template("book_management.html")



@app.route("/librarian-renew-books")
def librarian_renew_books():

    if "email" not in session:
        return redirect("/login")

    if session.get("role") != "librarian":
        return redirect("/login")

    return render_template("renew_books.html")



@app.route("/waitlist-management")
def waitlist_management():

    if "email" not in session:
        return redirect("/login")

    if session.get("role") != "librarian":
        return redirect("/login")

    return render_template("waitlist_management.html")



@app.route("/fine-management")
def fine_management():

    if "email" not in session:
        return redirect("/login")

    if session.get("role") != "librarian":
        return redirect("/login")

    return render_template("fine_management.html")



@app.route("/book-availability")
def book_availability():

    if "email" not in session:
        return redirect("/login")

    if session.get("role") != "librarian":
        return redirect("/login")

    return render_template("book_availability.html")



@app.route("/borrow-records")
def borrow_records():

    if "email" not in session:
        return redirect("/login")

    if session.get("role") != "librarian":
        return redirect("/login")

    return render_template("borrow_records.html")



@app.route("/reports")
def reports():

    if "email" not in session:
        return redirect("/login")

    if session.get("role") != "librarian":
        return redirect("/login")

    return render_template("reports.html")



@app.route("/categories")
def categories():

    if "email" not in session:
        return redirect("/login")

    if session.get("role") != "librarian":
        return redirect("/login")

    return render_template("categories.html")


# ==========================
# Register
# ==========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        role = request.form.get("role", "user")

        users = load_users()

        # Check duplicate email
        for user in users:

            if user["email"].strip().lower() == email:

                flash("Email already exists.")

                return redirect("/register")

        # Hash password
        hashed = bcrypt.generate_password_hash(password).decode("utf-8")

        users.append({
            "name": name,
            "email": email,
            "password": hashed,
            "role": role
        })

        save_users(users)

        # Keep selected role for login
        session["selected_role"] = role

        flash("Registration Successful!")

        return redirect("/login")

    return render_template("register.html")
# ==========================
# Login
# ==========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        selected_role = session.get("selected_role")

        print("Entered Email:", email)
        print("Entered Password:", password)
        print("Selected Role:", selected_role)

        user = find_user(email)

        print("User Found:", user)

        if user:

            print("Stored Password:", user["password"])
            print("Stored Role:", user["role"])

            result = bcrypt.check_password_hash(
                user["password"],
                password
            )

            print("Password Match:", result)

            if result:

                # Check selected role
                if selected_role is None or user["role"] == selected_role:

                    session["email"] = user["email"]
                    session["name"] = user["name"]
                    session["role"] = user["role"]

                    # Redirect according to role

                    if user["role"] == "admin":

                        return redirect("/admin-dashboard")

                    elif user["role"] == "librarian":

                        return redirect("/librarian-dashboard")

                    else:

                        return redirect("/dashboard")

                else:

                    flash("Selected role does not match your account.")

                    return redirect("/login")

        flash("Invalid Email or Password")

    return render_template("login.html")
# ==========================
# User Dashboard
# ==========================

@app.route("/dashboard")
def dashboard():

    if "email" not in session:

        return redirect("/login")


    if session.get("role") != "user":

        return redirect("/login")


    return render_template(
        "user_dashboard.html",
        name=session["name"]
    )



# ==========================
# Librarian Dashboard
# ==========================

@app.route("/librarian-dashboard")
def librarian_dashboard():

    if "email" not in session:

        return redirect("/login")


    if session.get("role") != "librarian":

        return redirect("/login")


    return render_template(
        "librarian_dashboard.html",
        name=session["name"]
    )



# ==========================
# Admin Dashboard
# ==========================

@app.route("/admin-dashboard")
def admin_dashboard():

    if "email" not in session:

        return redirect("/login")


    if session.get("role") != "admin":

        return redirect("/login")


    return render_template(
        "admin_dashboard.html",
        name=session["name"]
    )



# ==========================
# Logout
# ==========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

# ==========================
# Edit Profile
# ==========================

@app.route("/profile", methods=["GET", "POST"])
def profile():

    if "email" not in session:
        return redirect("/login")

    users = load_users()

    current_user = None

    for user in users:
        if user["email"] == session["email"]:
            current_user = user
            break

    if request.method == "POST":

        current_user["name"] = request.form["name"]

        save_users(users)

        session["name"] = current_user["name"]

        flash("Profile Updated Successfully")

        return redirect("/dashboard")

    return render_template("profile.html", user=current_user)


# ==========================
# Change Password
# ==========================

@app.route("/change-password", methods=["GET", "POST"])
def change_password():

    if "email" not in session:
        return redirect("/login")

    users = load_users()

    current_user = None

    for user in users:
        if user["email"] == session["email"]:
            current_user = user
            break

    if request.method == "POST":

        old_password = request.form["old_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        # Check old password
        if not bcrypt.check_password_hash(current_user["password"], old_password):

            flash("Old Password is Incorrect")

            return redirect("/change-password")

        # Check if new password and confirm password match
        if new_password != confirm_password:

            flash("New Password and Confirm Password do not match")

            return redirect("/change-password")

        # Optional: Prevent using the same password again
        if bcrypt.check_password_hash(current_user["password"], new_password):

            flash("New Password cannot be the same as the current password")

            return redirect("/change-password")

        # Update password
        current_user["password"] = bcrypt.generate_password_hash(
            new_password
        ).decode("utf-8")

        save_users(users)

        flash("Password Changed Successfully")

        return redirect("/dashboard")

    return render_template("change_password.html")


# ==========================
# Forgot Password
# Send OTP
# ==========================

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]

        otp = str(random.randint(100000, 999999))

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

            flash("OTP Sent Successfully")

        except Exception as e:

            print(e)

            flash("Unable to Send OTP")

        return redirect("/verify-otp")

    return render_template("forgot_password.html")
# ==========================
# Verify OTP
# ==========================
@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():

    if request.method == "POST":

        entered_otp = request.form["otp"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        # Check if OTP exists
        if "otp" not in session:

            flash("OTP Expired")

            return redirect("/forgot-password")

        # Check OTP
        if entered_otp != session["otp"]:

            flash("Invalid OTP")

            return redirect("/verify-otp")

        # Check if passwords match
        if new_password != confirm_password:

            flash("Passwords do not match")

            return redirect("/verify-otp")

        users = load_users()

        for user in users:

            if user["email"] == session["reset_email"]:

                user["password"] = bcrypt.generate_password_hash(
                    new_password
                ).decode("utf-8")

                break

        save_users(users)

        # Clear OTP session
        session.pop("otp", None)
        session.pop("reset_email", None)

        flash("Password Reset Successful")

        return redirect("/login")

    return render_template("verify_otp.html")


# ==========================
# Run Application
# ==========================
print("\n========== FLASK ROUTES ==========")

for rule in app.url_map.iter_rules():
    print(rule)

print("==================================\n")
if __name__ == "__main__":

    app.run(debug=True)
