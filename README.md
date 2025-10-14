# Software-Only Parking Management System (Mini Project)

## Setup
1. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Create `.env` file with:
```
ADMIN_API_KEY=mysecret123
```

3. Run the app:
```bash
uvicorn main:app --reload
```

4. Open the API docs:
```
http://127.0.0.1:8000/docs
```

## Usage
- Add vehicles (/vehicles/add)
- Occupy slots (/slots/occupy/{slot_id})
- Free slots (/slots/free/{slot_id})
- View slots (/slots)
API key is required in header `api_key` for modifying data.
