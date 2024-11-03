from flask import Flask, render_template, request, redirect, url_for, current_app, session
from flask_login import LoginManager, UserMixin, logout_user, login_required, login_user, current_user
import sqlite3
import secrets
from forms import SignupForm, LoginForm, WebsiteForm 

# Initialize Flask app
app = Flask(__name__)

# Generate a secret key for session security (replace with a more secure method in production)
secret_key = secrets.token_hex()
app.secret_key = secret_key

# Initialize Flask-Login for user authentication
login_manager = LoginManager()
login_manager.init_app(app)

# Set login view for unauthorized access attempts
login_manager.login_view = 'login' 


# User class for authentication (represents a user in the database)
class User(UserMixin):
  def __init__(self, id, username, password):
    self.id = id
    self.username = username
    self.password = password

# Website class for storing website information (represents a website in the database)
class Website:
  def __init__(self, id, user_id, name, url):
    self.id = id
    self.user_id = user_id
    self.url = url
    self.name = name

# Function to retrieve user by ID from the database
def get_user_by_id(user_id):
  conn = sqlite3.connect('database.db')
  cursor = conn.cursor()
  cursor.execute('SELECT * FROM users WHERE id = {}'.format(int(user_id)))
  user_data = cursor.fetchone()
  conn.close()
  if user_data:
    return User(user_data[0], user_data[1], user_data[2])
  else:
    return None

# Load user for login (called by Flask-Login)
@login_manager.user_loader
def load_user(user_id):
  return get_user_by_id(user_id)

# Route for the main page
@app.route('/')
def index():
  return render_template('index.html')

# Route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
  form = SignupForm()
  if form.validate_on_submit():
    username = form.username.data
    password = form.password.data
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Check if username already exists
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    existing_user = c.fetchone()
    
    if existing_user:
      # Handle username already exists case
      form.username.errors.append('Username already taken.')
      conn.close()
    else:
      # Insert new user if username doesn't exist
      c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
      conn.commit()
      conn.close()
      return redirect(url_for('index'))
  
  return render_template('register.html', form=form)


# Route for user login
@app.route('/login', methods=['GET', 'POST'])
def login():
  form = LoginForm()
  error = None
  if form.validate_on_submit():
    username = form.username.data
    password = form.password.data
    conn = sqlite3.connect('database.db', timeout=60)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    data = c.fetchone()
    if data:
      user = User(data[0], data[1], data[2])
      login_user(user)
      session["user_id"] = data[0]
      return redirect(url_for('dashboard'))
    else:
      error = 'Invalid username or password'
  return render_template('login.html', form=form, error=error)

# Route for user logout
@app.route('/logout')
@login_required
def logout():
  session.pop("user_id", None)
  logout_user()
  return redirect(url_for('index'))


# Route for user dashboard
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
  form = WebsiteForm()
  if form.validate_on_submit():
    website_name = form.website_name.data
    website_url = form.website_url.data
    user_id = session["user_id"]
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('INSERT INTO websites (user_id, name, url) VALUES (?, ?, ?)', (user_id, website_name, website_url))
    conn.commit()
    c.close()
    conn.close()
    return redirect(url_for('dashboard'))

  # Retrieve user's websites from the database
  conn = sqlite3.connect('database.db')
  c = conn.cursor()
  c.execute('SELECT id, name, url FROM websites WHERE user_id = ?', (current_user.id,))
  websites = c.fetchall()  # Fetch all website records
  c.close()
  conn.close()

  # Convert website data into a list of dictionaries for easier template access
  websites = [{'id': row[0], 'name': row[1], 'url': row[2]} for row in websites]

  return render_template('dashboard.html', form=form, websites=websites)

# Route for deleting a website
@app.route('/dashboard/<int:website_id>/delete', methods=['POST'])
@login_required
def delete(website_id):
  conn = sqlite3.connect('database.db', timeout=60)
  c = conn.cursor()
  c.execute('DELETE FROM websites WHERE id = ?', (website_id,))
  conn.commit()
  c.close()
  conn.close()
  return redirect(url_for("dashboard"))

# Function to create database tables if they don't exist
def create_tables():
  with app.app_context():
    conn = sqlite3.connect('database.db', timeout=60)
    c = conn.cursor()

    # Check if the users table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not c.fetchone():
      with current_app.open_resource("./schema.sql") as f:
        c.executescript(f.read().decode("utf8"))
      conn.commit()
      print("Tables created successfully.")
    else:
      print("Tables already exist.")
    
    conn.close()

# Flag to ensure database initialization is done only once
tables_initialized = False

# Initialize database before each request
@app.before_request
def initialize_database():
  global tables_initialized
  if not tables_initialized:
    print("Initializing database...")
    create_tables()
    tables_initialized = True

if __name__ == '__main__':
  app.run(debug=True)