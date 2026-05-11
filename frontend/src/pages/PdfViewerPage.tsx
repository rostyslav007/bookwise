import { useCallback, useMemo, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import "./PdfViewerPage.css";
import {
  ArrowLeft,
  ZoomIn,
  ZoomOut,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";

pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

export default function PdfViewerPage() {
  const { bookId } = useParams<{ bookId: string }>();
  const [searchParams] = useSearchParams();
  const targetPage = Number(searchParams.get("page") ?? "1");
  const highlightText = searchParams.get("highlight");

  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(targetPage);
  const [scale, setScale] = useState(1.2);

  const pdfUrl = `/api/v1/books/${bookId}/pdf`;

  const highlightWords = useMemo(() => {
    if (!highlightText) return [];
    const stopWords = new Set([
      "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
      "have", "has", "had", "do", "does", "did", "will", "would", "could",
      "should", "may", "might", "shall", "can", "to", "of", "in", "for",
      "on", "with", "at", "by", "from", "as", "into", "through", "during",
      "before", "after", "and", "but", "or", "nor", "not", "so", "yet",
      "both", "either", "neither", "each", "every", "all", "any", "few",
      "more", "most", "other", "some", "such", "no", "only", "own", "same",
      "than", "too", "very", "just", "because", "if", "when", "that", "this",
      "it", "its", "then", "also", "about", "up", "out", "how", "what",
    ]);
    return highlightText
      .split(/\s+/)
      .filter((w) => w.length > 2 && !stopWords.has(w.toLowerCase()))
      .map((w) => w.toLowerCase());
  }, [highlightText]);

  const customTextRenderer = useCallback(
    (textItem: { str: string }) => {
      if (highlightWords.length === 0) return escapeHtml(textItem.str);

      const hasMatch = highlightWords.some((w) => textItem.str.toLowerCase().includes(w));
      if (!hasMatch) return escapeHtml(textItem.str);
      return `<mark style="background:rgba(250,204,21,0.4);mix-blend-mode:multiply;border-radius:2px">${escapeHtml(textItem.str)}</mark>`;
    },
    [highlightWords],
  );

  function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
    setNumPages(numPages);
    setCurrentPage(Math.min(targetPage, numPages));
  }

  return (
    <div className="flex h-screen flex-col">
      <div className="flex items-center justify-between border-b px-4 py-2">
        <Link
          to={`/books/${bookId}`}
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-4" />
          Back to book
        </Link>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
          >
            <ChevronLeft className="size-4" />
          </Button>
          <span className="text-sm">
            Page {currentPage} of {numPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setCurrentPage((p) => Math.min(numPages, p + 1))}
            disabled={currentPage >= numPages}
          >
            <ChevronRight className="size-4" />
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setScale((s) => Math.max(0.5, +(s - 0.2).toFixed(1)))}
          >
            <ZoomOut className="size-4" />
          </Button>
          <span className="text-sm">{Math.round(scale * 100)}%</span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setScale((s) => Math.min(3, +(s + 0.2).toFixed(1)))}
          >
            <ZoomIn className="size-4" />
          </Button>
        </div>
      </div>

      <div className="flex flex-1 justify-center overflow-auto bg-gray-100 py-4">
        <Document
          file={pdfUrl}
          onLoadSuccess={onDocumentLoadSuccess}
          loading={
            <p className="p-8 text-muted-foreground">Loading PDF...</p>
          }
        >
          <Page
            pageNumber={currentPage}
            scale={scale}
            customTextRenderer={customTextRenderer}
          />
        </Document>
      </div>
    </div>
  );
}
