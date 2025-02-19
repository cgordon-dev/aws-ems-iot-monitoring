FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .

# Upgrade pip, force-reinstall a compatible version of NumPy, then install the rest.
RUN pip install --upgrade pip && \
    pip install numpy==1.21.6 --force-reinstall && \
    pip install -r requirements.txt

COPY app.py .

EXPOSE 8501
ENV PORT=8501

CMD ["streamlit", "run", "app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]