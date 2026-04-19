import torch
import numpy as np
import sys
from sentence_transformers import SentenceTransformer

def cosine_similarity(query_emb, corpus_embs):
    # Normalize
    query_norm = query_emb / np.linalg.norm(query_emb)
    corpus_norms = corpus_embs / np.linalg.norm(corpus_embs, axis=1, keepdims=True)
    # Dot product gives cosine similarity if normalized
    return np.dot(corpus_norms, query_norm.T).flatten()

def main():
    if len(sys.argv) < 2:
        print("Kullanım: python search_books.py 'arama metni veya açıklama'")
        sys.exit(1)
        
    query_text = sys.argv[1]
    
    # 1. Load checkpoints
    checkpoint_file = 'first_1k_checkpoint.npz'
    try:
        data = np.load(checkpoint_file, allow_pickle=True)
        corpus_embeddings = data['embeddings']
        ids = data['ids']
        titles = data['titles']
    except Exception as e:
        print(f"Error loading checkpoint: {e}")
        sys.exit(1)
        
    # 2. Get device 
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    
    print("\n[Arama Motoru Hazırlanıyor...]")
    print(f"BGE-M3 Modeli yükleniyor (Aygıt: {device})...")
    # Using float16 for fast loading
    model = SentenceTransformer('BAAI/bge-m3', device=device, model_kwargs={"torch_dtype": torch.float16})
    
    print(f"\nSorgu metniniz: '{query_text}'")
    print("Sorgu vektöre dönüştürülüyor...")
    query_embedding = model.encode([query_text], device=device, show_progress_bar=False)[0]
    
    # 3. Calculate similarity
    print("Benzerlik hesaplanıyor...")
    similarities = cosine_similarity(query_embedding, corpus_embeddings)
    
    # 4. Get Top 5 results
    top_k = 5
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    print("\n" + "="*60)
    print(f"EN İYİ {top_k} EŞLEŞEN KİTAP")
    print("="*60)
    
    for rank, idx in enumerate(top_indices, start=1):
        score = similarities[idx]
        title = titles[idx]
        book_id = ids[idx]
        # In case title is missing or nan
        if str(title) == 'nan' or not title:
            title = "Bilinmeyen Başlık"
        print(f"{rank}. [Skor: %{score*100:.1f}] | Kitap: {title} (ID: {book_id})")
        
if __name__ == "__main__":
    main()
