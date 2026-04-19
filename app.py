"""
Kitap Öneri Sistemi — FastAPI Backend
Hikaye tabanlı kitap keşif API'si (ChatGPT entegrasyonu)
"""

import os
import numpy as np
import pandas as pd
import torch
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from openai import OpenAI

# ── Config ─────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-your-key-here":
    print("[WARNING] OPENAI_API_KEY is not set in .env — story generation will fail!")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI(title="Kitap Öneri Sistemi")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global State ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKPOINT_PATH = os.path.join(BASE_DIR, "first_1k_checkpoint.npz")
BOOK_DATA_PATH = os.path.join(BASE_DIR, "cleaned_data", "book_data")

MAX_ATTEMPTS = 6

model = None
corpus_embeddings = None
book_ids = None
book_titles = None
books_df = None


# ── Helpers ────────────────────────────────────────────────────
def cosine_similarity(query_emb: np.ndarray, corpus_embs: np.ndarray) -> np.ndarray:
    query_norm = query_emb / (np.linalg.norm(query_emb) + 1e-10)
    corpus_norms = corpus_embs / (np.linalg.norm(corpus_embs, axis=1, keepdims=True) + 1e-10)
    return np.dot(corpus_norms, query_norm.T).flatten()


def load_model():
    global model
    if model is not None:
        return model
    from sentence_transformers import SentenceTransformer
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"[Model] Loading BAAI/bge-m3 on {device}...")
    model = SentenceTransformer(
        "BAAI/bge-m3",
        device=device,
        model_kwargs={"torch_dtype": torch.float16},
    )
    model.max_seq_length = 128
    print("[Model] Ready.")
    return model


def find_similar_books(book_ids_selected: List[str], prompt: str, top_k: int = MAX_ATTEMPTS) -> List[str]:
    """Return top_k similar book IDs via hybrid vector search + rating boost."""
    book_vectors = []
    prompt_vector = None

    # 1) Kitap vektörleri
    if book_ids_selected:
        id_to_idx = {bid: i for i, bid in enumerate(book_ids)}
        for bid in book_ids_selected:
            idx = id_to_idx.get(bid)
            if idx is not None:
                book_vectors.append(corpus_embeddings[idx])

    # 2) Prompt vektörü
    if prompt and prompt.strip():
        m = load_model()
        device = "mps" if torch.backends.mps.is_available() else "cpu"
        prompt_vector = m.encode([prompt.strip()], device=device, show_progress_bar=False)[0]

    # Hibrit: hem kitap seçimi hem prompt varsa ağırlıklı ortalama
    if book_vectors and prompt_vector is not None:
        books_avg = np.mean(book_vectors, axis=0)
        query_vector = 0.6 * books_avg + 0.4 * prompt_vector
    elif book_vectors:
        query_vector = np.mean(book_vectors, axis=0)
    elif prompt_vector is not None:
        query_vector = prompt_vector
    else:
        return []

    similarities = cosine_similarity(query_vector, corpus_embeddings)

    # Rating normalizasyonu (0-5 arası -> 0-1 arası)
    exclude_set = set(book_ids_selected) if book_ids_selected else set()
    scored = []
    for i, sim_score in enumerate(similarities):
        if book_ids[i] not in exclude_set:
            bid = book_ids[i]
            rating = 0.0
            if bid in books_df.index:
                r = books_df.loc[bid, "average_rating"]
                rating = float(r) / 5.0 if pd.notna(r) else 0.0
            # Final skor: %70 benzerlik + %30 rating
            final_score = 0.7 * float(sim_score) + 0.3 * rating
            scored.append((i, final_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [book_ids[idx] for idx, _ in scored[:top_k]]


def generate_story(book_title: str, book_description: str) -> str:
    """Generate a spoiler-free engaging short story inspired by the book."""
    system_prompt = """Sen yaratıcı bir hikaye yazarısın. Sana bir kitabın başlığı ve açıklaması verilecek.
Görevin: Bu kitabın temasını, atmosferini ve duygusal tonunu yansıtan, ama KESİNLİKLE spoiler vermeyen 
ÇOK KISA ve ilgi çekici bir sahne/an yazmak.

KURALLAR:
- Kitabın adını, yazarın adını veya karakterlerin gerçek isimlerini ASLA kullanma
- Kitabın olay örgüsünü direkt anlatma, sadece temasından esinlen
- MAKSIMUM 1-2 kısa paragraf olsun (5-8 cümle)
- Bir sahne, bir an, bir duygu yakala — uzun anlatma
- Okuyucunun merakını uyandıracak, "bu kitabı okumak istiyorum" dedirtecek bir ton kullan
- Hikayeyi Türkçe yaz
- Sonunda yorum, öneri veya ekstra açıklama EKLEME
- Sadece hikayeyi yaz, başka bir şey ekleme"""

    user_prompt = f"""Kitap Başlığı: {book_title}
Kitap Açıklaması: {book_description}

Bu kitaptan esinlenerek çok kısa, etkileyici ve spoiler vermeyen bir sahne yaz."""

    try:
        response = openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=400,
            temperature=0.85,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[GPT Error] {e}")
        raise HTTPException(status_code=500, detail=f"Hikaye oluşturulamadı: {str(e)}")


# ── Startup ────────────────────────────────────────────────────
@app.on_event("startup")
def startup():
    global corpus_embeddings, book_ids, book_titles, books_df

    print("[Startup] Loading checkpoint...")
    data = np.load(CHECKPOINT_PATH, allow_pickle=True)
    corpus_embeddings = data["embeddings"]
    book_ids = data["ids"].astype(str)
    book_titles = data["titles"].astype(str)
    print(f"[Startup] Loaded {len(book_ids)} embeddings.")

    print("[Startup] Loading book metadata...")
    full_df = pd.read_parquet(BOOK_DATA_PATH)
    id_set = set(book_ids)
    books_df = full_df[full_df["id"].astype(str).isin(id_set)].copy()
    books_df["id"] = books_df["id"].astype(str)
    books_df = books_df.set_index("id", drop=False)
    print(f"[Startup] Metadata ready for {len(books_df)} books.")


# ── Request / Response Models ──────────────────────────────────
class DiscoverRequest(BaseModel):
    book_ids: List[str] = []
    prompt: Optional[str] = ""


class StoryResponse(BaseModel):
    story: str
    attempt: int
    max_attempts: int
    session_books: List[str]


class NextStoryRequest(BaseModel):
    session_books: List[str]
    current_attempt: int


class RevealRequest(BaseModel):
    session_books: List[str]
    current_attempt: int


class BookReveal(BaseModel):
    id: str
    title: str
    author_name: str
    image_url: str
    description: str
    average_rating: float


# ── API Endpoints ──────────────────────────────────────────────
@app.get("/api/books/search")
def search_books(q: str = Query("", min_length=1)):
    """Title / author arama."""
    q_lower = q.lower()
    mask = (
        books_df["title"].str.lower().str.contains(q_lower, na=False)
        | books_df["author_name"].str.lower().str.contains(q_lower, na=False)
    )
    results = books_df[mask].head(20)
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "author_name": row["author_name"],
            "image_url": row["image_url"],
        }
        for _, row in results.iterrows()
    ]


@app.post("/api/discover", response_model=StoryResponse)
def discover(req: DiscoverRequest):
    """Find similar books and generate a story for the first one."""
    similar_ids = find_similar_books(req.book_ids, req.prompt or "", MAX_ATTEMPTS)

    if not similar_ids:
        raise HTTPException(status_code=404, detail="Benzer kitap bulunamadı.")

    # Generate story for first book
    bid = similar_ids[0]
    if bid in books_df.index:
        row = books_df.loc[bid]
        story = generate_story(str(row["title"]), str(row["description"]))
    else:
        raise HTTPException(status_code=404, detail="Kitap bilgisi bulunamadı.")

    return StoryResponse(
        story=story,
        attempt=1,
        max_attempts=MAX_ATTEMPTS,
        session_books=similar_ids,
    )


@app.post("/api/story/next", response_model=StoryResponse)
def next_story(req: NextStoryRequest):
    """Generate story for the next book in the session."""
    attempt = req.current_attempt + 1

    if attempt > MAX_ATTEMPTS or attempt > len(req.session_books):
        raise HTTPException(status_code=400, detail="Maksimum deneme sayısına ulaşıldı.")

    bid = req.session_books[attempt - 1]
    if bid in books_df.index:
        row = books_df.loc[bid]
        story = generate_story(str(row["title"]), str(row["description"]))
    else:
        raise HTTPException(status_code=404, detail="Kitap bilgisi bulunamadı.")

    return StoryResponse(
        story=story,
        attempt=attempt,
        max_attempts=MAX_ATTEMPTS,
        session_books=req.session_books,
    )


@app.post("/api/story/reveal", response_model=BookReveal)
def reveal_book(req: RevealRequest):
    """Reveal the actual book for the current attempt."""
    if req.current_attempt < 1 or req.current_attempt > len(req.session_books):
        raise HTTPException(status_code=400, detail="Geçersiz deneme numarası.")

    bid = req.session_books[req.current_attempt - 1]
    if bid not in books_df.index:
        raise HTTPException(status_code=404, detail="Kitap bulunamadı.")

    row = books_df.loc[bid]
    return BookReveal(
        id=bid,
        title=str(row["title"]),
        author_name=str(row["author_name"]),
        image_url=str(row["image_url"]),
        description=str(row["description"])[:500],
        average_rating=float(row["average_rating"]) if pd.notna(row["average_rating"]) else 0.0,
    )


# ── Serve Frontend ─────────────────────────────────────────────
frontend_dir = os.path.join(BASE_DIR, "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))


# ── Run ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
