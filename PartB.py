# This script manages seat bookings for an airline using a SQLite database.
# It uses SQLAlchemy for ORM and provides a CLI menu for user interactions.

# Import necessary modules
import csv  # For reading CSV files to initialize seat data
import random  # For generating booking references
import string  # For string operations related to booking references
from sqlalchemy import create_engine, Column, String, Integer, Enum, CheckConstraint, ForeignKey  # Database ORM components
from sqlalchemy.orm import declarative_base, sessionmaker, relationship  # ORM utilities
from sqlalchemy.exc import IntegrityError  # To handle database integrity errors

# Initialize SQLAlchemy base class for ORM models
Base = declarative_base()


class Seat(Base):
    """ORM model representing a seat, aisle, or storage area in the aircraft."""
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
        """Initializes the database with seat data from a CSV file."""
        Base.metadata.create_all(session.bind)

        if session.query(Seat).count() == 0:
            try:
                with open(csv_filename, 'r') as f:
                    csv_reader = csv.reader(f)
                    for csv_row in csv_reader:
                        row_label = csv_row[0]
                        positions = csv_row[1:]

                        if row_label in ['A', 'F']:
                            category = 'window'
                        elif row_label in ['B', 'E']:
                            category = 'middle'
                        elif row_label in ['C', 'D']:
                            category = 'aisle'
                        else:
                            category = 'middle'

                        for idx, cell in enumerate(positions, start=1):
                            seat_type = 'seat'
                            if cell == 'X':
                                seat_type = 'aisle'
                            elif cell == 'S':
                                seat_type = 'storage'

                            # Corrected line: use idx for seat_id when it's a seat
                            seat_id = f"{row_label}{idx}" if seat_type == 'seat' else f"{row_label}-{idx}"

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
	"""ORM model representing a traveler linked to a booked seat."""
	__tablename__ = 'Travelers'
	# Primary key and foreign key to Seat's booking_reference
	booking_reference = Column(String(8), ForeignKey('Seats.booking_reference'), primary_key=True)
	passport_number = Column(String(20), nullable=False)  # Traveler's passport ID
	first_name = Column(String(50), nullable=False)  # Traveler's first name
	last_name = Column(String(50), nullable=False)  # Traveler's last name
	seat_row = Column(String(1), nullable=False)  # Booked seat's row (redundant but convenient)
	seat_column = Column(Integer, nullable=False)  # Booked seat's position


def generate_booking_reference(session):
	"""Generates a unique 8-character alphanumeric booking reference.

	Design Logic:
	- Character Set: A-Z (uppercase) and 0-9 (36 total characters).
	- Collision Handling: Guarantees uniqueness via database checks.
	- Uniqueness: 36^8 (~2.8 trillion) combinations minimize collision risk.

	Workflow:
	1. Generate random 8-character string
	2. Verify uniqueness against existing booking references in the database
	3. Repeat until unique reference is found

	Performance Notes:
	- Optimized for low collision probability (typically 1 iteration needed)
	- Requires active database connection for validation
	"""

	# Define allowed characters: uppercase letters + digits
	chars = string.ascii_uppercase + string.digits  # 26 letters + 10 digits = 36 chars

	# Infinite loop ensures we never return a duplicate
	while True:
		# Generate random 8-character combination
		reference = ''.join(random.choices(chars, k=8))  # Example: "A3B9CZ7Q"

		# Database uniqueness check
		# Returns None if reference doesn't exist in Seat.booking_reference
		existing = session.query(Seat).filter_by(booking_reference=reference).first()

		if not existing:  # Found unique reference
			return reference
	# Implicit else: loop continues to generate new reference


def show_menu():
	"""Displays the CLI menu options."""
	print("\nMenu:")
	print("1. Check seat availability")
	print("2. Book a seat")
	print("3. Free a seat")
	print("4. Show booking status")
	print("5. Exit")


def check_availability(session):
	"""Checks if a specific seat is available."""
	seat_id = input("For example, seat a12 or 12a please type as a12a\nEnter seat number: ").strip().upper()  # Normalize input (e.g., 'a3' -> 'A3')
	seat = session.query(Seat).filter_by(seat_id=seat_id).first()  # Query database

	if not seat or seat.type != 'seat':
		print("Invalid seat number.")  # Seat doesn't exist or isn't bookable
	else:
		status = 'available' if not seat.booking_reference else 'booked'
		print(f"Seat {seat_id} ({seat.category}) is {status}.")


def book_seat(session):
	"""Books a seat based on user's preferred category and collects traveler info."""
	print("\nChoose seat type:")
	print("1. Window (Rows A/F)")
	print("2. Middle (Rows B/E)")
	print("3. Aisle (Rows C/D)")
	choice = input("Choice (1-3): ").strip()

	# Map user choice to seat category
	category_map = {'1': 'window', '2': 'middle', '3': 'aisle'}
	if choice not in category_map:
		print("Invalid choice.")
		return

	# Find first available seat in the selected category
	seat = session.query(Seat).filter(
		Seat.category == category_map[choice],
		Seat.booking_reference == None
	).first()

	if not seat:
		print("No seats available in this category.")
		return

	# Collect traveler details
	passport = input("Passport number: ").strip()
	first_name = input("First name: ").strip()
	last_name = input("Last name: ").strip()

	# Generate and assign booking reference
	reference = generate_booking_reference(session)
	seat.booking_reference = reference

	# Create Traveler record linked to the seat
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
		session.commit()  # Save changes
		print(f"Booked {seat.seat_id} ({seat.category}) successfully. Reference: {reference}")
	except IntegrityError:
		session.rollback()  # Handle rare duplicate reference collision
		print("Booking failed (duplicate reference).")


def free_seat(session):
	"""Frees a booked seat using its booking reference."""
	reference = input("Enter booking reference: ").strip().upper()
	seat = session.query(Seat).filter_by(booking_reference=reference).first()

	if not seat or seat.type != 'seat':
		print("Invalid reference.")
		return

	# Delete traveler record and unlink booking reference
	session.query(Traveler).filter_by(booking_reference=reference).delete()
	seat.booking_reference = None
	session.commit()
	print(f"Freed seat {seat.seat_id}.")


def show_booking_status(session):
	"""Displays a grid of seat statuses (F=free, R=reserved, S=storage, spaces=aisles)."""
	print("\nBooking Status:")
	rows = ['A', 'B', 'C', 'D', 'E', 'F']  # Expected aircraft rows
	for row in rows:
		seats = session.query(Seat).filter_by(row=row).order_by(Seat.position).all()
		display = [f"{row}:"]  # Row label (e.g., "A:")
		for seat in seats:
			if seat.type == 'aisle':
				display.append(' ')  # Represent aisles with spaces
			elif seat.type == 'storage':
				display.append('S')  # Storage areas marked 'S'
			else:
				# 'R' for reserved, 'F' for free
				display.append('R' if seat.booking_reference else 'F')
		print(' '.join(display))  # Print row status as a string


def main():
	"""Main function to initialize database and handle user input."""
	# Configure database connection
	engine = create_engine('sqlite:///FC723_Final.db')  # SQLite database file
	Base.metadata.create_all(engine)  # Create tables if missing
	Session = sessionmaker(bind=engine)
	session = Session()  # Start a new database session

	# Initialize seat data from CSV
	Seat.initialize_database(session)

	# CLI loop
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
	session.close()  # Cleanup database connection


if __name__ == "__main__":
	main()  # Execute only if run as a script