# One Stop Portal

## Overview
One Stop Portal is a versatile tool designed to streamline content creation and quiz management. It features two main functionalities:

1. **Article Generation Tool**: Automates article creation using Google Sheets.
2. **Quiz App**: Simplifies quiz generation based on Google Sheets data.

---

## Features

### 1. Article Generation Tool
- **Input:** Requires Google Sheet ID and website names.
- **Functionality:** Uses sheet automation to generate articles efficiently for multiple websites.

### 2. Quiz App
- **Input:** Requires only the Google Sheet ID.
- **Functionality:** Generates quizzes automatically based on the data provided in the Google Sheet.

---

## How to Use

### For Article Generation:
```bash
# Input the Google Sheet ID and Website Names
python article_generator.py --sheet_id YOUR_SHEET_ID --websites "Website1, Website2"
```

### For Quiz App:
```bash
# Input the Google Sheet ID
python quiz_app.py --sheet_id YOUR_SHEET_ID
```


