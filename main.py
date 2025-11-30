from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import List, Dict, Any
import asyncio
import time

app = FastAPI(title="Message Search Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_URL = "https://november7-730026606190.europe-west1.run.app"
message_cache: List[Dict[str, Any]] = []
cache_loaded = False

async def load_all_messages():
    global message_cache, cache_loaded
    
    if cache_loaded:
        return
    
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        skip = 0
        limit = 100
        all_messages = []
        max_retries = 5
        
        while True:
            retry_count = 0
            success = False
            
            while retry_count < max_retries and not success:
                try:
                    url = f"{BASE_URL}/messages/"
                    response = await client.get(
                        url,
                        params={"skip": skip, "limit": limit}
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    items = data.get("items", [])
                    if not items:
                        cache_loaded = True
                        message_cache = all_messages
                        print(f"Loaded {len(message_cache)} messages into cache")
                        return
                    
                    all_messages.extend(items)
                    total = data.get("total", 0)
                    print(f"Loaded {len(all_messages)}/{total} messages...")
                    
                    skip += limit
                    success = True
                    
                    # Adding a small delay between requests to avoid rate limiting
                    await asyncio.sleep(1.0)
                    
                    if len(all_messages) >= total:
                        cache_loaded = True
                        message_cache = all_messages
                        print(f"Loaded {len(message_cache)} messages into cache")
                        return
                        
                except httpx.HTTPStatusError as e:
                    if e.response.status_code in [400, 402, 403, 429, 404, 401,405]:
                        retry_count += 1
                        wait_time = 5 * (2 ** retry_count)  # Exponential backoff: 2, 4, 8 seconds
                        print(f"Rate limited at skip={skip}. Waiting {wait_time}s before retry {retry_count}/{max_retries}...")
                        await asyncio.sleep(wait_time)
                    else:
                        print(f"Error at skip={skip}: {e}")
                        break
                except Exception as e:
                    print(f"Unexpected error at skip={skip}: {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        await asyncio.sleep(5)
            
            if not success:
                print(f"Failed to load all messages. Loaded {len(all_messages)} so far.")
                break
        
        message_cache = all_messages
        cache_loaded = True
        print(f"Loaded {len(message_cache)} messages into cache (partial)")

def search_messages(query: str, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
    """Search messages in cache."""
    query_lower = query.lower()
    
    matched = [
        msg for msg in message_cache
        if (query_lower in msg.get("message", "").lower() or
            query_lower in msg.get("user_name", "").lower() or
            query_lower in msg.get("user_id", "").lower())
    ]
    
    total = len(matched)
    paginated = matched[skip:skip + limit]
    
    return {
        "total": total,
        "items": paginated,
        "skip": skip,
        "limit": limit,
        "cache_size": len(message_cache)
    }

@app.on_event("startup")
async def startup_event():
    """Load messages on startup."""
    print("Starting up... Loading messages into cache")
    await load_all_messages()

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "running",
        "cached_messages": len(message_cache),
        "total_messages": 3349,
        "cache_percentage": f"{(len(message_cache) / 3349 * 100):.1f}%",
        "endpoints": {
            "search": "/search?q=your_query",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "cache_loaded": cache_loaded,
        "cached_messages": len(message_cache),
        "total_messages": 3349
    }

@app.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of items to retrieve")
):
    """
    Search messages by query string.
    Returns results in under 100ms.
    """
    start_time = time.perf_counter()
    
    if not cache_loaded:
        raise HTTPException(status_code=503, detail="Cache still loading, please wait...")
    
    if not q or q.strip() == "":
        raise HTTPException(status_code=400, detail="Query parameter 'q' cannot be empty")
    
    results = search_messages(q.strip(), skip, limit)
    
    end_time = time.perf_counter()
    elapsed_ms = (end_time - start_time) * 1000
    
    results["response_time_ms"] = round(elapsed_ms, 2)
    
    return results

@app.post("/refresh-cache")
async def refresh_cache():
    """Manually refresh the message cache."""
    global cache_loaded
    cache_loaded = False
    await load_all_messages()
    return {
        "status": "success",
        "cached_messages": len(message_cache)
    }