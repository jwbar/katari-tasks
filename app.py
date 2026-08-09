import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from bson.objectid import ObjectId

from config import Config
from models import db, User, Task

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user_data = User.get_by_username(username)
        if user_data and check_password_hash(user_data['password'], password):
            if not user_data.get('active', True):
                flash('Account is disabled.', 'error')
                return redirect(url_for('login'))
            user = User(user_data)
            login_user(user)
            flash(f'Welcome, {username}!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current = request.form.get('current_password')
        new_pass = request.form.get('new_password')
        confirm = request.form.get('confirm_password')
        user_data = User.get_by_username(current_user.username)
        if not check_password_hash(user_data['password'], current):
            flash('Current password is incorrect.', 'error')
            return redirect(url_for('change_password'))
        if new_pass != confirm:
            flash('New passwords do not match.', 'error')
            return redirect(url_for('change_password'))
        if len(new_pass) < 4:
            flash('Password must be at least 4 characters.', 'error')
            return redirect(url_for('change_password'))
        db.users.update_one(
            {'_id': ObjectId(current_user.id)},
            {'$set': {'password': generate_password_hash(new_pass)}}
        )
        flash('Password changed successfully! Please log in again.', 'success')
        logout_user()
        return redirect(url_for('login'))
    return render_template('change_password.html')

# ==================== ADMIN ROUTES ====================

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('user_dashboard'))
    
    selected_day = request.args.get('day', None)
    tasks = Task.get_all_tasks(include_archived=False)
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    tasks_by_day = {day: [] for day in weekdays}
    
    for task in tasks:
        day = task.get('weekday', 'Unassigned')
        if day in tasks_by_day:
            assignee = db.users.find_one({'_id': ObjectId(task['assigned_to'])})
            task['assignee_name'] = assignee['username'] if assignee else 'Unknown'
            tasks_by_day[day].append(task)
    
    for day in weekdays:
        tasks_by_day[day].sort(key=lambda t: (str(t.get('due_date') or '9999-99-99'), t.get('title', '').lower()))
    
    return render_template('admin_dashboard.html', tasks_by_day=tasks_by_day, weekdays=weekdays, selected_day=selected_day)

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('user_dashboard'))
    users = list(db.users.find({'role': 'user'}))
    return render_template('admin_users.html', users=users)

@app.route('/admin/archive')
@login_required
def admin_archive():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('user_dashboard'))
    archived_tasks = Task.get_archived_tasks()
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    tasks_by_day = {day: [] for day in weekdays}
    for task in archived_tasks:
        day = task.get('weekday', 'Unassigned')
        if day in tasks_by_day:
            assignee = db.users.find_one({'_id': ObjectId(task['assigned_to'])})
            task['assignee_name'] = assignee['username'] if assignee else 'Unknown'
            approver = db.users.find_one({'_id': ObjectId(task.get('approved_by', ''))})
            task['approver_name'] = approver['username'] if approver else 'Unknown'
            tasks_by_day[day].append(task)
    for day in weekdays:
        tasks_by_day[day].sort(key=lambda t: (t.get('due_date') or '9999-99-99', t.get('title', '').lower()))
    return render_template('admin_archive.html', tasks_by_day=tasks_by_day, weekdays=weekdays)

@app.route('/admin/task/<task_id>/approve', methods=['POST'])
@login_required
def admin_approve_task(task_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('user_dashboard'))
    task = Task.get_task(task_id)
    if not task:
        flash('Task not found.', 'error')
        return redirect(url_for('admin_dashboard'))
    if task['status'] != 'completed':
        flash('Task must be completed before approval.', 'error')
        return redirect(url_for('admin_dashboard'))
    Task.approve_task(task_id, current_user.id)
    flash('Task approved and archived.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/task/<task_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_task(task_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('user_dashboard'))
    
    task = Task.get_task(task_id)
    if not task:
        flash('Task not found.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    users = list(db.users.find({'role': 'user'}))
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        assigned_to = request.form.get('assigned_to')
        weekday = request.form.get('weekday')
        due_date = request.form.get('due_date') or None
        
        if not all([title, assigned_to, weekday]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('admin_edit_task', task_id=task_id))
        
        updates = {
            'title': title,
            'description': description,
            'assigned_to': assigned_to,
            'weekday': weekday,
            'due_date': due_date
        }
        Task.update_task(task_id, updates)
        flash('Task updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin_edit_task.html', task=task, users=users, weekdays=weekdays)

@app.route('/admin/assign', methods=['GET', 'POST'])
@login_required
def admin_assign():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('user_dashboard'))
    users = list(db.users.find({'role': 'user'}))
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        assigned_to = request.form.get('assigned_to')
        weekday = request.form.get('weekday')
        due_date = request.form.get('due_date') or None
        if not all([title, assigned_to, weekday]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('admin_assign'))
        Task.create_task(title=title, description=description, assigned_to=assigned_to,
                        assigned_by=current_user.id, weekday=weekday, due_date=due_date)
        flash('Task assigned successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_assign.html', users=users, weekdays=weekdays)

@app.route('/admin/task/<task_id>/delete', methods=['POST'])
@login_required
def admin_delete_task(task_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('user_dashboard'))
    task = Task.get_task(task_id)
    if task and task.get('photo_path'):
        photo_path = os.path.join(app.root_path, task['photo_path'])
        if os.path.exists(photo_path):
            os.remove(photo_path)
    Task.delete_task(task_id)
    flash('Task deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/add', methods=['POST'])
@login_required
def admin_add_user():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('user_dashboard'))
    username = request.form.get('username')
    password = request.form.get('password')
    email = request.form.get('email')
    role = request.form.get('role', 'user')
    if not all([username, password]):
        flash('Username and password are required.', 'error')
        return redirect(url_for('admin_users'))
    user_id = User.create_user(username, password, email, role)
    if user_id:
        flash(f'User {username} created successfully!', 'success')
    else:
        flash('Username already exists.', 'error')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<user_id>/reset-password', methods=['POST'])
@login_required
def admin_reset_password(user_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('user_dashboard'))
    new_password = request.form.get('new_password')
    if not new_password or len(new_password) < 4:
        flash('Password must be at least 4 characters.', 'error')
        return redirect(url_for('admin_users'))
    db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'password': generate_password_hash(new_password)}}
    )
    flash('Password reset successfully.', 'success')
    return redirect(url_for('admin_users'))

# ==================== USER ROUTES ====================

@app.route('/dashboard')
@login_required
def user_dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    selected_day = request.args.get('day', None)
    active_tasks = Task.get_user_tasks(current_user.id, selected_day, include_archived=False)
    archived_tasks = Task.get_user_archived_tasks(current_user.id)
    active_tasks.sort(key=lambda t: (t.get('due_date') or '9999-99-99', t.get('title', '').lower()))
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pending = sum(1 for t in active_tasks if t['status'] == 'pending')
    completed = sum(1 for t in active_tasks if t['status'] == 'completed')
    total_completed = len(archived_tasks) + completed
    return render_template('user_dashboard.html', tasks=active_tasks, archived_tasks=archived_tasks,
                         weekdays=weekdays, selected_day=selected_day,
                         pending_count=pending, completed_count=total_completed)

@app.route('/task/<task_id>', methods=['GET', 'POST'])
@login_required
def task_detail(task_id):
    task = Task.get_task(task_id)
    if not task:
        flash('Task not found.', 'error')
        return redirect(url_for('user_dashboard'))
    if current_user.role != 'admin' and task['assigned_to'] != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('user_dashboard'))
    if request.method == 'POST':
        comment = request.form.get('comment', '').strip()
        photo = request.files.get('photo')
        if not photo or photo.filename == '':
            flash('Photo is required to confirm task completion.', 'error')
            return redirect(url_for('task_detail', task_id=task_id))
        if not allowed_file(photo.filename):
            flash('Invalid file type. Please upload an image.', 'error')
            return redirect(url_for('task_detail', task_id=task_id))
        ext = photo.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(filepath)
        updates = {
            'status': 'completed',
            'comment': comment,
            'photo_path': f"uploads/{filename}",
            'completed_at': datetime.utcnow()
        }
        Task.update_task(task_id, updates)
        flash('Task completed successfully! Awaiting admin approval.', 'success')
        return redirect(url_for('user_dashboard'))
    return render_template('task_detail.html', task=task)

@app.route('/task/<task_id>/photo')
@login_required
def view_task_photo(task_id):
    task = Task.get_task(task_id)
    if not task or not task.get('photo_path'):
        flash('Photo not found.', 'error')
        return redirect(url_for('user_dashboard'))
    if current_user.role != 'admin' and task['assigned_to'] != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('user_dashboard'))
    return redirect(url_for('static', filename=task['photo_path']))

@app.route('/my-archive')
@login_required
def user_archive():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    archived_tasks = Task.get_user_archived_tasks(current_user.id)
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return render_template('user_archive.html', archived_tasks=archived_tasks, weekdays=weekdays)

@app.cli.command('init-db')
def init_db():
    if not User.get_by_username('admin'):
        User.create_user('admin', 'admin123', 'admin@example.com', 'admin')
        print("Admin user created: username='admin', password='admin123'")
        print("IMPORTANT: Change this password in production!")
    else:
        print("Admin user already exists.")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5020)