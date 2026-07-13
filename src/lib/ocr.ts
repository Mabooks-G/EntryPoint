/**
 * Client-side OCR utility using Tesseract.js + pdfjs-dist.
 * Handles images (PNG, JPG, etc.) directly and renders PDFs to canvas first.
 */

import { createWorker } from "tesseract.js";
import * as pdfjsLib from "pdfjs-dist";

// Set the PDF.js worker to use a CDN-hosted copy to avoid bundling issues
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`;

// ─── Types ───────────────────────────────────────────

export interface OcrResult {
  text: string;
  confidence: number;
}

// ─── Helpers ─────────────────────────────────────────

const IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".tif", ".webp"];

function isImageFile(filename: string): boolean {
  const ext = filename.toLowerCase().split(".").pop();
  return ext ? IMAGE_EXTENSIONS.includes(`.${ext}`) : false;
}

function isPdfFile(filename: string): boolean {
  return filename.toLowerCase().endsWith(".pdf");
}

// ─── PDF Rendering ───────────────────────────────────

async function renderPdfToCanvas(file: File): Promise<HTMLCanvasElement[]> {
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
  const canvases: HTMLCanvasElement[] = [];

  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const viewport = page.getViewport({ scale: 2 }); // 2x for better OCR accuracy
    const canvas = document.createElement("canvas");
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    const ctx = canvas.getContext("2d")!;
    //await page.render({ canvasContext: ctx, viewport }).promise;
    await page.render({ canvas: ctx.canvas, canvasContext: ctx, viewport }).promise;
    canvases.push(canvas);
  }

  return canvases;
}

// ─── OCR Entry Point ─────────────────────────────────

/**
 * Extract text from a file (image or PDF) using client-side OCR.
 * Returns the extracted text and average confidence.
 */
export async function extractTextFromFile(file: File): Promise<OcrResult> {
  const filename = file.name;

  if (isPdfFile(filename)) {
    // PDF → canvas → OCR
    const canvases = await renderPdfToCanvas(file);
    if (canvases.length === 0) return { text: "", confidence: 0 };

    const worker = await createWorker("eng");
    let fullText = "";
    let totalConfidence = 0;

    try {
      for (const canvas of canvases) {
        const { data } = await worker.recognize(canvas);
        fullText += data.text + "\n";
        totalConfidence += data.confidence;
      }
      return {
        text: fullText.trim(),
        confidence: Math.round(totalConfidence / canvases.length),
      };
    } finally {
      await worker.terminate();
    }
  } else if (isImageFile(filename)) {
    // Direct OCR on image
    const worker = await createWorker("eng");
    try {
      const { data } = await worker.recognize(file);
      return {
        text: data.text.trim(),
        confidence: Math.round(data.confidence),
      };
    } finally {
      await worker.terminate();
    }
  } else {
    // Unsupported format — return empty
    return { text: "", confidence: 0 };
  }
}

/**
 * Extract text from multiple files, returning a map of filename → OcrResult.
 */
export async function extractTextFromFiles(files: File[]): Promise<Map<string, OcrResult>> {
  const results = new Map<string, OcrResult>();
  const supported = files.filter((f) => isImageFile(f.name) || isPdfFile(f.name));

  // Process files one at a time to avoid overwhelming the browser
  for (const file of supported) {
    try {
      const result = await extractTextFromFile(file);
      results.set(file.name, result);
    } catch (err) {
      console.warn(`OCR failed for ${file.name}:`, err);
      results.set(file.name, { text: "", confidence: 0 });
    }
  }

  return results;
}