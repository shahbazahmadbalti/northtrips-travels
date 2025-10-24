# North Trips and Travel - Refactored Flask Application

This is the refactored version of your monolithic `app.py` file, split into a standard Flask project structure for better maintainability.

## Project Structure

The application now follows this structure:

```
.
├── app.py                  # Main application logic and routes
├── database.db             # SQLite database file (will be created on first run)
├── README.md               # This file
├── static/
│   └── css/
│       └── style.css       # All CSS styles
└── templates/
    ├── admin/              # Templates for the admin dashboard
    │   ├── bookings.html
    │   ├── dashboard.html
    │   ├── edit_tour.html
    │   ├── tickets.html
    │   ├── tours.html
    │   └── users.html
    ├── about.html
    ├── base.html           # Base template with navigation and footer
    ├── book_tour.html
    ├── contact.html
    ├── index.html
    ├── login.html
    ├── profile.html
    ├── register.html
    ├── tour_detail.html
    └── tours.html
```

## How to Run

1.  **Install Dependencies:**
    You will need `flask`, `sqlite3`, and `pdfkit`. The original code also implies the use of `wkhtmltopdf` (an external binary) for PDF generation, which must be installed on your system or Railway environment.
    
    ```bash
    pip install Flask pdfkit
    # You must also install the wkhtmltopdf binary on your system
    # On Debian/Ubuntu: sudo apt-get install wkhtmltopdf
    ```

2.  **Run the Application:**
    
    ```bash
    python3 app.py
    ```

3.  **Access the App:**
    The application will be running at `http://127.0.0.1:5000/`.

## Key Changes

*   **`app.py`:** Contains all the Python logic, imports, database setup, helper functions, and Flask routes. All `render_template_string` calls have been replaced with `render_template`, pointing to the new external HTML files. The only exception is the `download_invoice` route, which still uses `render_template_string` to generate the HTML content for the PDF, as this content is dynamic and not a standard page.
*   **`static/css/style.css`:** All the embedded CSS from the original file has been moved here.
*   **`templates/`:** All HTML content has been extracted into separate Jinja2 template files.
    *   `base.html` holds the common structure (header, navigation, footer, flash messages).
    *   All other HTML files (`index.html`, `login.html`, etc.) now `{% extends "base.html" %}` and define their specific content in the `{% block content %}`.
    *   Admin templates are placed in the `templates/admin/` subdirectory.

This refactoring makes the code much cleaner and easier to manage, especially for future updates to the UI or backend logic.

