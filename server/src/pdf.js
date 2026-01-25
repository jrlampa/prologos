import pdfParse from "pdf-parse";

export async function extractPdfText(buffer, { maxChars = 6000 } = {}) {
  if (!buffer || !buffer.length) return "";

  const data = await pdfParse(buffer);
  const txt = (data?.text ?? "").replace(/\s+\n/g, "\n").trim();
  if (!maxChars) return txt;
  return txt.slice(0, maxChars);
}

