"""
Main application entry point
"""
from app.core.app import create_app
from app.config.config import DEBUG

app = create_app()

if __name__ == '__main__':
    app.run(debug=DEBUG)