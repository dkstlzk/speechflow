import sys
from sqlalchemy import create_engine
engine = create_engine("postgresql+psycopg2://dkstlzk:speechflow123@localhost:5432/speechflow")
with engine.connect() as conn:
    res = conn.execute("SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_enum.enumtypid = pg_type.oid WHERE pg_type.typname = 'session_status';")
    for row in res:
        print(row[0])
