# 📚 Kitap Keşif Sistemi

Yapay zeka destekli, hikaye tabanlı bir kitap keşif platformu. Sistem, kullanıcının sevdiği kitapları veya ilgi alanlarını analiz ederek benzer kitapları bulur. Ancak doğrudan kitap önermek yerine, **GPT ile kitabın temasından esinlenen spoiler-free bir kısa hikaye** üretir. Kullanıcı hikayeyi beğenirse kitap açığa çıkar!

## 🎯 Nasıl Çalışır?

```
1. Sevdiğin kitapları seç veya ne istediğini yaz
2. Sistem vektör benzerliği ile en uygun kitapları bulur
3. İlk kitap için GPT spoiler-free bir hikaye yazar
4. 👍 Beğendiysen → Kitap açığa çıkar (isim, yazar, kapak)
5. 👎 Beğenmediysen → Sonraki kitap için yeni hikaye (maks 6 deneme)
6. 6 kez beğenmezsen → "Maalesef bulamadık" mesajı
```

## 🏗️ Mimari

```
┌─────────────────────┐     ┌──────────────────────────────────┐
│     FRONTEND         │     │           BACKEND (FastAPI)       │
│  HTML / CSS / JS     │────▶│                                  │
│                      │     │  /api/books/search  → Kitap Ara  │
│  • Kitap Arama       │     │  /api/discover      → Hikaye Üret│
│  • Seçim (Chip UI)   │     │  /api/story/next    → Sonraki    │
│  • Hikaye Okuma      │     │  /api/story/reveal  → Kitabı Aç  │
│  • 👍 / 👎 Butonlar  │     │                                  │
│  • Kitap Reveal      │     │  BAAI/bge-m3 → Vektör Benzerliği │
└─────────────────────┘     │  OpenAI GPT  → Hikaye Üretimi    │
                             └──────────────────────────────────┘
```

## 🛠️ Teknolojiler

| Katman | Teknoloji |
|--------|-----------|
| **Frontend** | Vanilla HTML, CSS, JavaScript |
| **Backend** | Python, FastAPI, Uvicorn |
| **Embedding Model** | BAAI/bge-m3 (1024-dim, sentence-transformers) |
| **Hikaye Üretimi** | OpenAI GPT API (gpt-4o-mini) |
| **Veri** | Parquet formatında 445K+ kitap verisi |
| **Benzerlik** | Cosine Similarity ile vektör arama |

> ⚠️ **Not:** Şu an yalnızca ilk **1.000 kitap** için embedding üretilmiştir (`first_1k_checkpoint.npz`). Daha iyi ve çeşitli sonuçlar için tüm 445K+ kitabın embedding'i üretilebilir. Bunun için `generate_embeddings.py` dosyasındaki `df.head(1000)` satırını kaldırarak tüm veri seti üzerinde çalıştırabilirsiniz. Bu işlem donanıma bağlı olarak birkaç saat sürebilir.

## 📁 Proje Yapısı

```
kitap-oneri-sistemi/
├── app.py                    # FastAPI backend (ana uygulama)
├── .env                      # API key'ler (git'e gönderilmez!)
├── .gitignore                # Git'e gönderilmeyecek dosyalar
├── requirements.txt          # Python bağımlılıkları
├── generate_embeddings.py    # Embedding üretim scripti
├── search_books.py           # CLI kitap arama (test amaçlı)
├── process_books.py          # Veri temizleme scripti
├── first_1k_checkpoint.npz   # 1000 kitap embedding'i (git'e gönderilmez)
├── cleaned_data/
│   └── book_data             # Kitap verisi - parquet (git'e gönderilmez)
└── frontend/
    ├── index.html            # Ana sayfa
    ├── style.css             # Koyu tema, glassmorphism tasarım
    └── app.js                # Frontend mantığı
```

## 🚀 Kurulum

### 1. Repoyu klonla
```bash
git clone https://github.com/KULLANICI_ADI/kitap-oneri-sistemi.git
cd kitap-oneri-sistemi
```

### 2. Virtual environment oluştur
```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
# veya Windows: venv\Scripts\activate
```

### 3. Bağımlılıkları yükle
```bash
pip install -r requirements.txt
```

### 4. Veri dosyalarını hazırla

> ⚠️ Büyük veri dosyaları git'e dahil edilmez. Aşağıdaki dosyalar gereklidir:

- `cleaned_data/book_data` — Parquet formatında kitap verisi
- `first_1k_checkpoint.npz` — Önceden üretilmiş embedding'ler

Bu dosyaları takım arkadaşlarından veya paylaşılan depolama alanından alın.

Eğer embedding'leri sıfırdan üretmek isterseniz:
```bash
python generate_embeddings.py
```

### 5. API Key ayarla

Proje kök dizininde `.env` dosyası oluşturun:
```
OPENAI_API_KEY=sk-buraya-kendi-keyinizi-yazin
OPENAI_MODEL=gpt-4o-mini
```

API key almak için: https://platform.openai.com/api-keys

### 6. Uygulamayı başlat
```bash
python app.py
```

Tarayıcıda açın: **http://localhost:8000**

## 📸 Ekran Görüntüleri

### Ana Sayfa
Koyu tema, glassmorphism tasarım ile kitap arama ve hikaye keşif arayüzü.

### Hikaye Akışı
GPT tarafından üretilen spoiler-free hikayeyi okuyun, beğenip beğenmediğinize karar verin.

### Kitap Reveal
Hikayeyi beğendiğinizde, arkasındaki kitap kapak resmi, yazar adı ve açıklaması ile birlikte açığa çıkar.

## 🔧 API Endpoint'leri

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| `GET` | `/api/books/search?q=...` | Kitap arama (başlık/yazar) |
| `POST` | `/api/discover` | Benzer kitap bul + ilk hikaye üret |
| `POST` | `/api/story/next` | Sonraki kitap için hikaye üret |
| `POST` | `/api/story/reveal` | Beğenilen kitabın bilgilerini göster |

## 👥 Katkıda Bulunanlar

- Geliştirici: H. Atay

## 📄 Lisans

Bu proje eğitim amaçlıdır.
