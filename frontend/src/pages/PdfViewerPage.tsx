import { useCallback, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
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

  const customTextRenderer = useCallback(
    (textItem: { str: string }) => {
      if (!highlightText) return escapeHtml(textItem.str);

      const src = textItem.str;
      const query = highlightText.toLowerCase();
      const parts: string[] = [];
      let remaining = src;

      while (remaining.length > 0) {
        const idx = remaining.toLowerCase().indexOf(query);
        if (idx === -1) {
          parts.push(escapeHtml(remaining));
          break;
        }
        if (idx > 0) parts.push(escapeHtml(remaining.slice(0, idx)));
        parts.push(
          `<mark class="bg-yellow-300/70">${escapeHtml(remaining.slice(idx, idx + highlightText.length))}</mark>`,
        );
        remaining = remaining.slice(idx + highlightText.length);
      }

      return parts.join("");
    },
    [highlightText],
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

        {highlightText && (
          <span className="rounded bg-yellow-200 px-2 py-0.5 text-xs text-yellow-900">
            Highlighting: &quot;{highlightText}&quot;
          </span>
        )}

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
