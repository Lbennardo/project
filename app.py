import os
from cs50 import SQL
from flask import Flask, render_template, session, redirect, url_for, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_default_secret')

db = SQL("sqlite:///users.db")


def is_logged_in():
    return session.get('user_id') is not None


@app.route("/")
def index():
    if is_logged_in():
        # If user is logged in, redirect to the home page
        return render_template("index.html")
    else:
        # If user is not logged in, redirect to the login page
        return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    # If user is already logged in, redirect to the home page
    if is_logged_in():
        return redirect("/")
    
    # Forget any user_id
    session.clear()

    if request.method == "POST":
        # Grab username and password from the form
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Check if username and password are provided
        if not username or not password:
            return render_template("login.html", error="Username and password are required.")
        
        # Query the database for the user
        current_user = db.execute("SELECT * FROM users WHERE username = ?", username)

        # If no user found, return an error
        if not current_user:
            return render_template("login.html", error="Invalid username or password.")

        # Ensure username exists and password is correct
        if len(current_user) != 1 or not check_password_hash(
            current_user[0]["hash"], password
        ):
            return render_template("login.html", error="Invalid username or password.")
        
        # Remember which user has logged in
        session["user_id"] = current_user[0]["id"]
        
        # Redirect to the index page after successful login
        return redirect("/")
    
    # If GET request, render the login page
    return render_template("login.html")


@app.route("/logout")
def logout():
    # Forget any user_id
    session.clear()
    
    # Redirect to the index page after logout
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    # If user is already logged in, redirect to the home page
    if is_logged_in():
        return redirect("/")
    
    if request.method == "POST":
        # Grab username and password from the form
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # Check if passwords match
        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match.")
        
        # Check if username and password are provided
        if not username or not password or not confirm_password:
            return render_template("register.html", error="Username and password are required.")
        
        # Check if the username already exists
        existing_user = db.execute("SELECT * FROM users WHERE username = ?", username)
        if existing_user:
            return render_template("register.html", error="Username already taken.")
        
        # Hash the password
        password_hash = generate_password_hash(password)

        # Insert the new user into the database
        print("Inserting user into DB")
        try:
            db.execute("INSERT INTO users (username, hash) VALUES (?, ?);", 
                        username, password_hash)
        except ValueError:
            return render_template("register.html", error="Error creating user. Please try again.")
        
        # Start cookies
        id = db.execute("SELECT id FROM users WHERE username = ? AND hash = ?;",
                        username, password_hash)
        session["user_id"] = id[0]["id"]

        # Redirect to the home page after successful registration
        return redirect("/")
    
    # If GET request, render the registration page
    return render_template("register.html")


@app.route('/get_image_url')
def get_image_url():
    page = request.args.get('page', type=int)

    if page is None:
        return jsonify({'image_url': None})

    # List valid image filenames (e.g. 0.jpg, 1.jpg, ...)
    image_folder = os.path.join(app.static_folder, 'images')
    valid_filenames = {
        os.path.splitext(f)[0]  # remove file extension
        for f in os.listdir(image_folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')) and os.path.splitext(f)[0].isdigit()
    }

    if str(page) in valid_filenames:
        image_url = url_for('static', filename=f'images/{page}.jpg')
        return jsonify({'image_url': image_url})
    else:
        return jsonify({'image_url': None})


@app.route('/get_image_count')
def get_image_count():
    image_folder = os.path.join(app.static_folder, 'images')
    valid_images = [
        f for f in os.listdir(image_folder)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')) and os.path.splitext(f)[0].isdigit()
    ]
    return jsonify({'count': len(valid_images)})


@app.route('/save_note', methods=['POST'])
def save_note():
    if not is_logged_in():
        return jsonify({'error': 'Not logged in'}), 403

    data = request.get_json()
    page = data.get('page')
    note = data.get('note')

    if page is None or not note:
        return jsonify({'error': 'Missing data'}), 400

    user_id = session['user_id']
    db.execute("INSERT INTO notes (user_id, page, note) VALUES (?, ?, ?)", user_id, page, note)

    return jsonify({'success': True})


@app.route('/get_notes')
def get_notes():
    if not is_logged_in():
        return jsonify({'notes': []})

    page = request.args.get('page', type=int)
    user_id = session['user_id']
    rows = db.execute("SELECT id, note FROM notes WHERE user_id = ? AND page = ? ORDER BY id ASC", user_id, page)

    notes = [{'id': row['id'], 'content': row['note']} for row in rows]

    return jsonify({'notes': notes})


@app.route('/delete_note/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    if not is_logged_in():
        return jsonify({'error': 'Not logged in'}), 403

    user_id = session['user_id']
    # Only delete the note if it belongs to the current user
    db.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", note_id, user_id)

    return jsonify({'success': True})

    
