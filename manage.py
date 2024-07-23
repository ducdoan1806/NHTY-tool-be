import os
from flask import Flask
from flask_migrate import Migrate
from app import create_app, db

config_path = os.path.join(os.path.dirname(__file__), 'app/config.py')
app = create_app(config_path)
migrate = Migrate(app, db)

@app.cli.command('db_init')
def db_init():
    """Initialize the database migration repository."""
    from flask_migrate import init
    init()

@app.cli.command('db_migrate')
@app.cli.option('--message', prompt='Migration message', help='The migration message')
def db_migrate(message):
    """Generate a new database migration."""
    from flask_migrate import migrate
    migrate(message=message)

@app.cli.command('db_upgrade')
def db_upgrade():
    """Apply the latest database migrations."""
    from flask_migrate import upgrade
    upgrade()

@app.cli.command('db_downgrade')
@app.cli.option('--revision', prompt='Revision to downgrade to', help='The revision to downgrade to')
def db_downgrade(revision):
    """Downgrade the database to a specific revision."""
    from flask_migrate import downgrade
    downgrade(revision)

if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1", port=81818)
