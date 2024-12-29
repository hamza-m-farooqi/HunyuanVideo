#!/usr/bin/env python3

import subprocess

def main():
    # 1. Download HunyuanVideo model into /home/HunyuanVideo/ckpts
    subprocess.run(
        [
            "huggingface-cli", "download",
            "tencent/HunyuanVideo",
            "--local-dir", "/home/HunyuanVideo/ckpts"
        ],
        check=True
    )

    # 3. Download llava-llama-3-8b-v1_1-transformers into /home/HunyuanVideo/ckpts
    subprocess.run(
        [
            "huggingface-cli", "download",
            "xtuner/llava-llama-3-8b-v1_1-transformers",
            "--local-dir", "/home/HunyuanVideo/ckpts/llava-llama-3-8b-v1_1-transformers"
        ],
        check=True
    )

    # 4. Run the preprocessing script to create text_encoder folder
    #    This separates the language model parts to reduce GPU memory usage.
    preprocess_script = "/home/HunyuanVideo/hyvideo/utils/preprocess_text_encoder_tokenizer_utils.py"
    subprocess.run(
        [
            "python", preprocess_script,
            "--input_dir", "/home/HunyuanVideo/ckpts/llava-llama-3-8b-v1_1-transformers",
            "--output_dir", "/home/HunyuanVideo/ckpts/text_encoder"
        ],
        check=True
    )

    # 5. Download CLIP model (text_encoder_2) from openai/clip-vit-large-patch14
    subprocess.run(
        [
            "huggingface-cli", "download",
            "openai/clip-vit-large-patch14",
            "--local-dir", "/home/HunyuanVideo/ckpts/text_encoder_2"
        ],
        check=True
    )

    print("All downloads and preprocessing steps are complete.")

if __name__ == "__main__":
    main()
