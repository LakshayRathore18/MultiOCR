import requests
from bs4 import BeautifulSoup
import re

def scrape_selenium_multipage(url, output_file="data/scraped_sanskrit.txt", max_pages=5, append=True, chapter=None):
    """Scrape multiple pages with Selenium - uses next button navigation
    
    Args:
        url: Website URL to scrape
        output_file: Output file path
        max_pages: Number of pages to scrape
        append: If True, append to existing file. If False, overwrite.
        chapter: Chapter number to select (optional)
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
        from pathlib import Path
        
        print(f"Starting multi-page scrape: {url}")
        print(f"Max pages to scrape: {max_pages}")
        print(f"Append mode: {append}")
        if chapter:
            print(f"Chapter to select: {chapter}")
        print()
        
        # Read existing texts if appending
        existing_texts = []
        if append and Path(output_file).exists():
            print(f"📖 Reading existing file: {output_file}")
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing_texts = [line.strip() for line in f.readlines() if line.strip()]
                print(f"✅ Found {len(existing_texts)} existing texts")
            except Exception as e:
                print(f"⚠️  Could not read existing file: {e}")
        
        # Try Chrome first
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        
        try:
            driver = webdriver.Chrome(options=options)
        except:
            print("Chrome not found, trying Edge...")
            driver = webdriver.Edge()
        
        driver.get(url)
        time.sleep(3)
        
        # Select chapter if specified
        if chapter:
            print(f"\n=== Selecting Chapter {chapter} ===\n")
            try:
                # Find all select dropdowns
                selects = driver.find_elements(By.TAG_NAME, "select")
                print(f"Found {len(selects)} dropdown(s)")
                
                # Look for the chapter/adhyaya dropdown (usually the second one)
                chapter_dropdown = None
                for i, sel in enumerate(selects):
                    try:
                        options_list = sel.find_elements(By.TAG_NAME, "option")
                        print(f"  Dropdown {i+1}: {len(options_list)} options")
                        # Chapter dropdown usually has many options
                        if len(options_list) > 10:
                            chapter_dropdown = sel
                            print(f"  ✓ Using dropdown {i+1} as chapter selector")
                            break
                    except:
                        continue
                
                if chapter_dropdown:
                    # Get options and select the chapter
                    options_list = chapter_dropdown.find_elements(By.TAG_NAME, "option")
                    
                    if chapter <= len(options_list):
                        option_to_select = options_list[chapter - 1]  # 0-indexed
                        chapter_name = option_to_select.text
                        print(f"Selecting: {chapter_name[:50]}...")
                        option_to_select.click()
                        time.sleep(2)  # Wait for page to load
                        print(f"✅ Chapter {chapter} selected")
                    else:
                        print(f"⚠️  Chapter {chapter} not found (only {len(options_list)} chapters available)")
                else:
                    print("⚠️  Could not find chapter dropdown")
            
            except Exception as e:
                print(f"⚠️  Error selecting chapter: {e}")
        
        all_texts = list(existing_texts)  # Start with existing texts
        pages_scraped = 0
        
        print("\n=== Scraping pages using next button (>) navigation ===\n")
        
        while pages_scraped < max_pages:
            try:
                print(f"[Page {pages_scraped + 1}] Extracting content...")
                
                # Extract all Sanskrit text from current page
                texts = _extract_sanskrit_from_page(driver)
                print(f"   ✓ Extracted {len(texts)} texts")
                all_texts.extend(texts)
                pages_scraped += 1
                
                if pages_scraped >= max_pages:
                    print(f"\n✅ Reached maximum pages ({max_pages})")
                    break
                
                # Find and click the NEXT button (>)
                # The button is: <input name="nextAdhi" value=">" onclick="changeAdhi(...)" />
                next_button = None
                try:
                    # Selectors for the next button
                    selectors = [
                        "//input[@name='nextAdhi']",                 # Exact match for next button
                        "//input[@value='>' and @name='nextAdhi']",  # Even more specific
                        "//input[@onclick='changeAdhi(document.pageForm, document.pageForm.selAdhi, this);']",  # By onclick
                    ]
                    
                    for selector in selectors:
                        try:
                            next_button = driver.find_element(By.XPATH, selector)
                            if next_button and next_button.is_enabled():
                                break
                        except:
                            continue
                    
                    if next_button and next_button.is_enabled():
                        print(f"   ➜ Clicking next page button...")
                        next_button.click()
                        time.sleep(2)  # Wait for page to load
                    else:
                        print(f"   ⚠️  No more pages available (next button disabled)")
                        break
                
                except Exception as e:
                    print(f"   ❌ Error clicking next button: {e}")
                    break
            
            except KeyboardInterrupt:
                print("\n⏸️  Scraping interrupted by user")
                break
            except Exception as e:
                print(f"   ❌ Error on page {pages_scraped + 1}: {e}")
                break
        
        driver.quit()
        
        # Remove duplicates while preserving order
        unique_texts = list(dict.fromkeys(all_texts))
        
        # Save to file
        if unique_texts:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(unique_texts))
            
            new_texts_count = len(unique_texts) - len(existing_texts)
            
            print(f"\n{'='*50}")
            print(f"✅ Scraped {pages_scraped} pages")
            print(f"✅ Extracted {len(all_texts)} total texts (including existing)")
            print(f"✅ Previous texts: {len(existing_texts)}")
            print(f"✅ New texts added: {new_texts_count}")
            print(f"✅ Total unique texts: {len(unique_texts)}")
            print(f"✅ Saved to {output_file}")
            print(f"{'='*50}")
            return unique_texts
        else:
            print("❌ No texts extracted")
            return []
            
    except ImportError:
        print("❌ Selenium not installed: pip install selenium")
        return []
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def _extract_sanskrit_from_page(driver):
    """Extract all Sanskrit text from current page"""
    from selenium.webdriver.common.by import By
    
    all_spans = driver.find_elements(By.TAG_NAME, "span")
    
    texts = []
    for span in all_spans:
        text = span.text.strip()
        # Check if text contains Devanagari characters (U+0900 to U+097F)
        has_devanagari = any('\u0900' <= char <= '\u097F' for char in text)
        
        if text and len(text) > 5 and has_devanagari:
            texts.append(text)
    
    return texts

if __name__ == "__main__":
    url = "https://niimh.nic.in/ebooks/ecaraka/?mod=read"
    
    print("🔄 Multi-page Sanskrit Text Scraper")
    print("="*50)
    print()
    
    # Interactive input for chapter number
    chapter = None
    while chapter is None:
        try:
            user_input = input("Which chapter do you want to scrape? (default 2): ").strip()
            if user_input == "":
                chapter = 2
            else:
                chapter = int(user_input)
                if chapter <= 0:
                    print("❌ Please enter a chapter number greater than 0")
                    chapter = None
        except ValueError:
            print("❌ Invalid input. Please enter a chapter number.")
        except KeyboardInterrupt:
            print("\n⏸️  Cancelled by user")
            exit(0)
    
    # Interactive input for number of pages
    max_pages = None
    while max_pages is None:
        try:
            user_input = input("How many pages do you want to scrape? (default 56): ").strip()
            if user_input == "":
                max_pages = 56
            else:
                max_pages = int(user_input)
                if max_pages <= 0:
                    print("❌ Please enter a number greater than 0")
                    max_pages = None
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\n⏸️  Cancelled by user")
            exit(0)
    
    print(f"\n✅ Will scrape chapter {chapter} for {max_pages} pages")
    print()
    
    # Always append (don't overwrite)
    texts = scrape_selenium_multipage(url, max_pages=max_pages, append=True, chapter=chapter)
    
    if texts:
        print(f"\n✨ First 3 texts in file:")
        for i, text in enumerate(texts[:3], 1):
            preview = text[:80] + "..." if len(text) > 80 else text
            print(f"{i}. {preview}")







