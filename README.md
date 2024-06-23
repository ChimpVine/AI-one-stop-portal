# Chimpvine Web Application

Chimpvine is a web application built with Flask that provides educational content on mathematics topics such as even and odd numbers, quizzes, and interactive articles.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)

## Overview

Chimpvine is designed to dynamically generate educational content based on user queries. It serves as an educational platform where users can access articles, quizzes, and interactive content related to various mathematical concepts. The application also includes administrative functionalities for managing users, departments, and content generation.

## Features

- **Content Generation**: Automatically generates educational articles based on specified topics and keywords.
- **User Management**: Allows registration, login, and assignment of administrative roles.
- **Department Assignment**: Assigns users to various departments such as H5P, Article, Quiz and Video Script.
- **Database Integration**: Utilizes SQLAlchemy for database management, storing user data and department assignments.
- **Web Interface**: Provides a user-friendly web interface for interaction and management.

## Installation

To run Chimpvine locally, follow these steps:

1. **Clone Repository**:
   ```bash
   git clone https://github.com/your-username/Chimpvine.git
   cd Chimpvine
   ```

   - **Explanation**: This command clones the repository from your GitHub account to your local machine and navigates into the project directory.

2. **Set Up Virtual Environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

   - **Explanation**: Setting up a virtual environment (`venv`) isolates dependencies for the project, ensuring compatibility and preventing conflicts with other Python projects on your system.

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   - **Explanation**: Installs all necessary Python packages listed in the `requirements.txt` file. These packages include Flask, SQLAlchemy, Flask-WTF, and other dependencies required for the application.

4. **Set Environment Variables**:
   Create a `.env` file in the root directory with the following variables:
   ```dotenv
   SECRET_KEY=your_secret_key
   DATABASE_URL=sqlite:///site.db
   ```

   - **Explanation**: The `.env` file stores sensitive or environment-specific configurations. `SECRET_KEY` is used by Flask for session management and security, while `DATABASE_URL` specifies the database connection URL (SQLite in this case).

5. **Initialize Database**:
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

   - **Explanation**: These commands initialize the database migrations with Flask-Migrate. It creates the necessary migration folder (`migrations/`), generates an initial migration script based on the current state of your models, and applies the migration to create the database schema.

6. **Run Application**:
   ```bash
   flask run
   ```

   - **Explanation**: Starts the Flask development server. You can now access the application by navigating to `http://localhost:5000` in a web browser.

7. **Access Application**:
   Open a web browser and navigate to `http://localhost:5000`.

   - **Explanation**: Once the application is running, you can interact with its features through the web interface.

## Usage

- **Admin Panel**: Use the provided `add_admin.py` script to create an admin user.
- **Department Assignment**: Use `add_departments.py` to add departments (e.g., H5P, Article, Quiz).
- **Content Generation**: Use `submit_MathfunForm` function to generate and submit educational content based on predefined templates.

   - **Explanation**: This section outlines how to perform administrative tasks such as creating admin users and managing departments. It also explains how to generate educational content using predefined functions.


