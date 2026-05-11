import os
import re
from flask import Flask, render_template, request, jsonify
import fitz
from google import genai
import pytesseract
import re
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

app = Flask(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


LAST_DOCUMENT_TEXT = ""
LAST_ANALYSIS_RESULT = ""



from PIL import Image

def preprocess_image_for_ocr(img):

    gray = ImageOps.grayscale(img)

    scale = 2
    gray = gray.resize((gray.width * scale, gray.height * scale))

    enhancer = ImageEnhance.Contrast(gray)
    gray = enhancer.enhance(2.0)

    gray = gray.filter(ImageFilter.SHARPEN)

    threshold = 180
    binary = gray.point(lambda x: 255 if x > threshold else 0)

    return binary


def normalize_ocr_text(text):
    text = text.replace("\r", "\n")

    replacements = {
        "Si000": "$1000",
        "S1000": "$1000",
        "ﬁ": "fi",
        "ﬂ": "fl",
        "|": "I",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\n{3,}", "\n\n", text)

    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()


def score_ocr_text(text):
    if not text:
        return 0

    score = 0

    if len(text) > 30:
        score += 1
    if len(text) > 100:
        score += 1

    alnum_count = sum(c.isalnum() for c in text)
    ratio = alnum_count / max(len(text), 1)
    if ratio > 0.45:
        score += 1

    words = re.findall(r"[A-Za-z]{2,}", text)
    if len(words) >= 3:
        score += 1

    digits = re.findall(r"\d", text)
    if len(digits) >= 3:
        score += 1

    return score

def detect_document_structure(text: str) -> str:
    if not text or len(text) < 30:
        return "Low-text Image"

    words = text.split()
    lines = text.split("\n")

    avg_word_len = sum(len(w) for w in words) / max(len(words), 1)
    digit_ratio = sum(c.isdigit() for c in text) / max(len(text), 1)

    if digit_ratio > 0.3:
        return "Table-like Document"

    if avg_word_len < 3:
        return "Table-like Document"

    if len(lines) > 10 and len(words) / max(len(lines), 1) < 5:
        return "Table-like Document"

    return "Text Document"

def get_ocr_quality_label(score: int) -> str:
    if score >= 5:
        return "High"
    elif score >= 3:
        return "Medium"
    else:
        return "Low"

def extract_text_with_ocr(file_path):
    text = ""

    try:
        if file_path.lower().endswith(".pdf"):
            doc = fitz.open(file_path)
            try:
                all_pages_text = []

                for page in doc:
                    matrix = fitz.Matrix(2.5, 2.5)
                    pix = page.get_pixmap(matrix=matrix)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                    processed_img = preprocess_image_for_ocr(img)

                    candidates = []

                    text_1 = pytesseract.image_to_string(
                        processed_img,
                        lang="chi_sim+eng",
                        config="--oem 3 --psm 6"
                    )
                    candidates.append(text_1)

                    text_2 = pytesseract.image_to_string(
                        processed_img,
                        lang="chi_sim+eng",
                        config="--oem 3 --psm 11"
                    )
                    candidates.append(text_2)

                    text_3 = pytesseract.image_to_string(
                        img,
                        lang="chi_sim+eng",
                        config="--oem 3 --psm 6"
                    )
                    candidates.append(text_3)

                    best_text = max(candidates, key=score_ocr_text)
                    best_text = normalize_ocr_text(best_text)

                    all_pages_text.append(best_text)

                text = "\n".join(all_pages_text)

            finally:
                doc.close()

        else:
            img = Image.open(file_path)
            processed_img = preprocess_image_for_ocr(img)

            candidates = []

            text_1 = pytesseract.image_to_string(
                processed_img,
                lang="chi_sim+eng",
                config="--oem 3 --psm 6"
            )
            candidates.append(text_1)

            text_2 = pytesseract.image_to_string(
                processed_img,
                lang="chi_sim+eng",
                config="--oem 3 --psm 11"
            )
            candidates.append(text_2)

            text_3 = pytesseract.image_to_string(
                img,
                lang="chi_sim+eng",
                config="--oem 3 --psm 6"
            )
            candidates.append(text_3)

            text = max(candidates, key=score_ocr_text)
            text = normalize_ocr_text(text)

    except Exception as e:
        print("OCR Error:", e)

    print("OCR Preview (first 200 chars):")
    print(text[:200])
    print("OCR Quality Score:", score_ocr_text(text))

    return text.strip()

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    doc = fitz.open(file_path)
    try:
        for page in doc:
            page_text = page.get_text()
            if page_text:
                text += page_text + "\n"
    finally:
        doc.close()

    text = text.strip()

    if len(text) < 150:
        print("Low text detected, switching to OCR...")
        text = extract_text_with_ocr(file_path)

    return text

def detect_title(text: str) -> str:
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    candidates = []

    for line in lines[:10]:
        words = line.split()

        if 2 <= len(words) <= 6:

            if not line.islower():

                capital_ratio = sum(w[0].isupper() for w in words if w) / len(words)

                if capital_ratio > 0.6:
                    candidates.append(line)

    if candidates:
        return max(candidates, key=len)

    return "Not detected"


def clean_ocr_preview_text(text: str) -> str:
    lines = [line.strip() for line in text.split("\n")]
    lines = [line for line in lines if line]
    return "\n".join(lines[:20])


def build_prompt(mode: str, text: str) -> str:
    trimmed_text = text[:12000]

    common_format = """
Please strictly use English output and follow the exact structure below:

Document Type:
Summary:
Key Data:
Important Clauses:
Reading Advice:

Requirements:
1. All content must be in English.
2. "Key Data" must use bullet points starting with "- ".
3. "Important Clauses" must use bullet points starting with "- ".
4. "Summary" should be 2–4 concise sentences.
5. "Reading Advice" should include 1–3 clear suggestions.
"""

    if mode == "General Analysis":
        task = "You are a professional document analysis assistant. Perform a structured analysis of the following document."
    elif mode == "Recruitment Analysis":
        task = """
You are a recruitment document analysis assistant.
Focus on:
1. Target candidates
2. Time requirements
3. Qualification criteria
4. Restrictions or conditions
5. Most important information for applicants
"""
    elif mode == "Contract Analysis":
        task = """
You are a contract analysis assistant.
Focus on:
1. Contract type
2. Rights and obligations
3. Risk clauses
4. Time, payment, liabilities
5. Critical sections to review
"""
    elif mode == "Academic Paper Analysis":
        task = """
You are an academic paper analysis assistant.
Focus on:
1. Research topic
2. Core problem
3. Methodology
4. Results or contributions
5. Reading advice
"""
    else:
        task = "You are a professional document analysis assistant. Perform a structured analysis."

    return f"""
{task}

{common_format}

Document content:
{trimmed_text}
"""


def build_followup_prompt(document_text: str, previous_result: str, user_question: str) -> str:
    doc_trimmed = document_text[:10000]
    result_trimmed = previous_result[:5000]

    return f"""
You are an intelligent document analysis agent.

[Original Document]
{doc_trimmed}

[Previous Analysis Result]
{result_trimmed}

[User Question]
{user_question}

Answer the question based on the document and previous analysis.

Requirements:
1. Be concise and structured.
2. Use bullet points if appropriate.
3. Do NOT repeat the entire summary.
4. Focus only on answering the question.
"""

def generate_with_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=prompt
    )
    return response.text.strip()


def parse_structured_result(result_text: str) -> dict:
    sections = {
        "Document Type": "",
        "Summary": "",
        "Key Data": "",
        "Important Clauses": "",
        "Reading Advice": "",
    }

    title_map = {
        "document type": "Document Type",
        "summary": "Summary",
        "key data": "Key Data",
        "important clauses": "Important Clauses",
        "reading advice": "Reading Advice",
    }

    current_key = None
    lines = result_text.splitlines()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        normalized = line.replace("*", "").replace("#", "").strip()
        matched = False

        for raw_title, mapped_key in title_map.items():
            low = normalized.lower()
            if low.startswith(raw_title.lower() + "：") or low.startswith(raw_title.lower() + ":"):
                content = normalized[len(raw_title):].lstrip("：: ").strip()
                sections[mapped_key] = content
                current_key = mapped_key
                matched = True
                break

            if low == raw_title.lower() or low == raw_title.lower() + "：" or low == raw_title.lower() + ":":
                current_key = mapped_key
                matched = True
                break

        if matched:
            continue

        if current_key:
            if sections[current_key]:
                sections[current_key] += "\n" + normalized
            else:
                sections[current_key] = normalized

    return sections


@app.route("/")
def index():
    return render_template("index_v2.html")

@app.route("/v2")
def index_v2():
    return render_template("index_v2.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    global LAST_DOCUMENT_TEXT, LAST_ANALYSIS_RESULT

    if "file" not in request.files:
        return jsonify({"error": "No file received"}), 400

    file = request.files["file"]
    mode = request.form.get("mode", "General Analysis")

    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    filename = file.filename.lower()

    if not (
        filename.endswith(".pdf")
        or filename.endswith(".png")
        or filename.endswith(".jpg")
        or filename.endswith(".jpeg")
    ):
        return jsonify({"error": "Only PDF, PNG, JPG, JPEG are supported"}), 400

    os.makedirs("data", exist_ok=True)
    save_path = os.path.join("data", file.filename)
    file.save(save_path)

    try:
        if filename.endswith(".pdf"):
            text = extract_text_from_pdf(save_path)
        elif filename.endswith((".png", ".jpg", ".jpeg")):
            print("Image detected, using OCR...")
            text = extract_text_with_ocr(save_path)
        else:
            return jsonify({"error": "Unsupported file type"}), 400
        
        ocr_score = score_ocr_text(text)
        ocr_quality = get_ocr_quality_label(ocr_score)

        doc_structure = detect_document_structure(text)
        print("Detected Structure:", doc_structure)

        print("Extracted text length:", len(text))
        print("OCR Quality Label:", ocr_quality)

        if not text.strip():
            return jsonify({
                "error": "No valid text was extracted. The file may be a chart, a low-quality image, or a non-text document."
            }), 400

        if len(text) < 50:
            return jsonify({
                "error": "Extracted text is too short. The document may contain insufficient readable text for reliable analysis."
            }), 400

        if ocr_quality == "Low":
            return jsonify({
                "error": "OCR quality is too low for reliable analysis. Please use a clearer image or a text-based document."
            }), 400
        
        if doc_structure == "Table-like Document":
            return jsonify({
                "error": "The document appears to be table-like or data-heavy. Current OCR pipeline is not reliable for structured data such as charts or tables."
            }), 400

        print("Extracted text length:", len(text))

        LAST_DOCUMENT_TEXT = text

        prompt = build_prompt(mode, text)
        result = generate_with_gemini(prompt)
        LAST_ANALYSIS_RESULT = result

        parsed = parse_structured_result(result)

        detected_title = detect_title(text)
        ocr_preview = clean_ocr_preview_text(text)

        return jsonify({
            "success": True,
            "mode": mode,
            "raw_result": result,
            "parsed": parsed,
            "detected_title": detected_title,
            "ocr_preview": ocr_preview,
            "ocr_score": ocr_score,
            "ocr_quality": ocr_quality,
            "doc_structure": doc_structure
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/followup", methods=["POST"])
def followup():
    global LAST_DOCUMENT_TEXT, LAST_ANALYSIS_RESULT

    data = request.get_json()
    question = (data.get("question") or "").strip()

    if not LAST_DOCUMENT_TEXT or not LAST_ANALYSIS_RESULT:
        return jsonify({"error": "Please run document analysis first"}), 400

    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    try:
        prompt = build_followup_prompt(LAST_DOCUMENT_TEXT, LAST_ANALYSIS_RESULT, question)
        answer = generate_with_gemini(prompt)

        return jsonify({
            "success": True,
            "question": question,
            "answer": answer
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == "__main__":
    app.run(debug=True)