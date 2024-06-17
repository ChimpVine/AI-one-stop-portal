from app import app
from extensions import db
from models import Department

def create_departments():
    with app.app_context():
        departments = ['H5P', 'Article', 'Quiz']
        for name in departments:
            if not Department.query.filter_by(name=name).first():
                department = Department(name=name)
                db.session.add(department)
        db.session.commit()
        print("Departments added successfully.")

if __name__ == "__main__":
    create_departments()

