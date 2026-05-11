# CISC7298 Final Project

# DocuMind

Intelligent Document Analysis and Structuring System

## Overview

DocuMind is a lightweight intelligent document analysis system that combines OCR technology and large language models for structured document understanding.

The system supports:
- PDF and image input
- OCR text extraction
- OCR quality evaluation
- Document structure detection
- LLM-based document summaries
- Follow-up question answering

The system is designed to improve document readability and assist users in understanding different types of documents through automated analysis.

---

## Technologies

- Python
- Flask
- PyMuPDF
- Tesseract OCR
- Gemini API
- HTML / CSS / JavaScript

---

## Installation

Install Python dependencies:

```bash
pip install -r requirements.txt
```

---

## Requirements

Before running the system, please ensure:

- Python 3.10 or above is installed
- Tesseract OCR is installed locally
- A valid Gemini API key is required

Example environment variable:

```bash
GEMINI_API_KEY=your_api_key
```

Tesseract OCR default path used in this project:

```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

---

## How to Run

Run the Flask application:

```bash
python main.py
```

After running the program, open the following address in your browser:

```text
http://127.0.0.1:5000
```

---

## Supported File Types

The system currently supports:

- PDF
- PNG
- JPG
- JPEG

---

## Features

### OCR Text Extraction
The system extracts text from both scanned images and PDF documents using Tesseract OCR and PDF parsing.

### OCR Quality Evaluation
The system evaluates OCR quality using a lightweight scoring mechanism based on:
- Text length
- Character ratio
- Readable words
- Numeric content

### Document Structure Detection
The system detects whether the document is:
- Text Document
- Table-like Document
- Low-text Image

### AI Document Analysis
The extracted text is analyzed using Gemini large language models to generate:
- Document summaries
- Key information
- Important clauses
- Reading advice

### Follow-up Question Answering
Users can ask additional questions after the initial analysis.

---

## Notes

This project is developed for academic purposes as the final project of CISC7298.
