from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectMultipleField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError
from models import User, Department


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[
                            DataRequired()])  # New field for full name
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError(
                'Email already registered. Please use a different email address.')
        
    def validate_admin_email(self, email):
        user = User.query.filter_by(email=email.data, is_admin=True).first()
        if user is not None:
            raise ValidationError('Admin with this email already exists.')


class DepartmentAssignmentForm(FlaskForm):
    user = SelectField('Staff', coerce=int, validators=[DataRequired()])
    departments = SelectMultipleField(
        'Departments', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Assign Departments')
