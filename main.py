import agentql
import csv
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

load_dotenv()

agentql_api_key = os.getenv("AGENTQL_API_KEY")

scraping_active = True

# List to keep track of all active scraping processes
active_processes = []

# Initialize agentql
print("agentql_api_key", agentql_api_key)

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
log_queue = queue.Queue()

# Connection Manager for WebSocket handling
class ConnectionManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        """Accept and store the WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        """Remove the disconnected WebSocket."""
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        """Send a message to all active WebSocket connections."""
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error sending message: {e}")

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

def save_to_csv_realtime(product, filename='car_listings.csv'):
    """Append a single product's data to the CSV file."""
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=product.keys())
        # Write headers only if the file is empty
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow(product)
        
        
def save_to_csv_and_db(product, db: Session, filename='car_listings.csv'):
    """Save data to CSV and database."""
    # Save to CSV
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=product.keys())
        if file.tell() == 0:
            writer.writeheader()
        writer.writerow(product)

    # Save to database
    db_product = Document(**product)
    db.add(db_product)
    db.commit()

def scrape_ecommerce_realtime(url, max_pages):
    """Scrape an e-commerce website for car listings and details."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = agentql.wrap(browser.new_page())

        page.goto(url)
        print("Loading first page...")
        log_queue.put("Loading first page...")

        page_count = 0

        while scraping_active:
            page.wait_for_page_ready_state()

            print(f"Fetching product listings from page {page_count + 1}...")
            log_queue.put(f"Fetching product listings from page {page_count + 1}...")
            response = page.query_data(QUERY_LISTINGS)

            if response.get("products"):
                for product in response["products"]:
                    product_details = product.copy()
                    if product.get("car_url"):
                        try:
                            print(f"Visiting detail page: {product['car_url']}")
                            log_queue.put(f"Visiting detail page: {product['car_url']}")
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
                                print("No additional details found for this product.")
                                log_queue.put(f"No additional details found for this product.")
                        except Exception as e:
                            print(f"Error fetching details for {product['car_url']}: {e}")
                            log_queue.put(f"Error fetching details for {product['car_url']}: {e}")

                    # Save to CSV and DB should be called with a new session
                    with get_db() as db:
                        save_to_csv_and_db(product_details, db)

            page_count += 1

            if page_count >= max_pages:
                print(f"Reached the specified page limit of {max_pages}.")
                break

            try:
                next_button = page.locator("text='Next'")
                if next_button.is_visible():
                    next_button.click()
                    print("Navigating to the next page...")
                    log_queue.put(f"Navigating to the next page...")
                else:
                    print("No more pages. Ending pagination.")
                    log_queue.put(f"No more pages. Ending pagination.")
                    break
            except Exception as e:
                print(f"Pagination ended with error: {e}")
                log_queue.put(f"Pagination ended with error: {e}")
                break

        browser.close()
        print("Scraping completed.")
        log_queue.put(f"Scraping completed.")

@app.get("/")
def read_root():
    return {"message": "Welcome to the opash Web Scraping API"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time logging."""
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.post("/api/scrape")
async def scrape_endpoint(background_tasks: BackgroundTasks, url: str, max_pages: int):
    """Endpoint to start scraping in the background."""
    try:
        if any(p.is_alive() for p in active_processes):
            raise HTTPException(status_code=400, detail="Scraping is already running.")
        
        scraping_process = multiprocessing.Process(target=scrape_ecommerce_realtime, args=(url, max_pages))
        scraping_process.start()
        active_processes.append(scraping_process)
        
        return {"message": "Scraping started in the background."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop-scraping")
async def stop_scraping():
    """Stop all scraping processes safely."""
    global scraping_active
    scraping_active = False
    log_queue.put("Scraping has been stopped.")
    
    for process in active_processes:
        if process.is_alive():
            process.terminate()
            process.join()
    
    active_processes.clear()
    
    return {"message": "All scraping processes stopped successfully."}

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

@app.get("/api/download")
async def download_csv():
    """API endpoint to download the CSV file."""
    file_path = "car_listings.csv"
    return FileResponse(file_path, filename="car_listings.csv")

if __name__ == "__main__":
    # This ensures that the multiprocessing code is only executed when the script is run directly
    multiprocessing.set_start_method('spawn', force=True)
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")