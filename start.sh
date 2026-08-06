#!/bin/bash
# Start FastAPI backend in the background
uvicorn client_bridge:app --host 127.0.0.1 --port 8000 &

# Start Streamlit frontend on Hugging Face's port
streamlit run app.py --server.port 7860 --server.address 0.0.0.0