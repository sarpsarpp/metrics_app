# Running the Metrics App

## Prerequisites
- Python 3.8 or higher
- pip package manager

## Setup Instructions

### 1. Create Virtual Environment
```bash
python3 -m venv venv
```

### 2. Activate Virtual Environment

**On macOS/Linux:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
streamlit run app.py
```

## Access the Application
Once running, the app will be available at:
- Local URL: http://localhost:8501
- Network URL: Check the terminal output for your network URL

## Stopping the Application
Press `Ctrl+C` in the terminal to stop the Streamlit server.

## Deactivating Virtual Environment
When you're done, deactivate the virtual environment:
```bash
deactivate
```

## Troubleshooting

### Performance Warning
If you see a performance warning, you can install watchdog:
```bash
pip install watchdog
```

### Port Already in Use
If port 8501 is already in use, you can specify a different port:
```bash
streamlit run app.py --server.port 8502
```