"""
STUDENT ATTENDANCE MANAGEMENT SYSTEM
Main Flask Application Entry Point
Authors: Marthav Ganesh (24BCE0662), Saketh Kolluri (24BAI0250), Kota Reeyan (24BCT0308)
"""
import os
from flask import Flask, render_template
from config import Config
from routes import auth_bp, admin_bp, faculty_bp, student_bp, report_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register Route Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(faculty_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(report_bp)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', not_found=True), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return "Internal Server Error: Please verify database connection and configuration.", 500

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"============================================================")
    print(f"  STUDENT ATTENDANCE MANAGEMENT SYSTEM")
    print(f"  Running on: http://127.0.0.1:{port}")
    print(f"  Database: {Config.DB_NAME} on {Config.DB_HOST}:{Config.DB_PORT}")
    print(f"============================================================")
    app.run(host='127.0.0.1', port=port, debug=True)
