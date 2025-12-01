# Message Search Engine

A high-performance search API that provides sub-100ms search across message data.

## Deployed URL

https://message-search-engine-pp0y.onrender.com

## Features

- Sub-1ms search response time (100x faster than required)
- Full-text search across messages, usernames, and user IDs
- Pagination support
- In-memory caching (3,349 messages cached)
- Auto-retry with exponential backoff for API rate limits

## API Endpoints

### Search Messages
```bash
GET /search?q={query}&skip={skip}&limit={limit}
```

**Parameters:**
- `q` (required): Search query string
- `skip` (optional): Number of results to skip (default: 0)
- `limit` (optional): Number of results to return (default: 100, max: 1000)

**Example:**
```bash
curl "https://message-search-engine-pp0y.onrender.com/search?q=paris&limit=10"
```

**Response:**
```json
{
  "total": 86,
  "items": [...],
  "skip": 0,
  "limit": 10,
  "cache_size": 3349,
  "response_time_ms": 1.75
}
```

### Health Check
```bash
GET /health
```

Returns cache status and message count.

## Performance

- Average response time: 0.5-2ms
- Requirement: < 100ms 
- Cache load time: approximately 60 seconds on startup
- Total messages cached: 3,349

## Local Development
```bash
# Clone repository
git clone git@github.com:hb2101/search-engine.git
cd search-engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --reload

# Test
curl "http://localhost:8000/search?q=test"
```

## Technical Stack

- Framework: FastAPI 0.104.1
- HTTP Client: httpx 0.25.1
- Python: 3.9+
- Deployment: Render.com

## Design Approaches Considered

### Approach 1: Direct API Proxy (Not Chosen)

Forward each search request directly to the source API.

**Pros:** Simple implementation, always returns up-to-date data

**Cons:** High latency (200-500ms), cannot reliably meet the sub-100ms requirement

**Decision:** Not chosen due to performance constraints

### Approach 2: In-Memory Cache (Chosen)

Load all messages into memory at startup and search through the cached data.

**Pros:** Extremely fast response time (sub-1ms), simple implementation

**Cons:** Uses more memory, requires startup time to load data, data becomes stale until restart

**Decision:** Chosen because it easily meets the performance requirement with minimal complexity. For a dataset of 3,349 messages, the memory overhead is acceptable and the startup time is reasonable.

### Approach 3: SQLite with Full-Text Search

Store messages in a SQLite database with FTS5 full-text search extension.

**Pros:** Persistent storage, advanced search features like ranking and stemming, handles larger datasets well

**Cons:** Additional complexity (database schema, migrations), slightly slower than in-memory (30-50ms), requires filesystem access

**When to use:** Better suited for production systems that require data persistence and more complex querying capabilities.

### Approach 4: Elasticsearch

Use a dedicated search engine like Elasticsearch or OpenSearch.

**Pros:** Production-grade search capabilities, horizontal scalability, advanced features like fuzzy matching and autocomplete, relevance scoring

**Cons:** Significant infrastructure cost, complex setup and maintenance, overkill for a dataset of only 3,349 messages

**When to use:** Appropriate for large-scale production systems with hundreds of thousands or millions of records that require advanced search features.

## Reducing Latency to 30ms

Current performance is already 0.5-2ms, which is well under the 30ms target. However, if further optimization were needed, here are some approaches that could be considered:

### 1. Inverted Index
Build a mapping from words to message IDs. This would reduce search complexity from O(n) to approximately O(1) for lookups plus O(k) for result assembly, where k is the number of matching results.

### 2. Trie Data Structure
Implement a prefix tree for faster prefix matching queries. This would be  particularly useful for autocomplete-style searches.

### 3. Bloom Filters
Use bloom filters for quick negative lookups. This allows the system to quickly determine if a search term definitely does not exist in the dataset without scanning all messages.

### 4. Response Compression
Adding a gzip compression middleware to reduce the size of responses sent over the network. This would be especially beneficial for large result sets.

### 5. CDN Caching
Cache common search queries at edge locations using a CDN. This would reduce latency for frequently searched terms by serving responses from servers closer to the user.

## Implementation Notes

The external API has rate limiting that prevents loading all messages in quick succession. The implementation includes retry logic with exponential backoff to handle these limits gracefully. After testing various strategies, a 1-second delay between requests with extended backoff periods on rate limit errors was found to be effective for loading the full dataset.

## License

MIT