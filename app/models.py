from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.sql import func
from .database import Base

class Document(Base):
    __tablename__ = "scrapdata"

    id = Column(Integer, primary_key=True, index=True)
    
    # Basic car details
    make = Column(Text, nullable=False)          # Manufacturer of the car
    model = Column(Text, nullable=False)         # Model of the car
    price =Column(Text, nullable=True)              # Price of the car
    mileage = Column(Text, nullable=True)         # Mileage in kilometers or miles
    year = Column(Text, nullable=True)             # Year of manufacture

    # Location and dealer details
    location = Column(Text, nullable=True)       # Location of the car
    dealer_name = Column(Text, nullable=True)    # Name of the dealer
    dealer_rating = Column(Text, nullable=True)        # Rating of the dealer

    # URLs for car listing and images
    car_url = Column(Text, nullable=True)        # URL of the car listing
    image_url = Column(Text, nullable=True)      # URL for car images

    # Seller contact information
    seller_name = Column(Text, nullable=True)    # Name of the seller
    seller_email = Column(Text, nullable=True)   # Email of the seller
    seller_contact = Column(Text, nullable=True) # Contact number of the seller
    store_owner=Column(Text, nullable=True)
    # Car description and technical details
    description = Column(Text, nullable=True)           # Detailed description of the car
    engine_type = Column(Text, nullable=True)    # Type of engine (e.g., V6, Electric)
    transmission = Column(Text, nullable=True)   # Transmission type (e.g., Automatic, Manual)
    fuel_type = Column(Text, nullable=True)      # Fuel type (e.g., Petrol, Diesel, Electric)
    drivetrain = Column(Text, nullable=True)     # Drivetrain type (e.g., AWD, FWD, RWD)

    # Exterior and interior details
    exterior_color = Column(Text, nullable=True) # Exterior color of the car
    interior_color = Column(Text, nullable=True) # Interior color of the car
    seating_capacity = Column(Text, nullable=True)   # Number of seats in the car

    # Features of the car
    features = Column(Text, nullable=True)              # Features (e.g., Sunroof, Leather seats)
    
    # Timestamps and metadata
    created_at = Column(DateTime, server_default=func.now(), nullable=False)  # Auto-generated timestamp
    size = Column(Text, nullable=True)   # Size (e.g., file size or record size)
