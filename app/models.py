from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.sql import func
from .database import Base

class Document(Base):
    __tablename__ = "scrapdata"

    id = Column(Integer, primary_key=True, index=True)
    
    # Basic car details
    make = Column(String(255), nullable=False)          # Manufacturer of the car
    model = Column(String(255), nullable=False)         # Model of the car
    price = Column(Float, nullable=False)               # Price of the car
    mileage = Column(Integer, nullable=False)           # Mileage in kilometers or miles
    year = Column(Integer, nullable=False)              # Year of manufacture

    # Location and dealer details
    location = Column(String(255), nullable=True)       # Location of the car
    dealer_name = Column(String(255), nullable=True)    # Name of the dealer
    dealer_rating = Column(Float, nullable=True)        # Rating of the dealer

    # URLs for car listing and images
    car_url = Column(String(255), nullable=True)        # URL of the car listing
    image_url = Column(String(255), nullable=True)      # URL for car images

    # Seller contact information
    seller_name = Column(String(255), nullable=True)    # Name of the seller
    seller_email = Column(String(255), nullable=True)   # Email of the seller
    seller_contact = Column(String(255), nullable=True) # Contact number of the seller

    # Car description and technical details
    description = Column(Text, nullable=True)           # Detailed description of the car
    engine_type = Column(String(255), nullable=True)    # Type of engine (e.g., V6, Electric)
    transmission = Column(String(255), nullable=True)   # Transmission type (e.g., Automatic, Manual)
    fuel_type = Column(String(255), nullable=True)      # Fuel type (e.g., Petrol, Diesel, Electric)
    drivetrain = Column(String(255), nullable=True)     # Drivetrain type (e.g., AWD, FWD, RWD)

    # Exterior and interior details
    exterior_color = Column(String(255), nullable=True) # Exterior color of the car
    interior_color = Column(String(255), nullable=True) # Interior color of the car
    seating_capacity = Column(Integer, nullable=True)   # Number of seats in the car

    # Features of the car
    features = Column(Text, nullable=True)              # Features (e.g., Sunroof, Leather seats)
    
    # Timestamps and metadata
    created_at = Column(DateTime, server_default=func.now(), nullable=False)  # Auto-generated timestamp
    size = Column(Integer, default=0, nullable=False)   # Size (e.g., file size or record size)
