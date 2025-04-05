import csv
from sqlalchemy import create_engine, Column, String, Integer, Enum, CheckConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError

Base = declarative_base()

class Seat(Base):
	__tablename__ = 'Seats'
	seat_id = Column(String(10), primary_key=True)
	row = Column(String(1), nullable=False)
	position = Column(Integer, nullable=False)
	type = Column(Enum('seat', 'aisle', 'storage', name='seat_type'), nullable=False)
	status = Column(Enum('F', 'R', name='seat_status'), nullable=True)

	__table_args__ = (
		CheckConstraint(
			"(type != 'seat') OR (status IN ('F', 'R'))"
		),
	)

	@staticmethod
	def initialize_database(session, csv_filename='Seats.csv'):
		Base.metadata.create_all(session.bind)

		if session.query(Seat).count() == 0:
			try:
				with open(csv_filename, 'r') as f:
					csv_reader = csv.reader(f)
					for csv_row in csv_reader:
						row_label = csv_row[0]
						for idx, cell in enumerate(csv_row[1:], start=1):
							seat_type = 'seat'
							if cell == 'X':
								seat_type = 'aisle'
							elif cell == 'S':
								seat_type = 'storage'

							if seat_type == 'seat':
								seat_id = cell
							else:
								seat_id = f"{row_label}-{idx}"

							seat = Seat(
								seat_id=seat_id,
								row=row_label,
								position=idx,
								type=seat_type,
								status='F' if seat_type == 'seat' else None
							)
							session.add(seat)
				session.commit()
			except IntegrityError:
				session.rollback()
				print("Error initializing database. Duplicate seats detected.")
			except Exception as e:
				session.rollback()
				print(f"Error initializing database: {e}")

def show_menu():
	print("\nMenu:")
	print("1. Check availability of seat")
	print("2. Book a seat")
	print("3. Free a seat")
	print("4. Show booking status")
	print("5. Exit program")

def check_availability(session):
	seat_id = input("Enter seat number: ").strip().upper()
	seat = session.query(Seat).filter_by(seat_id=seat_id).first()

	if not seat:
		print("Invalid seat number.")
	elif seat.type != 'seat':
		print("This is not a bookable seat.")
	else:
		print(f"Seat {seat_id} is {'available.' if seat.status == 'F' else 'booked.'}")

def book_seat(session):
	seat_id = input("Enter seat number to book: ").strip().upper()
	seat = session.query(Seat).filter_by(seat_id=seat_id).first()

	if not seat:
		print("Invalid seat number.")
	elif seat.type != 'seat':
		print("Cannot book non-seat area.")
	elif seat.status == 'R':
		print("Seat already booked.")
	else:
		seat.status = 'R'
		session.commit()
		print(f"Seat {seat_id} booked successfully.")

def free_seat(session):
	seat_id = input("Enter seat number to free: ").strip().upper()
	seat = session.query(Seat).filter_by(seat_id=seat_id).first()

	if not seat:
		print("Invalid seat number.")
	elif seat.type != 'seat':
		print("Cannot free non-seat area.")
	elif seat.status == 'F':
		print("Seat is not booked.")
	else:
		seat.status = 'F'
		session.commit()
		print(f"Seat {seat_id} freed successfully.")

def show_booking_status(session):
	rows = session.query(Seat.row).distinct().order_by(Seat.row).all()
	rows = [row[0] for row in rows]

	print("\nCurrent Booking Status:")
	for row_label in rows:
		seats = session.query(Seat).filter_by(row=row_label).order_by(Seat.position).all()
		row_display = [row_label]
		for seat in seats:
			if seat.type == 'aisle':
				row_display.append('X')
			elif seat.type == 'storage':
				row_display.append('S')
			else:
				row_display.append(seat.status if seat.status else 'F')
		print(','.join(row_display))

def main():
	engine = create_engine('sqlite:///FC723_final.db')
	Base.metadata.create_all(engine)
	Session = sessionmaker(bind=engine)
	session = Session()

	Seat.initialize_database(session)

	while True:
		show_menu()
		choice = input("Enter your choice (1-5): ").strip()

		if choice == '1':
			check_availability(session)
		elif choice == '2':
			book_seat(session)
		elif choice == '3':
			free_seat(session)
		elif choice == '4':
			show_booking_status(session)
		elif choice == '5':
			print("Thank you for using Apache Airlines. Goodbye!")
			break
		else:
			print("Invalid choice. Please try again.")

	session.close()

if __name__ == "__main__":
	main()