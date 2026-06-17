module.exports = {
  apps: [{
    name: 'katari-tasks',
    script: './wsgi.py',
    interpreter: '/home/jay/venv/bin/python3',
    cwd: '/home/jay/katari-intern-tastks',
    watch: true,
    env: {
      FLASK_ENV: 'production'
    }
  }]
}
