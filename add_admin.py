from app import app
from extensions import db
from models import User


def create_admin():
    with app.app_context():
        admin_email = "admin12@email.com"
        admin_password = "Admin123"
        admin_full_name = "Admin User"  # Added full_name for the admin

        # Check if admin already exists
        if User.query.filter_by(email=admin_email).first():
            print("Admin user already exists.")
            return

        admin = User(email=admin_email,
                     full_name=admin_full_name, is_admin=True)
        admin.set_password(admin_password)

        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully.")


if __name__ == "__main__":
    create_admin()
