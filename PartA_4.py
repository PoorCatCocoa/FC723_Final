# Import necessary modules
import csv
from sqlalchemy import create_engine, Column, String, Integer, Enum, CheckConstraint
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError

# Create a base class for declarative class definitions
Base = declarative_base()


# Define the Seat class representing the 'Seats' table in the database
class Seat(Base):
	__tablename__ = 'Seats'

	# Columns definition
	seat_id = Column(String(10), primary_key=True)  # Unique seat identifier (e.g., '1A')
	row = Column(String(1), nullable=False)  # Row label (e.g., 'A', 'B')
	position = Column(Integer, nullable=False)  # Position index in the row
	type = Column(Enum('seat', 'aisle', 'storage', name='seat_type'), nullable=False)  # Seat type
	status = Column(Enum('F', 'R', name='seat_status'), nullable=True)  # Booking status (F=Free, R=Reserved)

	# Table-level constraint: If type is 'seat', status must be 'F' or 'R'
	__table_args__ = (
		CheckConstraint(
			"(type != 'seat') OR (status IN ('F', 'R'))",
			name='check_seat_status'
		),
	)

	# Static method to initialize the database with data from a CSV file
	@staticmethod
	def initialize_database(session, csv_filename='Seats.csv'):
		# Create all tables if they don't exist
		Base.metadata.create_all(session.bind)

		# Only populate data if the table is empty
		if session.query(Seat).count() == 0:
			try:
				with open(csv_filename, 'r') as f:
					csv_reader = csv.reader(f)
					for csv_row in csv_reader:
						row_label = csv_row[0]  # First element is the row label
						# Iterate over remaining elements (seats/aisles/storage in the row)
						for idx, cell in enumerate(csv_row[1:], start=1):
							# Determine seat type based on cell value
							seat_type = 'seat'
							if cell == 'X':
								seat_type = 'aisle'
							elif cell == 'S':
								seat_type = 'storage'

							# Generate seat_id: Use cell value for seats, else row-position (e.g., 'A-1')
							if seat_type == 'seat':
								seat_id = cell  # Seat ID is directly from CSV (e.g., '1A')
							else:
								seat_id = f"{row_label}-{idx}"

							# Create Seat instance and add to session
							seat = Seat(
								seat_id=seat_id,
								row=row_label,
								position=idx,
								type=seat_type,
								status='F' if seat_type == 'seat' else None  # Default status for seats
							)
							session.add(seat)
				session.commit()  # Commit all changes to the database
			except IntegrityError:
				session.rollback()
				print("Error initializing database. Duplicate seats detected.")
			except Exception as e:
				session.rollback()
				print(f"Error initializing database: {e}")


# Display the program menu to the user
def show_menu():
	print("\nMenu:")
	print("1. Check availability of seat")
	print("2. Book a seat")
	print("3. Free a seat")
	print("4. Show booking status")
	print("5. Exit program")


# Check if a seat is available for booking
def check_availability(session):
	seat_id = input("Enter seat number: ").strip().upper()
	seat = session.query(Seat).filter_by(seat_id=seat_id).first()

	if not seat:
		print("Invalid seat number.")
	elif seat.type != 'seat':
		print("This is not a bookable seat.")
	else:
		print(f"Seat {seat_id} is {'available.' if seat.status == 'F' else 'booked.'}")


# Book a seat if available
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
		seat.status = 'R'  # Set status to Reserved
		session.commit()
		print(f"Seat {seat_id} booked successfully.")


# Free a booked seat
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
		seat.status = 'F'  # Set status to Free
		session.commit()
		print(f"Seat {seat_id} freed successfully.")


# Display the current booking status in a grid format
def show_booking_status(session):
	# Get all distinct row labels sorted alphabetically
	rows = session.query(Seat.row).distinct().order_by(Seat.row).all()
	rows = [row[0] for row in rows]

	print("\nCurrent Booking Status:")
	for row_label in rows:
		# Get all seats in the current row, ordered by position
		seats = session.query(Seat).filter_by(row=row_label).order_by(Seat.position).all()
		row_display = [row_label]  # Start with row label (e.g., 'A')
		for seat in seats:
			if seat.type == 'aisle':
				row_display.append('X')  # Represent aisle with 'X'
			elif seat.type == 'storage':
				row_display.append('S')  # Represent storage with 'S'
			else:
				# Show 'F' (Free), 'R' (Reserved), or default to 'F' if status is None
				row_display.append(seat.status if seat.status else 'F')
		# Print the row as a comma-separated string
		print(','.join(row_display))


# Main function to run the program
def main():
	# Set up SQLite database engine and connect to 'FC723_Final.db'
	engine = create_engine('sqlite:///FC723_Final.db')
	Base.metadata.create_all(engine)  # Ensure tables are created
	Session = sessionmaker(bind=engine)
	session = Session()  # Create a new session

	# Initialize database with data from CSV
	Seat.initialize_database(session)

	# Main loop for user interaction
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

	session.close()  # Close the session after exiting the loop


# Execute the main function when the script is run
if __name__ == "__main__":
	main()