import agentql
import csv
from playwright.sync_api import sync_playwright

# Query for listings with additional seller details
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

def scrape_ecommerce_realtime(url):
    """Scrape an e-commerce website for car listings and details."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = agentql.wrap(browser.new_page())

        # Navigate to the URL
        page.goto(url)
        print("Loading first page...")

        while True:
            page.wait_for_page_ready_state()

            # Fetch product listings from the current page
            print("Fetching product listings...")
            response = page.query_data(QUERY_LISTINGS)

            if response.get("products"):
                for product in response["products"]:
                    product_details = product.copy()  # Create a copy to avoid overwriting data
                    if product.get("car_url"):
                        try:
                            print(f"Visiting detail page: {product['car_url']}")
                            # Open detail page and fetch additional details
                            detail_page = agentql.wrap(browser.new_page())
                            detail_page.goto(product["car_url"])
                            detail_response = detail_page.query_data(QUERY_DETAILS)
                            detail_page.close()

                            # Merge additional details into the product record
                            if detail_response.get("productDetails"):
                                product_details.update(detail_response["productDetails"])
                            else:
                                print("No additional details found for this product.")
                        except Exception as e:
                            print(f"Error fetching details for {product['car_url']}: {e}")

                    # Save the product data to CSV in real time
                    save_to_csv_realtime(product_details)

            # Check for the "Next" button or pagination link
            try:
                next_button = page.locator("text='Next'")  # Adjust selector to match the site's pagination
                if next_button.is_visible():
                    next_button.click()
                    print("Navigating to the next page...")
                else:
                    print("No more pages. Ending pagination.")
                    break
            except Exception as e:
                print(f"Pagination ended with error: {e}")
                break

        browser.close()
        print("Scraping completed.")

if __name__ == "__main__":
    # Start URL provided by the user
    start_url = input("Enter the e-commerce URL to scrape: ")
    scrape_ecommerce_realtime(start_url)
