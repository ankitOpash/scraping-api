import agentql
import csv
import logging
from playwright.sync_api import sync_playwright

from sqlalchemy.orm import Session
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.responses import FileResponse
import asyncio
import sys
import multiprocessing
import threading
import queue
from app.database import get_db
from app.models import Document
import os
from dotenv import load_dotenv


db_lock = multiprocessing.Lock()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

agentql_api_key = os.getenv("AGENTQL_API_KEY")

scraping_active = True

# List to keep track of all active scraping processes
active_processes = []

# Initialize agentql
#logger.info(f"agentql_api_key {agentql_api_key}")

# Set the appropriate event loop policy for Windows
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(title="Scrap Management System API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex="https?://.*",  # Match any HTTP or HTTPS origin
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Queue for log messages
log_queue = multiprocessing.Queue()

# Connection Manager for WebSocket handling
class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        """Accept and store the WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("WebSocket connection established.")

    def disconnect(self, websocket: WebSocket):
        """Remove the disconnected WebSocket."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            # logger.info("WebSocket connection closed.")

    async def broadcast(self, message: str):
        """Send a message to all active WebSocket connections."""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                # logger.error(f"Error sending message: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

QUERY_LISTINGS = """
{
    products[] {
        make
        model
        price
        mileage
        year
        location
        dealer_name
        dealer_rating
        car_url
        image_url
        seller_name
        seller_email
        seller_contact
    }
}
"""

# Query for product details with refined fields
QUERY_DETAILS = """
{
    productDetails {
        description
        engine_type
        transmission
        fuel_type
        drivetrain
        exterior_color
        interior_color
        seating_capacity
        features[]
    }
}
"""

# def save_to_csv_and_db(product, db, filename='car_listings.csv'):
#     """Save data to CSV and database."""
#     with open(filename, mode='a', newline='', encoding='utf-8') as file:
#         writer = csv.DictWriter(file, fieldnames=product.keys())
#         if file.tell() == 0:
#             writer.writeheader()
#         writer.writerow(product)

#     db_product = Document(**product)
#     db.add(db_product)
#     db.commit()
def save_to_csv_and_db(product, filename='car_listings.csv'):
    """Save data to CSV and database."""
    # Save to CSV
    try:
        with open(filename, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=product.keys())
            if file.tell() == 0:
                writer.writeheader()
            writer.writerow(product)
    except Exception as e:
        logger.error(f"Error writing to CSV: {e}")

    # Save to Database
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        db_product = Document(**product)
        db.add(db_product)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error inserting product into database: {e}")
    finally:
        db.close()

        

def scrape_ecommerce_realtime(url, max_pages, log_queue):
    """Scrape an e-commerce website for car listings and details."""
   
    global scraping_active
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = agentql.wrap(browser.new_page())

            page.goto(url)
            log_queue.put("Loading first page...")
            logger.info("Loading first page...")

            page_count = 0

            while scraping_active and page_count < max_pages:
                page.wait_for_page_ready_state()

                log_queue.put(f"Fetching product listings from page {page_count + 1}...")
                logger.info(f"Fetching product listings from page {page_count + 1}...")
                response = page.query_data(QUERY_LISTINGS)

                if response.get("products"):
                    for product in response["products"]:
                        product_details = product.copy()
                        if product.get("car_url"):
                            try:
                                log_queue.put(f"Visiting detail page: {product['car_url']}")
                                logger.info(f"Visiting detail page: {product['car_url']}")
                                detail_page = agentql.wrap(browser.new_page())
                                detail_page.goto(product["car_url"])
                                detail_response = detail_page.query_data(QUERY_DETAILS)
                                detail_page.close()

                                if detail_response.get("productDetails"):
                                    product_details.update(detail_response["productDetails"])
                                    seller_name = detail_response["productDetails"].get("seller_name", "").strip()
                                    if seller_name.lower() != "owner":
                                        product_details["seller_name"] = seller_name
                                    else:
                                        product_details["seller_name"] = "Unknown"
                                else:
                                    log_queue.put("No additional details found for this product.")
                                    logger.info("No additional details found for this product.")
                            except Exception as e:
                                log_queue.put(f"Error fetching details for {product['car_url']}: {e}")
                                logger.error(f"Error fetching details for {product['car_url']}: {e}")

                        # Use the context manager to get a database session
                        with get_db() as db:
                            save_to_csv_and_db(product_details, db)

                page_count += 1

                if page_count >= max_pages:
                    log_queue.put(f"Reached the specified page limit of {max_pages}.")
                    logger.info(f"Reached the specified page limit of {max_pages}.")
                    break

                try:
                    next_button = page.locator("text='Next'")
                    if next_button.is_visible():
                        next_button.click()
                        log_queue.put("Navigating to the next page...")
                        logger.info("Navigating to the next page...")
                    else:
                        log_queue.put("No more pages. Ending pagination.")
                        logger.info("No more pages. Ending pagination.")
                        break
                except Exception as e:
                    log_queue.put(f"Pagination ended with error: {e}")
                    logger.error(f"Pagination ended with error: {e}")
                    break

            browser.close()
            log_queue.put("Scraping completed.")
            logger.info("Scraping completed.")
    except Exception as e:
        log_queue.put(f"Error during scraping: {e}")
        logger.error(f"Error during scraping: {e}")

async def consume_logs():
    """Consume logs from the queue and broadcast them."""
    while True:
        if not log_queue.empty():
            message = log_queue.get()
            await manager.broadcast(message)
        await asyncio.sleep(0.1)

@app.on_event("startup")
async def startup_event():
    """Start the log consumer on application startup."""
    asyncio.create_task(consume_logs())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time logging."""
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        
@app.get("/")
def read_root():
    return {"message": "Welcome to the opash Web Scraping API"}

@app.post("/api/scrape")
async def scrape_endpoint(url: str, max_pages: int):
    """Endpoint to start scraping in the background."""
    global scraping_active
    try:
        if any(p.is_alive() for p in active_processes):
            raise HTTPException(status_code=400, detail="Scraping is already running.")
        
        # Reset the scraping_active flag
        scraping_active = True
        
        # Start the scraping process
        scraping_process = multiprocessing.Process(target=scrape_ecommerce_realtime, args=(url, max_pages, log_queue))
        scraping_process.start()
        active_processes.append(scraping_process)
        
        return {"message": "Scraping started in the background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop-scraping")
async def stop_scraping():
    """Stop all scraping processes safely."""
    global scraping_active
    if not any(p.is_alive() for p in active_processes):
        return {"message": "No scraping processes are currently running."}

    scraping_active = False
    log_queue.put("Scraping has been stopped.")
    
    for process in active_processes:
        if process.is_alive():
            logger.info(f"Terminating process {process.pid}")
            process.terminate()
            process.join(timeout=5)  # Wait for up to 5 seconds for the process to terminate
            if process.is_alive():
                logger.warning(f"Process {process.pid} did not terminate, killing it.")
                process.kill()  # Forcefully kill the process if it didn't terminate
                process.join()  # Ensure the process is reaped
            logger.info(f"Process {process.pid} terminated.")
    
    active_processes.clear()
    
    return {"message": "All scraping processes stopped successfully."}

@app.get("/api/download")
async def download_csv():
    """API endpoint to download the CSV file."""
    file_path = "car_listings.csv"
    return FileResponse(file_path, filename="car_listings.csv")

# New endpoint to fetch data from the database

@app.get("/api/get-data")
async def get_data_from_db():
    """Endpoint to retrieve data from the database."""
    with get_db() as db:
        try:
            data = db.query(Document).all()
            return {"data": [item.__dict__ for item in data]}
        except Exception as e:
            logger.error(f"Error reading data: {e}")
            raise HTTPException(status_code=500, detail="Failed to fetch data.")

if __name__ == "__main__":
    # Set the start method for multiprocessing
    if sys.platform.startswith('win'):
        multiprocessing.set_start_method('spawn', force=True)
    else:
        multiprocessing.set_start_method('fork', force=True)
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
# if __name__ == "__main__":
#     # This ensures that the multiprocessing code is only executed when the script is run directly
#     multiprocessing.set_start_method('spawn')
#     import uvicorn
#     uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")