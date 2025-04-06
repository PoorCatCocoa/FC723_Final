import csv
import random
import string
from sqlalchemy import create_engine, Column, String, Integer, Enum, CheckConstraint, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.exc import IntegrityError

Base = declarative_base()


class Seat(Base):
	__tablename__ = 'Seats'
	seat_id = Column(String(10), primary_key=True)
	row = Column(String(1), nullable=False)
	position = Column(Integer, nullable=False)
	type = Column(Enum('seat', 'aisle', 'storage', name='seat_type'), nullable=False)
	booking_reference = Column(String(8), unique=True, nullable=True)
	category = Column(Enum('window', 'middle', 'aisle', name='seat_category'), nullable=True)

	__table_args__ = (
		CheckConstraint(
			"(type != 'seat') OR (category IS NOT NULL)",
			name='check_seat_category'
		),
		CheckConstraint(
			"(type != 'seat') OR (booking_reference IS NULL OR LENGTH(booking_reference) = 8)"
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
						positions = csv_row[1:]

						# Determine category based on row letter
						if row_label in ['A', 'F']:
							category = 'window'
						elif row_label in ['B', 'E']:
							category = 'middle'
						elif row_label in ['C', 'D']:
							category = 'aisle'
						else:
							category = 'middle'  # Default for other rows

						for idx, cell in enumerate(positions, start=1):
							seat_type = 'seat'
							if cell == 'X':
								seat_type = 'aisle'
							elif cell == 'S':
								seat_type = 'storage'

							seat_id = f"{row_label}{cell}" if seat_type == 'seat' else f"{row_label}-{idx}"

							seat = Seat(
								seat_id=seat_id,
								row=row_label,
								position=idx,
								type=seat_type,
								booking_reference=None,
								category=category if seat_type == 'seat' else None
							)
							session.add(seat)
				session.commit()
			except IntegrityError as e:
				session.rollback()
				print(f"Database error: {e}")
			except Exception as e:
				session.rollback()
				print(f"Error: {e}")


class Traveler(Base):
	__tablename__ = 'Travelers'
	booking_reference = Column(String(8), ForeignKey('Seats.booking_reference'), primary_key=True)
	passport_number = Column(String(20), nullable=False)
	first_name = Column(String(50), nullable=False)
	last_name = Column(String(50), nullable=False)
	seat_row = Column(String(1), nullable=False)
	seat_column = Column(Integer, nullable=False)


def generate_booking_reference(session):
	chars = string.ascii_uppercase + string.digits
	while True:
		reference = ''.join(random.choices(chars, k=8))
		if not session.query(Seat).filter_by(booking_reference=reference).first():
			return reference


def show_menu():
	print("\nMenu:")
	print("1. Check seat availability")
	print("2. Book a seat")
	print("3. Free a seat")
	print("4. Show booking status")
	print("5. Exit")


def check_availability(session):
	seat_id = input("Enter seat number: ").strip().upper()
	seat = session.query(Seat).filter_by(seat_id=seat_id).first()

	if not seat or seat.type != 'seat':
		print("Invalid seat number.")
	else:
		print(f"Seat {seat_id} ({seat.category}) is {'available' if not seat.booking_reference else 'booked'}.")


def book_seat(session):
	print("\nChoose seat type:")
	print("1. Window (Rows A/F)")
	print("2. Middle (Rows B/E)")
	print("3. Aisle (Rows C/D)")
	choice = input("Choice (1-3): ").strip()

	category_map = {'1': 'window', '2': 'middle', '3': 'aisle'}
	if choice not in category_map:
		print("Invalid choice.")
		return

	seat = session.query(Seat).filter(
		Seat.category == category_map[choice],
		Seat.booking_reference == None
	).first()

	if not seat:
		print("No seats available in this category.")
		return

	# Collect traveler info
	passport = input("Passport number: ").strip()
	first_name = input("First name: ").strip()
	last_name = input("Last name: ").strip()

	reference = generate_booking_reference(session)
	seat.booking_reference = reference
	traveler = Traveler(
		booking_reference=reference,
		passport_number=passport,
		first_name=first_name,
		last_name=last_name,
		seat_row=seat.row,
		seat_column=seat.position
	)
	session.add(traveler)

	try:
		session.commit()
		print(f"Booked {seat.seat_id} ({seat.category}) successfully. Reference: {reference}")
	except IntegrityError:
		session.rollback()
		print("Booking failed (duplicate reference).")


def free_seat(session):
	reference = input("Enter booking reference: ").strip().upper()
	seat = session.query(Seat).filter_by(booking_reference=reference).first()

	if not seat or seat.type != 'seat':
		print("Invalid reference.")
		return

	session.query(Traveler).filter_by(booking_reference=reference).delete()
	seat.booking_reference = None
	session.commit()
	print(f"Freed seat {seat.seat_id}.")


def show_booking_status(session):
	print("\nBooking Status:")
	rows = ['A', 'B', 'C', 'D', 'E', 'F']  # Assuming these are the only rows
	for row in rows:
		seats = session.query(Seat).filter_by(row=row).order_by(Seat.position).all()
		display = [f"{row}:"]
		for seat in seats:
			if seat.type == 'aisle':
				display.append(' ')
			elif seat.type == 'storage':
				display.append('S')
			else:
				display.append('R' if seat.booking_reference else 'F')
		print(' '.join(display))


def main():
	engine = create_engine('sqlite:///FC723_Final.db')
	Base.metadata.create_all(engine)
	Session = sessionmaker(bind=engine)
	session = Session()

	Seat.initialize_database(session)

	while True:
		show_menu()
		choice = input("Select option: ").strip()
		if choice == '1':
			check_availability(session)
		elif choice == '2':
			book_seat(session)
		elif choice == '3':
			free_seat(session)
		elif choice == '4':
			show_booking_status(session)
		elif choice == '5':
			print("Goodbye!")
			break
	session.close()


if __name__ == "__main__":
	main()