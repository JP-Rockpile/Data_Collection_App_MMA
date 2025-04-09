# PostgreSQL Setup Guide for DBeaver

## Installing DBeaver

1. Download and install DBeaver Community Edition from [DBeaver website](https://dbeaver.io/download/)

## Creating a PostgreSQL Connection in DBeaver

1. Open DBeaver
2. Click on the "New Database Connection" button (database+ icon)
3. Select "PostgreSQL" from the list of database types and click "Next"

4. Enter the following connection details:
   - **Host**: localhost (or your PostgreSQL server address)
   - **Port**: 5432
   - **Database**: postgres (initially connect to default database)
   - **Username**: your_postgres_username (default is often 'postgres')
   - **Password**: your_postgres_password

5. Test the connection by clicking "Test Connection..." button
6. If successful, click "Finish" to create the connection

## Creating the MMA Database

1. Right-click on your PostgreSQL connection and select "SQL Editor" > "Open SQL Script"
2. Run the following SQL commands:

```sql
-- Create a new database for the MMA application
CREATE DATABASE my_db_name;

-- Create a user with permissions
CREATE USER my_db_user WITH PASSWORD 'my_db_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE my_db_name TO my_db_user;
```

3. Refresh your connection by right-clicking on the connection and selecting "Refresh"
4. You should now see your new database in the list

## Creating a Connection to the MMA Database

1. Click on the "New Database Connection" button
2. Select "PostgreSQL" from the list of database types and click "Next"
3. Enter the following connection details:
   - **Host**: localhost (or your PostgreSQL server address)
   - **Port**: 5432
   - **Database**: my_db_name (the database you just created)
   - **Username**: my_db_user
   - **Password**: my_db_password
4. Test the connection and click "Finish"

## Update Your .env File

Update your `.env` file with the database connection details:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=my_db_name
DB_USER=my_db_user
DB_PASSWORD=my_db_password
```

## Run Your Flask Application

Your Flask application will create the necessary tables when you run it for the first time. Make sure your database connection is active before running the application:

```bash
python run.py
```

After running your application, refresh your database connection in DBeaver, and you should see the tables created by SQLAlchemy:
- fighters
- events
- fights 