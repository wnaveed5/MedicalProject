# Healthcare Denial Management Automation Tool

A web application designed to help healthcare staff manage and automate the denial management process for medical claims.

## Features

- Upload and process claim data
- Automatic identification of common billing issues
- Generation of denial reasons and appeal messages
- Issue tracking and logging
- User-friendly interface for healthcare staff

## Technology Stack

- Backend: Python + Flask
- Frontend: HTML/CSS with Bootstrap
- Database: SQLite
- Data Processing: Pandas
- Templates: Jinja2

## Setup Instructions

1. Clone the repository:
```bash
git clone [repository-url]
cd MedicalProject
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

5. Run the application:
```bash
flask run
```

The application will be available at `http://localhost:5000`

## Project Structure

```
MedicalProject/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── static/
│   └── templates/
├── instance/
├── migrations/
├── requirements.txt
└── README.md
```

## Usage

1. Access the web interface at `http://localhost:5000`
2. Upload claim data or enter it manually
3. Review automated analysis of potential billing issues
4. Generate and manage denial appeals
5. Track issues and their resolution status

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 