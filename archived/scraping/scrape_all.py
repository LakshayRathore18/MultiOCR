#!/usr/bin/env python3
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

URL = "https://niimh.nic.in/ebooks/ecaraka/?mod=read"
OUTPUT_FILE = "postocr/data/scraped_sanskrit.txt"

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def extract_sanskrit_from_page(driver):
    spans = driver.find_elements(By.TAG_NAME, "span")
    texts = []

    for span in spans:
        text = span.text.strip()
        if len(text) > 5 and any('\u0900' <= c <= '\u097F' for c in text):
            texts.append(text)

    return texts


def reached_pushpika(driver):
    """Check selected page option text"""
    try:
        page_select = driver.find_element(By.NAME, "selAdhi")
        selected = page_select.find_element(By.CSS_SELECTOR, "option:checked")
        return "पुष्पिका" in selected.text.strip()
    except:
        return False


def select_chapter(driver, chapter_number):
    """Select chapter using dropdown"""
    time.sleep(1)  # Wait before finding new elements
    selects = driver.find_elements(By.TAG_NAME, "select")

    chapter_select = None
    for sel in selects:
        options = sel.find_elements(By.TAG_NAME, "option")
        if len(options) > 10:  # chapter dropdown heuristic
            chapter_select = sel
            break

    if not chapter_select:
        raise RuntimeError("Chapter dropdown not found")

    # Get fresh options before clicking
    options = chapter_select.find_elements(By.TAG_NAME, "option")

    if chapter_number > len(options):
        raise ValueError(f"Chapter {chapter_number} not available (only {len(options)} chapters)")

    # Use Select for more reliable selection
    Select(chapter_select).select_by_index(chapter_number - 1)
    print(f"   ✔ Selected chapter {chapter_number}")
    time.sleep(3)  # Wait longer for chapter content to load


def select_sthana(driver, sthana_value=1):
    """Select sthana (section) by value, e.g., सूत्रस्थानम् has value=1"""
    try:
        sthana_select = Select(driver.find_element(By.NAME, "selSthana"))
        sthana_select.select_by_value(str(sthana_value))
        time.sleep(3)  # wait for page to update after selection
        section_name = "सूत्रस्थानम्" if sthana_value == 1 else f"value={sthana_value}"
        print(f"🔹 Selected sthana with value {sthana_value} ({section_name})")
    except Exception as e:
        print(f"❌ Failed to select sthana: {e}")


# --------------------------------------------------
# Main scraper
# --------------------------------------------------

def scrape_all_chapters(start_chapter=1, end_chapter=8):
    Path("postocr/data").mkdir(parents=True, exist_ok=True)

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)
    driver.get(URL)
    time.sleep(3)

    # First select सूत्रस्थानम् (value=1) from selSthana dropdown
    select_sthana(driver, sthana_value=1)

    # Get initial file count
    initial_count = 0
    if Path(OUTPUT_FILE).exists():
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            initial_count = len([line for line in f if line.strip()])
        print(f"📖 File currently has: {initial_count} texts\n")

    all_texts = []
    chapter_texts = []

    # Determine total chapters AFTER sthana selection (dropdowns change!)
    time.sleep(2)  # wait for page to stabilize
    selects = driver.find_elements(By.TAG_NAME, "select")
    chapter_select = None
    for sel in selects:
        if len(sel.find_elements(By.TAG_NAME, "option")) > 10:
            chapter_select = sel
            break

    if chapter_select:
        total_chapters = len(chapter_select.find_elements(By.TAG_NAME, "option"))
        print(f"📚 Total chapters detected: {total_chapters}")
    else:
        print("⚠️ Chapter dropdown not found!")
        total_chapters = end_chapter
    
    print(f"📘 Scraping chapters {start_chapter} to {end_chapter}\n")

    for chapter in range(start_chapter, end_chapter + 1):
        print("=" * 60)
        print(f"📘 Chapter {chapter}")
        print("=" * 60)

        select_chapter(driver, chapter)
        chapter_texts = []  # Reset for each chapter
        page_count = 0

        while True:
            if reached_pushpika(driver):
                print("🛑 Reached पुष्पिका — stopping chapter\n")
                break

            texts = extract_sanskrit_from_page(driver)
            chapter_texts.extend(texts)
            all_texts.extend(texts)
            page_count += 1
            print(f"   ✔ Page {page_count}: {len(texts)} texts")

            try:
                next_btn = driver.find_element(By.NAME, "nextAdhi")
                if not next_btn.is_enabled():
                    break
                next_btn.click()
                time.sleep(2)
            except:
                break

        # SAVE AFTER EACH CHAPTER - append ALL texts (no duplicate checking)
        print(f"\n📊 DEBUG: chapter_texts has {len(chapter_texts)} items")
        print(f"📊 DEBUG: all_texts has {len(all_texts)} items")
        
        if chapter_texts:
            print(f"📊 DEBUG: Writing {len(chapter_texts)} texts to {OUTPUT_FILE}")
            try:
                with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
                    write_count = 0
                    for text in chapter_texts:
                        f.write(text + "\n")
                        write_count += 1
                    print(f"✅ Confirmed: {write_count} texts written to disk")
                print(f"✅ Chapter {chapter} saved ({write_count} texts appended)")
            except Exception as e:
                print(f"❌ Error saving chapter {chapter}: {e}")
        else:
            print(f"⏭️ Chapter {chapter} skipped (chapter_texts is empty)")
        
        # Reset for next chapter
        chapter_texts = []
        print(f"📊 DEBUG: chapter_texts reset to {len(chapter_texts)}\n")
        time.sleep(2)

    driver.quit()

    # Count final file size
    final_count = 0
    if Path(OUTPUT_FILE).exists():
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            final_count = len([line for line in f if line.strip()])

    print("\n" + "=" * 60)
    print("✅ SCRAPING COMPLETE")
    print(f"📄 Before scraping: {initial_count} texts")
    print(f"📄 After scraping: {final_count} texts")
    print(f"➕ Added this session: {final_count - initial_count} texts")
    print(f"💾 Saved to: {OUTPUT_FILE}")
    print("=" * 60)


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    try:
        # Scrape chapters 16-30 (सूत्रस्थानम्)
        scrape_all_chapters(start_chapter=16, end_chapter=30)
    except KeyboardInterrupt:
        print("\n⏸️ Scraping interrupted by user")
