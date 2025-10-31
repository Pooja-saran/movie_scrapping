import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class IMDbScraper:
    def __init__(self, headless=True):
        self.setup_driver(headless)
        
    def setup_driver(self, headless=True):
        """Setup Chrome WebDriver"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("Chrome WebDriver initialized successfully")

    def scrape_top_250_movies(self):
        """Scrape IMDb Top 250 Movies list"""
        print("Starting to scrape IMDb Top 250 Movies...")
        
        try:
            # Navigate to IMDb Top 250 page
            url = "https://www.imdb.com/chart/top/"
            self.driver.get(url)
            
            # Wait for the page to load with multiple possible selectors
            print("Waiting for page to load...")
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "h3.ipc-title__text"))
                )
            except:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "cli-title"))
                )
            
            # Wait a bit more for dynamic content
            time.sleep(3)
            
            # Scroll to load all content
            self._scroll_page()
            
            movies_data = []
            
            # Try multiple selector strategies for movie rows
            selectors = [
                "li.ipc-metadata-list-summary-item",
                "tbody.lister-list tr",
                ".cli-children",
                "[data-testid='chart-layout-main-column'] li"
            ]
            
            movie_rows = []
            for selector in selectors:
                movie_rows = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if movie_rows:
                    print(f"Found {len(movie_rows)} movies using selector: {selector}")
                    break
            
            if not movie_rows:
                print("No movie rows found. Taking screenshot for debugging...")
                self.driver.save_screenshot("imdb_debug.png")
                print("Screenshot saved as imdb_debug.png")
                return []
            
            for index, movie_row in enumerate(movie_rows[:250], 1):  # Limit to 250
                try:
                    movie_data = self._extract_movie_data(movie_row, index)
                    if movie_data:
                        movies_data.append(movie_data)
                        if len(movies_data) % 25 == 0:
                            print(f"Progress: {len(movies_data)} movies scraped...")
                    
                except Exception as e:
                    print(f"Failed to extract data for movie {index}: {e}")
                    continue
            
            print(f"Successfully scraped {len(movies_data)} movies")
            return movies_data
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            # Take screenshot for debugging
            self.driver.save_screenshot("imdb_error.png")
            print("Screenshot saved as imdb_error.png for debugging")
            return []

    def _scroll_page(self):
        """Scroll the page to ensure all content is loaded"""
        print("Scrolling page to load all content...")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        for i in range(3):  # Limit to 3 scrolls
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                break
            last_height = new_height

    def _extract_movie_data(self, movie_row, rank):
        """Extract movie data from a single movie row with multiple fallback strategies"""
        try:
            # Try multiple title selectors
            title_selectors = [
                "h3.ipc-title__text",
                ".cli-title a",
                "td.titleColumn a",
                "[data-testid='title']",
                "a.ipc-title-link-wrapper"
            ]
            
            title = None
            for selector in title_selectors:
                try:
                    title_element = movie_row.find_element(By.CSS_SELECTOR, selector)
                    title_text = title_element.text
                    if title_text:
                        # Clean up title (remove ranking number if present)
                        if '. ' in title_text:
                            title = title_text.split('. ', 1)[1]
                        else:
                            title = title_text
                        break
                except:
                    continue
            
            if not title:
                return None

            # Try multiple year selectors
            year_selectors = [
                "span[data-testid='title-metadata'] span:first-child",
                ".cli-title-metadata span:first-child",
                "td.titleColumn span.secondaryInfo",
                ".cli-year",
                "[data-testid='ratingGroup--container'] + div span"
            ]
            
            year = "N/A"
            for selector in year_selectors:
                try:
                    year_element = movie_row.find_element(By.CSS_SELECTOR, selector)
                    year_text = year_element.text.strip('()')
                    if year_text and year_text.isdigit():
                        year = year_text
                        break
                except:
                    continue

            # Try multiple rating selectors
            rating_selectors = [
                "span.ipc-rating-star--rating",
                ".cli-ratings-container [data-testid='ratingGroup--rating']",
                "td.ratingColumn strong",
                ".ipc-rating-star",
                "[data-testid='ratingGroup--container'] span"
            ]
            
            rating = "N/A"
            for selector in rating_selectors:
                try:
                    rating_element = movie_row.find_element(By.CSS_SELECTOR, selector)
                    rating_text = rating_element.text
                    if rating_text and '.' in rating_text:
                        rating = rating_text
                        break
                except:
                    continue

            # Extract votes
            votes = "N/A"
            try:
                votes_selectors = [
                    "span.ipc-rating-star--voteCount",
                    ".cli-ratings-container [data-testid='ratingGroup--rating'] + span",
                    "td.ratingColumn strong::after"
                ]
                for selector in votes_selectors:
                    try:
                        votes_element = movie_row.find_element(By.CSS_SELECTOR, selector)
                        votes_text = votes_element.text.strip('()')
                        if votes_text:
                            votes = votes_text
                            break
                    except:
                        continue
            except:
                pass

            # Extract URL
            url = "N/A"
            try:
                url_selectors = [
                    "a.ipc-title-link-wrapper",
                    ".cli-title a",
                    "td.titleColumn a"
                ]
                for selector in url_selectors:
                    try:
                        link_element = movie_row.find_element(By.CSS_SELECTOR, selector)
                        url = link_element.get_attribute("href")
                        if url:
                            break
                    except:
                        continue
            except:
                pass
            
            return {
                'rank': rank,
                'title': title,
                'release_year': year,
                'imdb_rating': rating,
                'votes': votes,
                'url': url
            }
            
        except Exception as e:
            print(f"Error extracting movie data for rank {rank}: {e}")
            return None

    def save_to_csv(self, movies_data, filename="imdb_top_250.csv"):
        """Save scraped data to CSV file"""
        try:
            df = pd.DataFrame(movies_data)
            df.to_csv(filename, index=False, encoding='utf-8')
            print(f"Data saved to {filename}")
        except Exception as e:
            print(f"Failed to save data to CSV: {e}")

    def display_data(self, movies_data, num_samples=5):
        """Display sample of scraped data"""
        if not movies_data:
            print("No data to display")
            return
            
        df = pd.DataFrame(movies_data[:num_samples])
        print("\n" + "="*80)
        print("SAMPLE OF SCRAPED MOVIE DATA")
        print("="*80)
        print(df.to_string(index=False))
        print("="*80)

    def close(self):
        """Close the WebDriver"""
        if self.driver:
            self.driver.quit()
            print("WebDriver closed")

def main():
    """Main function to run the IMDb scraper"""
    scraper = None
    try:
        # Try with headless=False first to see what's happening
        scraper = IMDbScraper(headless=False)  # Set to False to see the browser
        
        # Scrape the data
        movies_data = scraper.scrape_top_250_movies()
        
        if movies_data:
            # Display sample data
            scraper.display_data(movies_data)
            
            # Save to files
            scraper.save_to_csv(movies_data)
            
            # Print summary
            print(f"\nSCRAPING SUMMARY:")
            print(f"Total movies scraped: {len(movies_data)}")
            
            # Calculate average rating
            ratings = []
            for movie in movies_data:
                try:
                    if movie['imdb_rating'] != 'N/A':
                        ratings.append(float(movie['imdb_rating']))
                except:
                    pass
            
            if ratings:
                print(f"Average IMDb rating: {sum(ratings)/len(ratings):.2f}")
            
            # Get year range
            years = []
            for movie in movies_data:
                try:
                    if movie['release_year'] != 'N/A' and movie['release_year'].isdigit():
                        years.append(int(movie['release_year']))
                except:
                    pass
            
            if years:
                print(f"Year range: {min(years)} - {max(years)}")
            
        else:
            print("No data was scraped. Check the screenshot for debugging.")
            
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Make sure you have ChromeDriver installed and in your PATH")
        
    finally:
        if scraper:
            scraper.close()

# Run the scraper
if __name__ == "__main__":
    main()