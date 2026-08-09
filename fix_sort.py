import re

with open('app.py', 'r') as f:
    content = f.read()

# Fix 1: admin_dashboard - add sort after the for loop
old1 = '''    for task in tasks:
        day = task.get('weekday', 'Unassigned')
        if day in tasks_by_day:
            assignee = db.users.find_one({'_id': ObjectId(task['assigned_to'])})
            task['assignee_name'] = assignee['username'] if assignee else 'Unknown'
            tasks_by_day[day].append(task)
    return render_template('admin_dashboard.html', tasks_by_day=tasks_by_day, weekdays=weekdays)'''

new1 = '''    for task in tasks:
        day = task.get('weekday', 'Unassigned')
        if day in tasks_by_day:
            assignee = db.users.find_one({'_id': ObjectId(task['assigned_to'])})
            task['assignee_name'] = assignee['username'] if assignee else 'Unknown'
            tasks_by_day[day].append(task)
    for day in weekdays:
        tasks_by_day[day].sort(key=lambda t: (str(t.get('due_date') or '9999-99-99'), t.get('title', '').lower()))
    return render_template('admin_dashboard.html', tasks_by_day=tasks_by_day, weekdays=weekdays)'''

content = content.replace(old1, new1)

# Fix 2: admin_archive - add sort after the for loop
old2 = '''    for task in archived_tasks:
        day = task.get('weekday', 'Unassigned')
        if day in tasks_by_day:
            assignee = db.users.find_one({'_id': ObjectId(task['assigned_to'])})
            task['assignee_name'] = assignee['username'] if assignee else 'Unknown'
            approver = db.users.find_one({'_id': ObjectId(task.get('approved_by', ''))})
            task['approver_name'] = approver['username'] if approver else 'Unknown'
            tasks_by_day[day].append(task)
    return render_template('admin_archive.html', tasks_by_day=tasks_by_day, weekdays=weekdays)'''

new2 = '''    for task in archived_tasks:
        day = task.get('weekday', 'Unassigned')
        if day in tasks_by_day:
            assignee = db.users.find_one({'_id': ObjectId(task['assigned_to'])})
            task['assignee_name'] = assignee['username'] if assignee else 'Unknown'
            approver = db.users.find_one({'_id': ObjectId(task.get('approved_by', ''))})
            task['approver_name'] = approver['username'] if approver else 'Unknown'
            tasks_by_day[day].append(task)
    for day in weekdays:
        tasks_by_day[day].sort(key=lambda t: (str(t.get('due_date') or '9999-99-99'), t.get('title', '').lower()))
    return render_template('admin_archive.html', tasks_by_day=tasks_by_day, weekdays=weekdays)'''

content = content.replace(old2, new2)

# Fix 3: user_dashboard - add sort
old3 = '''    active_tasks = Task.get_user_tasks(current_user.id, selected_day, include_archived=False)
    archived_tasks = Task.get_user_archived_tasks(current_user.id)
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']'''

new3 = '''    active_tasks = Task.get_user_tasks(current_user.id, selected_day, include_archived=False)
    archived_tasks = Task.get_user_archived_tasks(current_user.id)
    active_tasks.sort(key=lambda t: (str(t.get('due_date') or '9999-99-99'), t.get('title', '').lower()))
    weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']'''

content = content.replace(old3, new3)

with open('app.py', 'w') as f:
    f.write(content)

print("Done! Fixed 3 sort locations.")
