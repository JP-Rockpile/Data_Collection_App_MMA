# MMA Data Collection API

A Flask API for collecting and managing MMA fight data, including fighters, events, and fights.

## Requirements

- Python 3.9+
- PostgreSQL database

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mma-data-api
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on `.env.example` and update with your PostgreSQL credentials:
```bash
cp .env.example .env
# Edit .env with your actual database credentials
```

## Database Setup

1. Create a PostgreSQL database:
```sql
CREATE DATABASE my_db_name;
CREATE USER my_db_user WITH PASSWORD 'my_db_password';
GRANT ALL PRIVILEGES ON DATABASE my_db_name TO my_db_user;
```

2. Update the `.env` file with your PostgreSQL connection details.

## Running the Application

Start the Flask development server:
```bash
python run.py
```

The API will be available at http://localhost:5000/

## API Endpoints

### Fighters

- `GET /api/fighters` - Get all fighters
- `GET /api/fighters/<id>` - Get a specific fighter
- `POST /api/fighters` - Create a new fighter
- `PUT /api/fighters/<id>` - Update a fighter
- `DELETE /api/fighters/<id>` - Delete a fighter

### Events

- `GET /api/events` - Get all events
- `GET /api/events/<id>` - Get a specific event
- `POST /api/events` - Create a new event
- `PUT /api/events/<id>` - Update an event
- `DELETE /api/events/<id>` - Delete an event

### Fights

- `GET /api/fights` - Get all fights
- `GET /api/fights/<id>` - Get a specific fight
- `POST /api/fights` - Create a new fight
- `PUT /api/fights/<id>` - Update a fight
- `DELETE /api/fights/<id>` - Delete a fight

## Example Requests

### Create a fighter
```bash
curl -X POST http://localhost:5000/api/fighters \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Jon", "last_name": "Jones", "nickname": "Bones", "height": 193.04, "reach": 215.9}'
```

### Create an event
```bash
curl -X POST http://localhost:5000/api/events \
  -H "Content-Type: application/json" \
  -d '{"event_name": "UFC 285", "event_date": "2023-03-04", "location": "Las Vegas, Nevada"}'
```

### Create a fight
```bash
curl -X POST http://localhost:5000/api/fights \
  -H "Content-Type: application/json" \
  -d '{"event_id": 1, "fighter1_id": 1, "fighter2_id": 2, "weight_class": "Heavyweight", "scheduled_rounds": 5}'
``` 