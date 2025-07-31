# syntax=docker/dockerfile:1
FROM python:3.10-slim

# Tắt buffering output để log realtime
ENV PYTHONUNBUFFERED=1 \
    CHROMA_TELEMETRY_ENABLED=false

WORKDIR /app

# Cài hệ thống (nếu cần thêm lib cho PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy và cài dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn
COPY . /app

# Tạo và cấp quyền cho thư mục dữ liệu
RUN mkdir -p rag_v1/data rag_v1/chroma \
 && chmod -R a+rw rag_v1/data rag_v1/chroma

# (Tùy chọn) Build sẵn vector DB để startup nhanh hơn
RUN python rag_v1/create_db.py

EXPOSE 8000

# Khởi động FastAPI bằng uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
