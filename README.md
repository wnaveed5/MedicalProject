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

## Installation Instructions

1. **Clone the repository:**
    ```bash
    git clone [repository-url]
    cd MedicalProject
    ```

2. **Set up a virtual environment (Python 3.8+ recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Set environment variables (optional, see `env.example`):**
    - Copy `env.example` to `.env` and adjust as needed.

5. **Initialize the database:**
    ```bash
    flask db init
    flask db migrate
    flask db upgrade
    ```

6. **Run the application:**
    ```bash
    flask run
    ```

The application will be available at [http://localhost:5000](http://localhost:5000).

## Usage Guide

1. **Access the web interface:**  
   Open your browser and go to [http://localhost:5000](http://localhost:5000).

2. **Upload claim data:**  
   Use the upload feature or enter claim data manually.

3. **Review analysis:**  
   The system will automatically identify potential billing issues and suggest denial reasons.

4. **Generate appeals:**  
   Use the interface to generate and manage denial appeal messages.

5. **Track issues:**  
   Monitor the status of claims and appeals through the issue tracker.

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

## Contributing

I welcome contributions! To get started:

1. Fork the repository and create your branch from `main`.
2. If you've added code, write tests.
3. Ensure the test suite passes:  
   ```bash
   pytest --cov=migrations tests/

<img width="1454" height="707" alt="Screenshot 2025-07-31 at 2 28 28 PM" src="https://github.com/user-attachments/assets/49943bf0-20b3-4aaa-8875-7ae84e0c12eb" />
<img width="1458" height="710" alt="Screenshot 2025-07-31 at 2 29 19 PM" src="https://github.com/user-attachments/assets/1a923e72-f14e-4ab1-80f6-7499994b08e3" />


   
   ```
4. Submit a pull request with a clear description of your changes.

Please read `CONTRIBUTING.md` for more details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
