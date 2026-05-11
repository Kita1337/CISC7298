const pdfFile = document.getElementById("pdfFile");
const chooseFileBtn = document.getElementById("chooseFileBtn");
const analyzeBtn = document.getElementById("analyzeBtn");
const exportBtn = document.getElementById("exportBtn");
const followupBtn = document.getElementById("followupBtn");
const followupInput = document.getElementById("followupInput");

const statusText = document.getElementById("statusText");
const currentMode = document.getElementById("currentMode");

const docStructure = document.getElementById("docStructure");
const docType = document.getElementById("docType");
const detectedTitle = document.getElementById("detectedTitle");
const ocrQuality = document.getElementById("ocrQuality");
const summary = document.getElementById("summary");
const keyData = document.getElementById("keyData");
const terms = document.getElementById("terms");
const advice = document.getElementById("advice");
const ocrPreview = document.getElementById("ocrPreview");
const followupResult = document.getElementById("followupResult");

chooseFileBtn.addEventListener("click", () => {
  pdfFile.click();
});

pdfFile.addEventListener("change", () => {
  if (pdfFile.files.length > 0) {
    const filename = pdfFile.files[0].name;

    fakeFileInput.value = filename;

    setStatus("Status: File selected", "success");
  } else {
    fakeFileInput.value = "No file selected";

    setStatus("Status: Waiting for file selection", "success");
  }
});

analyzeBtn.addEventListener("click", async () => {
  if (!pdfFile.files.length) {
    alert("Please select a file first.");
    return;
  }

  const selectedMode = document.querySelector('input[name="mode"]:checked').value;
  currentMode.textContent = getModeDisplayName(selectedMode);

  setStatus("Status: Analyzing...", "warning");
  setButtonLoading(analyzeBtn, "Analyzing...");

  followupResult.textContent = "Waiting for question...";
  followupInput.value = "";

  docType.textContent = "Analyzing...";
  detectedTitle.textContent = "Analyzing...";
  ocrQuality.textContent = "Analyzing...";
  summary.textContent = "Generating summary...";
  keyData.textContent = "Extracting key data...";
  terms.textContent = "Identifying important clauses...";
  advice.textContent = "Generating reading advice...";
  ocrPreview.textContent = "Extracting OCR text...";
  docStructure.textContent = "Analyzing...";
  ocrQuality.textContent = "Analyzing...";

  const formData = new FormData();
  formData.append("file", pdfFile.files[0]);
  formData.append("mode", selectedMode);

  try {
    const response = await fetch("/analyze", {
      method: "POST",
      body: formData
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Analysis failed");
    }

    docType.textContent = data.parsed["Document Type"] || "Not identified";
    detectedTitle.textContent = data.detected_title || "Not detected";
    ocrQuality.textContent = `${data.ocr_quality} (Score: ${data.ocr_score})`;
    summary.textContent = data.parsed["Summary"] || "No content extracted";
    keyData.textContent = data.parsed["Key Data"] || "No content extracted";
    terms.textContent = data.parsed["Important Clauses"] || "No content extracted";
    advice.textContent = data.parsed["Reading Advice"] || "No content extracted";
    ocrPreview.textContent = data.ocr_preview || "No OCR preview available";
    docStructure.textContent = data.doc_structure || "Unknown";
    ocrQuality.textContent = `${data.ocr_quality} (Score: ${data.ocr_score})`;

    setStatus("Status: Analysis completed", "success");
    restoreButton(analyzeBtn);
    setSuggestedQuestionByMode(selectedMode);
  } catch (err) {
    docType.textContent = "Analysis failed";
    detectedTitle.textContent = "Not generated";
    ocrQuality.textContent = "Unavailable";
    summary.textContent = err.message;
    keyData.textContent = "Not generated";
    terms.textContent = "Not generated";
    advice.textContent = "Not generated";
    ocrPreview.textContent = "Not generated";
    docStructure.textContent = "Unavailable";
    ocrQuality.textContent = "Unavailable";

    setStatus("Status: Analysis failed", "error");
    restoreButton(analyzeBtn);
  }
});

function appendChatMessage(role, content) {
  if (followupResult.textContent.trim() === "Waiting for question...") {
    followupResult.innerHTML = "";
  }

  const message = document.createElement("div");
  message.className = role === "user" ? "chat-message user-message" : "chat-message agent-message";

  const label = document.createElement("div");
  label.className = "chat-role";
  label.textContent = role === "user" ? "You" : "Agent";

  const body = document.createElement("div");
  body.className = "chat-content";
  body.textContent = content;

  message.appendChild(label);
  message.appendChild(body);
  followupResult.appendChild(message);

  followupResult.scrollTop = followupResult.scrollHeight;
}

async function sendFollowupQuestion() {
  const question = followupInput.value.trim();

  if (!question) {
    alert("Please enter your question.");
    return;
  }

  setStatus("Status: Processing follow-up question...", "warning");
  setButtonLoading(followupBtn, "Processing...");

  try {
    const response = await fetch("/followup", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ question })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Follow-up request failed");
    }

    appendChatMessage("user", data.question);
    appendChatMessage("agent", data.answer);

    setStatus("Status: Follow-up completed", "success");
    restoreButton(followupBtn);
    followupInput.value = "";
  } catch (err) {
    appendChatMessage("agent", `Error: ${err.message}`);
    setStatus("Status: Follow-up failed", "error");
    restoreButton(followupBtn);
  }
}

followupBtn.addEventListener("click", sendFollowupQuestion);
exportBtn.addEventListener("click", exportAnalysisResult);

followupInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    sendFollowupQuestion();
  }
});

function setSuggestedQuestionByMode(mode) {
  let suggested = "What are the three most important points in this document?";

  if (mode === "Recruitment Analysis") {
    suggested = "What are the most important qualification requirements in this recruitment document?";
  } else if (mode === "Contract Analysis") {
    suggested = "Which risk clauses in this contract require the most attention?";
  } else if (mode === "Academic Paper Analysis") {
    suggested = "What are the main contributions and methods of this paper?";
  }

  followupInput.value = suggested;
}

function exportAnalysisResult() {
  const content = [
    "DocuMind Agent Export Result",
    "==============================",
    "",
    `Document Type: ${docType.textContent}`,
    `Current Mode: ${currentMode.textContent}`,
    "",
    "Summary:",
    summary.textContent,
    "",
    "Key Data:",
    keyData.textContent,
    "",
    "Important Clauses:",
    terms.textContent,
    "",
    "Reading Advice:",
    advice.textContent,
    "",
    "Follow-up Record:",
    followupResult.textContent
  ].join("\n");

  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;

  const now = new Date();
  const timestamp = now.getFullYear() + "-"
    + String(now.getMonth() + 1).padStart(2, "0") + "-"
    + String(now.getDate()).padStart(2, "0") + "_"
    + String(now.getHours()).padStart(2, "0")
    + String(now.getMinutes()).padStart(2, "0")
    + String(now.getSeconds()).padStart(2, "0");

  a.download = `documind_analysis_${timestamp}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  URL.revokeObjectURL(url);
}

function setButtonLoading(button, loadingText) {
  button.dataset.originalText = button.textContent;
  button.textContent = loadingText;
  button.disabled = true;
  button.style.opacity = "0.7";
  button.style.cursor = "not-allowed";
}

function restoreButton(button) {
  if (button.dataset.originalText) {
    button.textContent = button.dataset.originalText;
  }
  button.disabled = false;
  button.style.opacity = "1";
  button.style.cursor = "pointer";
}

function setStatus(text, type) {
  statusText.textContent = text;
  statusText.className = `status ${type}`;
}

function getModeDisplayName(mode) {
  if (mode === "General Analysis") return "General Analysis";
  if (mode === "Recruitment Analysis") return "Recruitment Document";
  if (mode === "Contract Analysis") return "Contract Analysis";
  if (mode === "Academic Paper Analysis") return "Academic Paper";
  return mode;
}