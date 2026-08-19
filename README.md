# Shine.com Jobs Scraper

Scrape job listings from Shine.com, India's second-largest online job portal with over 3 million monthly visitors.

## Features

- ✅ Extract job titles, companies, locations, salaries, and experience requirements
- ✅ Search by keywords and location
- ✅ Configurable result limits
- ✅ No login required
- ✅ Compatible with Claude, ChatGPT & AI agents via Apify MCP

## Input

| Field | Type | Description | Default |
|-------|------|-------------|---------|
| `searchQuery` | string | Job search keywords (e.g., 'data analyst', 'software engineer') | `"jobs"` |
| `location` | string | City or location (e.g., 'Mumbai', 'Bangalore') | `""` (all) |
| `maxResults` | integer | Maximum number of jobs to scrape | `100` |

## Output

Each job listing contains:

- `jobId` - Unique job identifier
- `title` - Job position title
- `company` - Hiring company name
- `location` - Job location
- `experience` - Required experience level
- `salary` - Salary range (if available)
- `url` - Direct link to job posting
- `scrapedAt` - Timestamp

## Example Input

```json
{
  "searchQuery": "data analyst",
  "location": "Bangalore",
  "maxResults": 50
}
```

## Example Output

```json
{
  "jobId": "12345678",
  "title": "Senior Data Analyst",
  "company": "Tech Solutions India",
  "location": "Bangalore / Bengaluru",
  "experience": "3-5 years",
  "salary": "₹8-12 LPA",
  "url": "https://www.shine.com/job/12345678",
  "scrapedAt": "2026-08-19T06:00:00.000Z"
}
```

## Pricing

- **$0.005 per result** ($5 per 1,000 jobs)
- **$0.05 actor start fee** (one-time per run)

## Use Cases

- 📊 Job market analysis and salary benchmarking
- 🎯 Recruitment and candidate sourcing
- 📈 Track hiring trends in India
- 🤖 AI-powered job matching and recommendations
- 📧 Job alert aggregation
