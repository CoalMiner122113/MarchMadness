import mysql.connector
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def export_database():
    # Connect to local MySQL
    connection = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST'),
        user=os.getenv('MYSQL_USER'),
        password=os.getenv('MYSQL_PASS')
    )
    
    cursor = connection.cursor()
    
    # Get all tables
    cursor.execute("USE marchMadness")
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    
    # Create export directory if it doesn't exist
    if not os.path.exists('db_export'):
        os.makedirs('db_export')
    
    # Export each table
    for table in tables:
        table_name = table[0]
        print(f"Exporting table: {table_name}")
        
        # Get table structure
        cursor.execute(f"SHOW CREATE TABLE {table_name}")
        create_table = cursor.fetchone()[1]
        
        # Get table data
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        # Write to file
        with open(f'db_export/{table_name}.sql', 'w') as f:
            # Write table creation
            f.write(f"{create_table};\n\n")
            
            # Write data
            for row in rows:
                values = [f"'{str(v)}'" if v is not None else 'NULL' for v in row]
                f.write(f"INSERT INTO {table_name} VALUES ({', '.join(values)});\n")
    
    cursor.close()
    connection.close()
    print("Database export completed!")

if __name__ == "__main__":
    export_database() 