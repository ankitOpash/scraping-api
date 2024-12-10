from app.database import engine, Base
from app.models import Document  # Ensure all models are imported

# Create all tables in the database
Base.metadata.create_all(bind=engine)