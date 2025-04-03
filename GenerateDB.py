import sqlalchemy
from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

engine = create_engine('sqlite:///FC723_Final.db')
Base = sqlalchemy.orm.declarative_base()

class SQLTable(Base):
    __tablename__ = 'Seats'
    row_label = Column(String, primary_key=True)  # Primary key as row label

# Dynamically add 80 columns (col1 to col80) to the SQLTable class
for col_num in range(1, 81):
    col_name = f'col{col_num}'
    setattr(SQLTable, col_name, Column(String))

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

rows_order = ['A', 'B', 'C', 'X', 'D', 'E', 'F']

for row_label in rows_order:
    data = {'row_label': row_label}
    if row_label == 'X':
        # All columns in row X are 'X'
        for col_num in range(1, 81):
            data[f'col{col_num}'] = 'X'
    else:
        for col_num in range(1, 81):
            # Check if current column is 77 or 78 in rows D, E, F
            if row_label in ['D', 'E', 'F'] and col_num in [77, 78]:
                data[f'col{col_num}'] = 'S'
            else:
                data[f'col{col_num}'] = f"{col_num}{row_label}"
    session.add(SQLTable(**data))

session.commit()
session.close()



