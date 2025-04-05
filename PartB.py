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

    __table_args__ = (
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
                        for idx, cell in enumerate(csv_row[1:], start=1):
                            seat_type = 'seat'
                            if cell == 'X':
                                seat_type = 'aisle'
                            elif cell == 'S':
                                seat_type = 'storage'

                            if seat_type == 'seat':
                                seat_id = cell.upper()  # Ensure uppercase
                            else:
                                seat_id = f"{row_label}-{idx}"

                            seat = Seat(
                                seat_id=seat_id,
                                row=row_label,
                                position=idx,
                                type=seat_type,
                                booking_reference=None
                            )
                            session.add(seat)
                session.commit()
            except IntegrityError:
                session.rollback()
                print("Error initializing database. Duplicate seats detected.")
            except Exception as e:
                session.rollback()
                print(f"Error initializing database: {e}")

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
        existing = session.query(Seat).filter_by(booking_reference=reference).first()
        if not existing:
            return reference

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
        status = 'available.' if seat.booking_reference is None else 'booked.'
        print(f"Seat {seat_id} is {status}")

def book_seat(session):
    seat_id = input("Enter seat number to book: ").strip().upper()
    seat = session.query(Seat).filter_by(seat_id=seat_id).first()

    if not seat:
        print("Invalid seat number.")
        return
    if seat.type != 'seat':
        print("Cannot book non-seat area.")
        return
    if seat.booking_reference is not None:
        print("Seat already booked.")
        return

    reference = generate_booking_reference(session)
    passport = input("Enter passport number: ").strip()
    first_name = input("Enter first name: ").strip()
    last_name = input("Enter last name: ").strip()

    traveler = Traveler(
        booking_reference=reference,
        passport_number=passport,
        first_name=first_name,
        last_name=last_name,
        seat_row=seat.row,
        seat_column=seat.position
    )
    seat.booking_reference = reference
    session.add(traveler)

    try:
        session.commit()
        print(f"Seat {seat_id} booked successfully. Reference: {reference}")
    except IntegrityError:
        session.rollback()
        print("Booking failed due to a duplicate reference. Please try again.")

def free_seat(session):
    reference = input("Enter booking reference to free: ").strip().upper()
    seat = session.query(Seat).filter_by(booking_reference=reference).first()

    if not seat:
        print("Invalid booking reference.")
        return
    if seat.type != 'seat':
        print("Cannot free non-seat area.")
        return

    traveler = session.query(Traveler).filter_by(booking_reference=reference).first()
    if traveler:
        session.delete(traveler)
    seat.booking_reference = None
    session.commit()
    print(f"Booking reference {reference} freed successfully.")

def show_booking_status(session):
    rows = session.query(Seat.row).distinct().order_by(Seat.row).all()
    rows = [row[0] for row in rows]

    print("\nCurrent Booking Status:")
    for row_label in rows:
        seats = session.query(Seat).filter_by(row=row_label).order_by(Seat.position).all()
        row_display = [row_label]
        for seat in seats:
            if seat.type == 'aisle':
                row_display.append(' ')  # Hide 'X'
            elif seat.type == 'storage':
                row_display.append('S')
            else:
                # Show 'R' if booked, 'F' if free
                row_display.append('R' if seat.booking_reference else 'F')
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