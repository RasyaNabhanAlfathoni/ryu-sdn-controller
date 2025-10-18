# Konfigurasi database (psycopg2)

import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_conn():
    return psycopg2.connect(
        dbname="sdn_controller",
        user="sdn",
        password="123",
        host="localhost",
        cursor_factory=RealDictCursor
    )
