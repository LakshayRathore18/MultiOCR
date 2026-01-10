#!/usr/bin/env python3
"""Batch scraper for multiple chapters and page counts"""

from scrape import scrape_selenium_multipage
import time

# Define chapters and page counts to scrape
SCRAPE_JOBS = [
    (8, 29),
    (9, 19),
    (10, 13),
    (11, 48),
    (12, 11),
    (13, 38),
    (14, 35),
    (15, 15),
]

def run_batch_scrape():
    """Run all scrape jobs in sequence"""
    url = "https://niimh.nic.in/ebooks/ecaraka/?mod=read"
    total_jobs = len(SCRAPE_JOBS)
    
    print("="*60)
    print("🔄 BATCH SCRAPER - Multiple Chapters")
    print("="*60)
    print(f"Total jobs to run: {total_jobs}\n")
    
    for idx, (chapter, pages) in enumerate(SCRAPE_JOBS, 1):
        print(f"\n{'='*60}")
        print(f"📚 Job {idx}/{total_jobs}: Chapter {chapter}, {pages} pages")
        print(f"{'='*60}\n")
        
        try:
            texts = scrape_selenium_multipage(
                url,
                output_file="data/scraped_sanskrit.txt",
                max_pages=pages,
                append=True,
                chapter=chapter
            )
            
            if texts:
                print(f"✅ Job {idx} completed successfully")
            else:
                print(f"⚠️  Job {idx} completed with no texts extracted")
        
        except Exception as e:
            print(f"❌ Job {idx} failed: {e}")
        
        # Small delay between jobs (avoid overwhelming the server)
        if idx < total_jobs:
            print(f"\n⏳ Waiting 5 seconds before next job...")
            time.sleep(5)
    
    print(f"\n{'='*60}")
    print("✨ BATCH SCRAPING COMPLETE!")
    print(f"{'='*60}\n")
    print("Next step: Run 'python scraping/clean_and_extract.py'")
    print("to extract unique Sanskrit words from all chapters.\n")

if __name__ == "__main__":
    try:
        run_batch_scrape()
    except KeyboardInterrupt:
        print("\n⏸️  Batch scraping cancelled by user")
        exit(0)
