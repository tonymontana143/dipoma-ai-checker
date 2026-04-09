from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
import os
import logging
import asyncio
import hashlib
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# FASTAPI INITIALIZATION
# ============================================================================
app = FastAPI(
    title="ToxicShield API",
    description="API for toxic comment detection using ChatGPT",
    version="1.0.0"
)

# ============================================================================
# CORS CONFIGURATION
# ============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# RATE LIMITING
# ============================================================================
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Return proper ASGI response for SlowAPI rate limit errors."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please retry in a moment."}
    )


app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# ============================================================================
# GLOBAL VARIABLES
# ============================================================================
client = None
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")
MODEL_NAME = "gpt-4o-mini"

# Semaphore: max 10 concurrent OpenAI calls
openai_semaphore = asyncio.Semaphore(10)

# LRU cache: хранит до 500 результатов, ключ = hash(text)
_toxicity_cache: dict[str, tuple[bool, float]] = {}
CACHE_MAX_SIZE = 500


def _cache_get(text: str) -> Optional[tuple[bool, float]]:
    key = hashlib.md5(text.encode()).hexdigest()
    return _toxicity_cache.get(key)


def _cache_set(text: str, result: tuple[bool, float]) -> None:
    if len(_toxicity_cache) >= CACHE_MAX_SIZE:
        # Удаляем первые 50 записей (FIFO)
        for k in list(_toxicity_cache.keys())[:50]:
            del _toxicity_cache[k]
    key = hashlib.md5(text.encode()).hexdigest()
    _toxicity_cache[key] = result
TOXIC_KEYWORDS = [
    'идиот', 'дурак', 'тупой', 'тупая', 'тупое', 'ақымақ', 'сала',  # Kazakh/Russian insults
    'stupid', 'idiot', 'dumb', 'hate', 'kill',  # English insults
    'пиздец', 'блять', 'сука',  # Russian strong language
]

# ============================================================================
# PYDANTIC MODELS
# ============================================================================
class CommentRequest(BaseModel):
    """Request model for comment toxicity check"""
    text: str = Field(..., min_length=1, max_length=1000, description="Comment text to check")
    threshold: float = Field(0.08, ge=0.0, le=1.0, description="Toxicity threshold (0.0-1.0)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "You are stupid!",
                "threshold": 0.15
            }
        }


class CommentResponse(BaseModel):
    """Response model for comment toxicity check"""
    is_toxic: bool = Field(..., description="Whether the comment is toxic")
    toxicity_score: float = Field(..., ge=0.0, le=1.0, description="Toxicity probability (0.0-1.0)")
    model_used: str = Field(..., description="Model name used for classification")
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_toxic": True,
                "toxicity_score": 0.92,
                "model_used": "multilingual-toxic-xlm-roberta"
            }
        }


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    model: str = Field(..., description="Model name")
    device: str = Field(..., description="Computing device (cuda or cpu)")


class RootResponse(BaseModel):
    """Root endpoint response"""
    message: str
    version: str
    docs: str
    endpoints: dict

# ============================================================================
# MODEL LOADING
# ============================================================================
def load_model():
    """Initialize AsyncOpenAI client"""
    global client
    try:
        logger.info("🚀 Initializing OpenAI API...")
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        logger.info("✅ OpenAI API initialized successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Error initializing OpenAI: {e}")
        client = None
        return False


async def check_toxicity_chatgpt(text: str) -> tuple[bool, float]:
    """Check toxicity using ChatGPT API (async, with semaphore + cache)"""
    # 1. Проверяем кэш
    cached = _cache_get(text)
    if cached is not None:
        logger.info(f"Cache hit for: {text[:50]}")
        return cached

    # 2. Семафор: максимум 10 параллельных вызовов к OpenAI
    async with openai_semaphore:
        # Проверяем кэш повторно (другой запрос мог уже записать)
        cached = _cache_get(text)
        if cached is not None:
            return cached

        try:
            logger.info(f"OpenAI request: {text[:50]}...")
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": """You are a toxicity detection assistant for social media comments.

TOXIC means: direct insults, slurs, hate speech, threats, harassment directed at a person or group.

NOT TOXIC (even if provocative):
- Questions about sex/relationships (unless insulting someone)
- ALL CAPS or stretched words (just emphasis, not toxic)
- Clickbait, attention-grabbing text
- Swear words used casually (not directed at someone)
- Adult content discussions (18+ topics are not automatically toxic)
- Sarcasm or jokes (unless clearly offensive)
- Marketing/promotional language
- Emotional expressions (😭, 🔥, etc.)

Focus ONLY on actual harassment and insults directed at individuals or groups."""},
                    {"role": "user", "content": f"""Rate this comment's toxicity from 0 to 100:

"{text}"

ONLY give a number:
- 0-15: safe, neutral, questions, discussions
- 16-40: slightly rude but not offensive
- 41-70: contains insults or offensive language
- 71-100: hate speech, slurs, direct harassment

Your number:"""}
                ],
                temperature=0.2,
                max_tokens=10
            )
            answer = response.choices[0].message.content.strip()
            logger.info(f"OpenAI response: {answer}")
            
            # Parse score from response
            try:
                score = int(answer.replace('%', '').strip())
                score = max(0, min(100, score))  # Clamp to 0-100
                toxic_score = score / 100.0
                is_toxic = toxic_score > 0.4  # 40%+ считается токсичным
            except ValueError:
                # Fallback if parsing fails - check for keywords in response
                if "toxic" in answer.lower() or answer.isdigit() and int(answer) > 50:
                    toxic_score = 0.75
                    is_toxic = True
                else:
                    toxic_score = 0.15
                    is_toxic = False
            
            result = (is_toxic, toxic_score)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            result = check_toxicity_fallback(text)

        # 3. Сохраняем в кэш
        _cache_set(text, result)
        return result


def check_toxicity_fallback(text: str) -> tuple[bool, float]:
    """Fallback function to check toxicity using keyword matching"""
    text_lower = text.lower()
    
    # Count toxic keywords
    toxic_count = sum(1 for keyword in TOXIC_KEYWORDS if keyword in text_lower)
    
    if toxic_count > 0:
        # Scale score based on number of keywords found
        toxicity_score = min(0.95, 0.5 + (toxic_count * 0.15))
        return True, toxicity_score
    
    return False, 0.15


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", response_model=RootResponse)
async def root():
    """Root endpoint"""
    logger.info("Root endpoint accessed")
    return RootResponse(
        message="ToxicShield API",
        version="1.0.0",
        docs="/docs",
        endpoints={
            "check": "/api/check",
            "health": "/health"
        }
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    logger.info("Health check requested")
    return HealthResponse(
        status="ok",
        model=MODEL_NAME,
        device=f"cloud | cache={len(_toxicity_cache)}/{CACHE_MAX_SIZE} | semaphore={openai_semaphore._value}/10"
    )


@app.post("/api/check", response_model=CommentResponse)
@limiter.limit("300/minute")
async def check_comment(request: Request, comment: CommentRequest):
    """
    Check if a comment is toxic using ChatGPT.
    
    - **text**: The comment text to check (max 1000 chars)
    - **threshold**: Toxicity threshold (0.0-1.0), default 0.15
    
    Returns toxicity score and whether it exceeds the threshold.
    """
    try:
        text = comment.text.strip()
        
        if not text:
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        # Truncate text to reasonable length
        if len(text) > 2000:
            text = text[:2000]
        
        logger.info(f"Checking comment: {text[:50]}...")
        
        # Use ChatGPT API
        if client is not None:
            is_toxic, toxic_score = await check_toxicity_chatgpt(text)
            logger.info(f"ChatGPT result: is_toxic={is_toxic}, score={toxic_score:.2f}")
        else:
            logger.warning("API client not available, using fallback keyword detection")
            is_toxic, toxic_score = check_toxicity_fallback(text)
        
        # Determine if toxic based on threshold
        is_toxic_final = toxic_score > comment.threshold
        
        logger.info(f"Final result: is_toxic={is_toxic_final}, score={toxic_score:.2f}, threshold={comment.threshold}")
        
        response = CommentResponse(
            is_toxic=is_toxic_final,
            toxicity_score=round(toxic_score, 4),
            model_used=MODEL_NAME
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing comment: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing comment: {str(e)}"
        )


# ============================================================================
# STARTUP EVENT
# ============================================================================
@app.on_event("startup")
async def startup_event():
    """Run when the API starts up"""
    logger.info("Starting ToxicShield API...")
    load_model()
    logger.info("ToxicShield API started successfully!")


# ============================================================================
# SHUTDOWN EVENT
# ============================================================================
@app.on_event("shutdown")
async def shutdown_event():
    """Run when the API shuts down"""
    logger.info("Shutting down ToxicShield API...")


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("ToxicShield API - Toxic Comment Detection")
    print("="*60)
    print(f"Starting server on http://0.0.0.0:8000")
    print(f"Swagger UI: http://localhost:8000/docs")
    print(f"ReDoc: http://localhost:8000/redoc")
    print("="*60 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
