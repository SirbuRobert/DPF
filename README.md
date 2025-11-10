# Digital Performance Foundation (DPF) - Smarthack 2025

## Project Overview

**Digital Performance Foundation (DPF)** is an educational platform developed for the Smarthack 2025 competition. The project aims to modernize the learning experience by leveraging Artificial Intelligence (AI) to enhance teaching materials and student engagement.

Built on the Django framework, DPF provides a robust system for managing didactic resources, generating interactive quizzes, summarizing complex lessons, and facilitating communication between students and teachers.

## Key Features

* **AI-Powered Content Generation:** Utilizes a pre-trained T5 small model for text processing, allowing for:
    * Automatic summarization of uploaded lesson materials.
    * Generation of quizzes (questions and answers) based on the input text content.
* **User Management:** Dedicated profiles and dashboards for two main user roles:
    * **Elevi (Students):** Access lessons, take AI-generated quizzes, view progress, and engage in chat.
    * **Profesori (Teachers):** Upload didactic materials, manage student lists, and communicate with students.
* **Didactic Material Management:** Supports uploading and viewing lesson materials (e.g., PDF files) organized by subject/topic.
* **Integrated Communication:** A dedicated chat feature to allow direct messaging between students and teachers.

## Tech Stack

The core components of the project are:

* **Backend Framework:** Django (Python)
* **AI/NLP:** Hugging Face Transformers (T5-small model fine-tunned for summarization and quiz generation)
* **Database:** PostgreSQL 
* **Frontend:** HTML5, CSS (with custom styling), and JavaScript

## Installation and Setup

### Prerequisites

* Python (3.x recommended)
* Virtual Environment Tool (`venv` or `conda`)

### Steps

1.  **Clone the Repository:**
    ```bash
    git clone [YOUR_REPO_URL_HERE]
    cd digitalperformancefoundation---smarthack-2025/DPF
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    .\venv\Scripts\activate   # On Windows
    ```

3.  **Install Dependencies:**
    *Note: The primary dependencies are listed in `requirments.txt`.*
    ```bash
    pip install -r requirments.txt
    ```

4.  **Run Migrations:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5.  **Create a Superuser (Admin):**
    ```bash
    python manage.py createsuperuser
    ```

6.  **Run the Server:**
    ```bash
    python manage.py runserver
    ```
    The application will now be running at `http://127.0.0.1:8000/`.

