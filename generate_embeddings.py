import pandas as pd
import time
import psutil
import os
import torch
import numpy as np
from sentence_transformers import SentenceTransformer

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

def main():
    start_time = time.time()
    start_mem = get_memory_usage()

    print(f"[{time.strftime('%H:%M:%S')}] Started process. Initial Memory: {start_mem:.2f} MB")

    # Determine device (CPU or MPS)
    if torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"
    print(f"[{time.strftime('%H:%M:%S')}] Using device: {device}")

    # Load Model
    print(f"[{time.strftime('%H:%M:%S')}] Loading BAAI/bge-m3 model (float16)...")
    model = SentenceTransformer('BAAI/bge-m3', device=device, model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = 128  # Prevent MPS Invalid buffer size error due to long padding

    # Note: BAAI/bge-m3 usually generates 1024 dimensional embeddings by default for dense vectors.
    
    # Load dataset
    print(f"[{time.strftime('%H:%M:%S')}] Loading dataset...")
    file_path = '/Users/h.atay./Desktop/kitap-oneri-sistemi/cleaned_data/book_data'
    df = pd.read_parquet(file_path)
    
    # Select first 1000 rows
    print(f"[{time.strftime('%H:%M:%S')}] Selecting first 1,000 rows")
    df_subset = df.head(1000).copy()
    
    texts = df_subset['description'].astype(str).tolist()
    
    # Generate Embeddings
    print(f"[{time.strftime('%H:%M:%S')}] Starting to encode descriptions. Batch size: 64")
    # Record starting encoding
    encode_start = time.time()
    
    # We will encode them
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=True, device=device)
    
    encode_end = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] Encoding completed in {encode_end - encode_start:.2f} seconds.")

    # Validation of shape
    embedding_shape = embeddings.shape
    print(f"[{time.strftime('%H:%M:%S')}] Generated embeddings shape: {embedding_shape}")
    if embedding_shape[1] != 1024:
        print(f"[{time.strftime('%H:%M:%S')}] Warning: Embedding vector dimension is {embedding_shape[1]}, expected 1024.")
    
    checkpoint_file = 'first_1k_checkpoint.npz'
    print(f"[{time.strftime('%H:%M:%S')}] Saving checkpoint to {checkpoint_file}...")
    np.savez_compressed(checkpoint_file, 
                        embeddings=embeddings, 
                        ids=df_subset['id'].values,
                        titles=df_subset['title'].values)
    
    # Measure memory
    end_mem = get_memory_usage()
    end_time = time.time()
    
    total_time = end_time - start_time
    mem_diff = end_mem - start_mem
    
    report = (
        f"--- EMBEDDING GENERATION SUMMARY ---\n"
        f"Model used             : BAAI/bge-m3\n"
        f"Device                 : {device}\n"
        f"Lines processed        : {len(df_subset)}\n"
        f"Batch size             : 64\n"
        f"Total time elapsed     : {total_time:.2f} seconds\n"
        f"Final Memory Usage     : {end_mem:.2f} MB\n"
        f"Memory Diff from start : +{mem_diff:.2f} MB\n"
        f"Checkpoint location    : {checkpoint_file}\n"
    )
    
    print("\n" + "="*50)
    print(report)
    print("="*50 + "\n")
    
    with open("embedding_report.txt", "w") as f:
        f.write(report)

if __name__ == "__main__":
    main()
