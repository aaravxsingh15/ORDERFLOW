# API image: docker build -t orderflow-api . && docker run -p 8000:8000 orderflow-api
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
COPY ml ml
COPY data data
COPY scripts scripts
# train at build time so the container starts instantly and the models match the installed scikit-learn
RUN python scripts/train_all.py
ENV ORDERFLOW_CORS_ORIGINS=http://localhost:3000
WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
