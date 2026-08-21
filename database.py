""""
the main purpose of this file is to setup a connection or a bridge from vscode to pgadmin.
so that our agent can fetch the dat from datbase.
"""

import os
import psycopg
from dotenv import load_dotenv
load_dotenv()

#postgressql dtabse connection url
DATABASE_URL=os.getenv(
    "DATABASE_URL"
)

#helper function 
def get_db_connection(): 
    try:
        conn=psycopg.connect(DATABASE_URL)
        return conn
    except Exception as error:
        raise ConnectionError(
            f"unable to connect{error}"
        )

def check_db()->bool:
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1;")
                return True
    except Exception as error:
        return False


def get_db_schema():
    """fetch te table names and teir respective columns from the postgresql database and feed them to 
    1. streamlit ui
    2. llm
    """
    query = """
        SELECT
            table_name,
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
    """

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()

                schema = {}

                for table_name, column_name, data_type in rows:
                    if table_name not in schema:
                        schema[table_name] = []

                    schema[table_name].append({
                        "column": column_name,
                        "type": data_type
                    })

                return schema

    except Exception as error:
        raise ConnectionError(
            f"Unable to fetch database schema: {error}"
        )
    
def seed_database():
    sql_statements = [
        # Drop existing tables cleanly
        "DROP TABLE IF EXISTS orders CASCADE;",
        "DROP TABLE IF EXISTS products CASCADE;",
        "DROP TABLE IF EXISTS users CASCADE;",
        "DROP TABLE IF EXISTS students CASCADE;",
        "DROP TABLE IF EXISTS employees CASCADE;",
        "DROP TABLE IF EXISTS departments CASCADE;",

        # 1. Departments Table
        """
        CREATE TABLE departments (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            location VARCHAR(100),
            budget NUMERIC(12, 2)
        );
        """,
        """
        INSERT INTO departments (name, location, budget) VALUES
        ('Engineering', 'San Francisco', 1500000.00),
        ('Marketing', 'New York', 800000.00),
        ('Human Resources', 'Chicago', 400000.00),
        ('Sales', 'Austin', 1200000.00),
        ('Finance', 'New York', 900000.00);
        """,

        # 2. Employees Table
        """
        CREATE TABLE employees (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE,
            salary NUMERIC(10, 2),
            department_id INT REFERENCES departments(id),
            hire_date DATE
        );
        """,
        """
        INSERT INTO employees (name, email, salary, department_id, hire_date) VALUES
        ('Rahul Verma', 'rahul@example.com', 95000.00, 1, '2021-03-15'),
        ('Aman Sharma', 'aman@example.com', 88000.00, 1, '2022-01-10'),
        ('Priya Patel', 'priya@example.com', 92000.00, 1, '2020-06-20'),
        ('Neha Gupta', 'neha@example.com', 75000.00, 2, '2021-09-01'),
        ('Vikram Singh', 'vikram@example.com', 72000.00, 2, '2022-05-12'),
        ('Ananya Roy', 'ananya@example.com', 68000.00, 3, '2019-11-05'),
        ('Rohan Mehta', 'rohan@example.com', 85000.00, 4, '2021-02-28'),
        ('Kavya Nair', 'kavya@example.com', 90000.00, 4, '2020-08-14'),
        ('Siddharth Kumar', 'siddharth@example.com', 98000.00, 5, '2018-04-01'),
        ('Deepak Joshi', 'deepak@example.com', 65000.00, 3, '2023-02-10');
        """,

        # 3. Students Table
        """
        CREATE TABLE students (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE,
            course VARCHAR(100),
            marks INT,
            enrollment_date DATE
        );
        """,
        """
        INSERT INTO students (name, email, course, marks, enrollment_date) VALUES
        ('Rahul Sharma', 'rahul.s@example.com', 'Computer Science', 98, '2023-08-01'),
        ('Aman Verma', 'aman.v@example.com', 'Computer Science', 95, '2023-08-01'),
        ('Priya Singh', 'priya.s@example.com', 'Data Science', 94, '2023-08-01'),
        ('Neha Agarwal', 'neha.a@example.com', 'Data Science', 91, '2023-08-01'),
        ('Karan Malhotra', 'karan.m@example.com', 'AI', 89, '2023-08-01'),
        ('Simran Kaur', 'simran.k@example.com', 'Computer Science', 87, '2023-08-01'),
        ('Arjun Reddy', 'arjun.r@example.com', 'Cybersecurity', 85, '2023-08-01'),
        ('Ishaan Iyer', 'ishaan.i@example.com', 'AI', 82, '2023-08-01'),
        ('Tanya Sen', 'tanya.s@example.com', 'Cybersecurity', 78, '2023-08-01'),
        ('Varun Rao', 'varun.r@example.com', 'Data Science', 72, '2023-08-01');
        """,

        # 4. Users Table
        """
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE,
            city VARCHAR(50)
        );
        """,
        """
        INSERT INTO users (name, email, city) VALUES
        ('Aarav Mehta', 'aarav@gmail.com', 'Delhi'),
        ('Diya Kapoor', 'diya@gmail.com', 'Mumbai'),
        ('Kabir Das', 'kabir@yahoo.com', 'Delhi'),
        ('Myra Joshi', 'myra@hotmail.com', 'Bangalore'),
        ('Vihaan Trivedi', 'vihaan@gmail.com', 'Hyderabad'),
        ('Aditi Rao', 'aditi@gmail.com', 'Delhi'),
        ('Reyansh Bhatia', 'reyansh@gmail.com', 'Chennai');
        """,

        # 5. Products Table
        """
        CREATE TABLE products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            category VARCHAR(50),
            price NUMERIC(10, 2),
            stock_quantity INT
        );
        """,
        """
        INSERT INTO products (name, category, price, stock_quantity) VALUES
        ('MacBook Pro M3', 'Electronics', 1999.99, 25),
        ('iPhone 15 Pro', 'Electronics', 1199.99, 50),
        ('Dell XPS 15', 'Electronics', 1499.99, 15),
        ('Ergonomic Chair', 'Furniture', 299.99, 40),
        ('Standing Desk', 'Furniture', 499.99, 20),
        ('Mechanical Keyboard', 'Accessories', 129.99, 100),
        ('Noise Cancelling Headphones', 'Accessories', 249.99, 60);
        """,

        # 6. Orders Table
        """
        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            user_id INT REFERENCES users(id),
            product_id INT REFERENCES products(id),
            quantity INT,
            total_amount NUMERIC(10, 2),
            order_date DATE
        );
        """,
        """
        INSERT INTO orders (user_id, product_id, quantity, total_amount, order_date) VALUES
        (1, 1, 1, 1999.99, '2024-01-15'),
        (1, 6, 2, 259.98, '2024-01-16'),
        (2, 2, 1, 1199.99, '2024-01-20'),
        (3, 4, 2, 599.98, '2024-02-01'),
        (4, 5, 1, 499.99, '2024-02-05'),
        (5, 3, 1, 1499.99, '2024-02-15'),
        (6, 7, 1, 249.99, '2024-03-01');
        """
    ]
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for i in sql_statements:
                    cursor.execute(i)
            conn.commit()
            print("database seeded successfully")
    except Exception as error:
        print(f"error seeding the database: {error}")

if __name__ == "__main__":
    seed_database()



        
