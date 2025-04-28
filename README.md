# MMA Data Collection Application

A Flask application for scraping and storing MMA fight data from UFCStats.com.

## Features

- Scrape fighter profiles, event details, fight results, and round-by-round stats
- Store data in a PostgreSQL database using SQLAlchemy models
- Browse and manage data via Flask-Admin interface

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd mma-data-collection
```

2. Set up a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure your environment:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

5. Initialize the database:
```bash
flask init-db
```

## Usage

### Starting the application

```bash
flask run
```

The web interface will be available at http://localhost:5000

### Scraping data

To scrape data from an event:

```bash
flask scrape --start-url http://ufcstats.com/event-details/f3743d8ef5dde970
```

You can replace the URL with any UFC event page.

### Example URLs for Testing

- Event: `http://ufcstats.com/event-details/f3743d8ef5dde970` (UFC 303)
- Fight Details: `http://ufcstats.com/fight-details/fc8ad0c7fc70dde7` (Dan Ige vs Diego Lopes)
- Fighter: `http://ufcstats.com/fighter-details/f166e93d04a8c274` (Diego Lopes)

## Database Schema

The application uses four main models:

1. **Fighter**: Stores fighter biographical data and career statistics
2. **Event**: Stores event information like name, date, and location
3. **Fight**: Stores fight details and total fight statistics
4. **FightRoundStats**: Stores detailed round-by-round statistics for each fighter

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License. 