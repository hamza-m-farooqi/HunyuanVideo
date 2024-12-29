# Base image
FROM hunyuanvideo/hunyuanvideo:cuda_12

ENV HF_HUB_ENABLE_HF_TRANSFER=0

# Set the working directory
WORKDIR /home

# Copy everything into the image
COPY . /home
# Install Python dependencies (Worker Template)
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r requirements-new.txt

RUN python3 /home/HunyuanVideo/inferene_server/download_models.py

CMD python3 -u /home/HunyuanVideo/inferene_server/run_pod_handler.py