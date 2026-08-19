"""Shine.com Jobs Scraper - India's second-largest job portal."""
import asyncio
import re
from datetime import datetime, timezone
from typing import Optional

from apify import Actor
from playwright.async_api import async_playwright, Page


async def extract_job_data(page: Page) -> list:
    """Extract job listings from the current page."""
    jobs = []
    
    try:
        # Wait for job cards to load - using actual Shine.com classes
        await page.wait_for_selector('.jdbigCard, div[class*="bigCard"]', timeout=20000)
        
        # Extract job data from cards
        job_cards = await page.query_selector_all('.jdbigCard, div[class*="bigCard"]')
        
        Actor.log.info(f'Found {len(job_cards)} job cards')
        
        for idx, card in enumerate(job_cards):
            try:
                # Extract title - using h3 itemprop="name"
                title_elem = await card.query_selector('h3[itemprop="name"], h3[class*="Heading"]')
                title = await title_elem.inner_text() if title_elem else None
                
                # Extract company name - using span with "Company" in class
                company_elem = await card.query_selector('span[class*="CompanyName"], span[class*="bigCardTopTitleName"]')
                company = await company_elem.inner_text() if company_elem else None
                
                # Extract location - div with "Location" in class
                location_elem = await card.query_selector('div[class*="Location"], span[class*="Location"]')
                location = await location_elem.inner_text() if location_elem else None
                
                # Extract experience - div with "Experience" in class
                exp_elem = await card.query_selector('div[class*="Experience"] span, span[class*="Exp"]')
                experience = await exp_elem.inner_text() if exp_elem else None
                
                # Extract salary - look for "Salary" or "CTC" in class
                salary_elem = await card.query_selector('div[class*="Salary"], span[class*="Salary"], div[class*="ctc"]')
                salary = await salary_elem.inner_text() if salary_elem else None
                
                # Extract job URL - meta itemprop="url" or anchor href
                url_elem = await card.query_selector('meta[itemprop="url"]')
                if url_elem:
                    job_url = await url_elem.get_attribute('content')
                else:
                    link_elem = await card.query_selector('a[href*="/jobs/"]')
                    job_url = await link_elem.get_attribute('href') if link_elem else None
                
                if job_url and not job_url.startswith('http'):
                    job_url = f'https://www.shine.com{job_url}'
                
                # Extract job ID from URL
                job_id = None
                if job_url:
                    match = re.search(r'/jobs/[^/]+/[^/]+/(\d+)', job_url)
                    if match:
                        job_id = match.group(1)
                
                if title:  # Only include if we have at least a title
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
                    Actor.log.debug(f'Extracted job #{idx+1}: {title}')
                    
            except Exception as e:
                Actor.log.debug(f'Error extracting job card #{idx+1}: {e}')
                continue
                
    except Exception as e:
        Actor.log.warning(f'Error finding job cards: {e}')
        
    return jobs


async def has_next_page(page: Page) -> bool:
    """Check if there's a next page button."""
    try:
        # Check for "next" link in pagination
        next_button = await page.query_selector('link[rel="next"], a[aria-label*="Next"], .pagination a:has-text("Next")')
        return next_button is not None
    except:
        return False


async def go_to_next_page(page: Page, current_page_num: int) -> bool:
    """Navigate to next page by URL manipulation."""
    try:
        current_url = page.url
        # Shine.com uses -2, -3, etc. for page numbers
        if f'-{current_page_num}' in current_url:
            next_url = current_url.replace(f'-{current_page_num}', f'-{current_page_num + 1}')
        else:
            # First page doesn't have number, add -2 for second page
            next_url = current_url.rstrip('/') + '-2'
        
        Actor.log.info(f'Navigating to: {next_url}')
        await page.goto(next_url, wait_until='networkidle', timeout=30000)
        await asyncio.sleep(3)
        return True
    except Exception as e:
        Actor.log.debug(f'Error navigating to next page: {e}')
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
                await asyncio.sleep(4)  # Wait for JS to render
                
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
                    success = await go_to_next_page(page, page_num)
                    if not success:
                        Actor.log.info('Could not navigate to next page')
                        break
                    page_num += 1
                        
            finally:
                await browser.close()
        
        Actor.log.info(f'Scraping completed. Total jobs: {total_scraped}')
