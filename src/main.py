"""Shine.com Jobs Scraper - India's second-largest job portal."""
import asyncio
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs

from apify import Actor
from playwright.async_api import async_playwright, Page, Browser


async def extract_job_data(page: Page) -> list:
    """Extract job listings from the current page."""
    jobs = []
    
    try:
        # Wait for job cards to load
        await page.wait_for_selector('.job_card, .jobCard, [data-job-id], .job-listing', timeout=15000)
        
        # Extract job data from cards
        job_cards = await page.query_selector_all('.job_card, .jobCard, [data-job-id], .job-listing')
        
        for card in job_cards:
            try:
                # Extract title
                title_elem = await card.query_selector('h2, h3, .job_title, .jobTitle, [class*="title"]')
                title = await title_elem.inner_text() if title_elem else None
                
                # Extract company
                company_elem = await card.query_selector('.company, .companyName, [class*="company"]')
                company = await company_elem.inner_text() if company_elem else None
                
                # Extract location
                location_elem = await card.query_selector('.location, .jobLocation, [class*="location"]')
                location = await location_elem.inner_text() if location_elem else None
                
                # Extract experience
                exp_elem = await card.query_selector('.experience, .exp, [class*="experience"]')
                experience = await exp_elem.inner_text() if exp_elem else None
                
                # Extract salary
                salary_elem = await card.query_selector('.salary, .ctc, [class*="salary"]')
                salary = await salary_elem.inner_text() if salary_elem else None
                
                # Extract job URL
                link_elem = await card.query_selector('a[href*="/job/"]')
                job_url = await link_elem.get_attribute('href') if link_elem else None
                if job_url and not job_url.startswith('http'):
                    job_url = f'https://www.shine.com{job_url}'
                
                # Extract job ID from URL or data attribute
                job_id = None
                if job_url:
                    match = re.search(r'/job/([^/]+)', job_url)
                    if match:
                        job_id = match.group(1)
                
                if title and company:  # Only include if we have minimal data
                    jobs.append({
                        'jobId': job_id,
                        'title': title.strip() if title else None,
                        'company': company.strip() if company else None,
                        'location': location.strip() if location else None,
                        'experience': experience.strip() if experience else None,
                        'salary': salary.strip() if salary else None,
                        'url': job_url,
                        'scrapedAt': datetime.now(timezone.utc).isoformat()
                    })
                    
            except Exception as e:
                Actor.log.debug(f'Error extracting job card: {e}')
                continue
                
    except Exception as e:
        Actor.log.warning(f'Error finding job cards: {e}')
        
    return jobs


async def has_next_page(page: Page) -> bool:
    """Check if there's a next page button."""
    try:
        next_button = await page.query_selector('a.next, .pagination a[aria-label="Next"], .pagination .next:not(.disabled)')
        return next_button is not None
    except:
        return False


async def click_next_page(page: Page) -> bool:
    """Click the next page button and wait for navigation."""
    try:
        next_button = await page.query_selector('a.next, .pagination a[aria-label="Next"], .pagination .next:not(.disabled)')
        if next_button:
            await next_button.click()
            await page.wait_for_load_state('networkidle', timeout=15000)
            await asyncio.sleep(2)  # Extra delay for dynamic content
            return True
    except Exception as e:
        Actor.log.debug(f'Error clicking next page: {e}')
    return False


async def main() -> None:
    """Main scraper entry point."""
    async with Actor:
        Actor.log.info('Shine Jobs Scraper starting...')
        
        # Get input
        actor_input = await Actor.get_input() or {}
        search_query = actor_input.get('searchQuery', 'jobs')
        location = actor_input.get('location', '')
        max_results = actor_input.get('maxResults', 100)
        
        # Build search URL
        base_url = 'https://www.shine.com/job-search/'
        
        # Format query for URL
        query_part = search_query.lower().replace(' ', '-')
        if location:
            query_part = f'{query_part}-jobs-in-{location.lower().replace(" ", "-")}'
        else:
            query_part = f'{query_part}-jobs'
            
        start_url = f'{base_url}{query_part}'
        
        Actor.log.info(f'Starting scrape: {start_url}')
        Actor.log.info(f'Max results: {max_results}')
        
        total_scraped = 0
        page_num = 1
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            
            try:
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1920, 'height': 1080}
                )
                
                page = await context.new_page()
                
                # Navigate to search page
                await page.goto(start_url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(3)  # Wait for JS to render
                
                while total_scraped < max_results:
                    Actor.log.info(f'Scraping page {page_num}...')
                    
                    # Extract jobs from current page
                    jobs = await extract_job_data(page)
                    
                    if not jobs:
                        Actor.log.warning(f'No jobs found on page {page_num}')
                        break
                    
                    Actor.log.info(f'Found {len(jobs)} jobs on page {page_num}')
                    
                    # Push results to dataset
                    for job in jobs:
                        if total_scraped >= max_results:
                            break
                        await Actor.push_data(job)
                        total_scraped += 1
                        
                        if total_scraped % 10 == 0:
                            Actor.log.info(f'Progress: {total_scraped}/{max_results} jobs scraped')
                    
                    # Check if we need more results
                    if total_scraped >= max_results:
                        break
                    
                    # Try to go to next page
                    if await has_next_page(page):
                        success = await click_next_page(page)
                        if not success:
                            Actor.log.info('Could not navigate to next page')
                            break
                        page_num += 1
                    else:
                        Actor.log.info('No more pages available')
                        break
                        
            finally:
                await browser.close()
        
        Actor.log.info(f'Scraping completed. Total jobs: {total_scraped}')
