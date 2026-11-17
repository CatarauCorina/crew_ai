import re
import pdfplumber
import fitz  # PyMuPDF
import os
import hashlib
import numpy as np
from urllib.parse import urlparse

from pathlib import Path

from PIL import Image

class PDFReader:
    def __init__(self, file_path):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found: {file_path}")
        self.file_path = file_path
        self.text_content = []
        self.tables = []
        self.image_paths = []
        self.links = {}

    def extract_text_and_tables(self):
        with pdfplumber.open(self.file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                # Extract text
                text = page.extract_text()
                if text:
                    self.text_content.append({"page": i + 1, "text": text})

                # Extract tables
                table = page.extract_table()
                if table:
                    self.tables.append({"page": i + 1, "table": table})
                
                # Extract links
                for idx,annot in enumerate(page.annots):
                    self.links[idx] = annot


    def filter_unique_links(self) -> list[str]:
    
        seen = set()
        filtered = []

        for link_obj in self.links.values():
            url = link_obj.get("uri", "")
            url = url.strip().lower()

            if not url.startswith("http"):
                continue  
            if url in seen:
                continue

            seen.add(url)
            filtered.append(url)

        return filtered
                

    def extract_images(self, output_folder="extracted_images"):
        os.makedirs(output_folder, exist_ok=True)
        pdf = fitz.open(self.file_path)
        seen_hashes = set()

        for page_index in range(len(pdf)):
            page = pdf[page_index]
            for img_index, img in enumerate(page.get_images(full=True)):
                xref = img[0]
                base_image = pdf.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]

                # Compute image hash
                image_hash = hashlib.md5(image_bytes).hexdigest()
                if image_hash in seen_hashes:
                    continue  # Skip duplicate
                seen_hashes.add(image_hash)

                image_filename = f"image_{image_hash}.{image_ext}"
                image_path = os.path.join(output_folder, image_filename)
                with open(image_path, "wb") as f:
                    f.write(image_bytes)
                self.image_paths.append(image_path)

    def read_all(self):
        self.extract_text_and_tables()
        self.extract_images()

    def get_summary(self):
        return {
            "text_pages": len(self.text_content),
            "tables_found": len(self.tables),
            "images_extracted": len(self.image_paths),
        }

    def print_summary(self):
        summary = self.get_summary()
        print("PDF Summary:")
        for key, val in summary.items():
            print(f"  {key}: {val}")




  
