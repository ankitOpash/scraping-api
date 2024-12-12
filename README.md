### 1. Create a Virtual Environment

Create and activate a virtual environment:

```bash
python -m venv venv
```

For Windows:

```bash
venv\Scripts\activate
```

For macOS/Linux:

```bash
source venv/bin/activate
```

### 2. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### 3. Initialize the Database

Run the ORM to create tables in the database:

```bash
python init_db.py
```

### 4. Run the Backend Project

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

### 5.for agentql set api key
```bash
$env:AGENTQL_API_KEY="your-api-key"
```
