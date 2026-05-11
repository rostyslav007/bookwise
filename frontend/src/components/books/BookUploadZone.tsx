import { useEffect, useId, useRef, useState, type DragEvent, type ChangeEvent } from "react";
import { Upload } from "lucide-react";
import { useUploadBook } from "@/api/books";
import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";

function extractDetail(body: unknown): string | null {
  if (typeof body === "string") {
    try {
      const parsed = JSON.parse(body);
      if (typeof parsed.detail === "string") return parsed.detail;
    } catch {
      return body;
    }
  }
  return null;
}

interface BookUploadZoneProps {
  groupId: string;
}

export function BookUploadZone({ groupId }: BookUploadZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const uploadMutation = useUploadBook();
  const inputId = useId();
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setError(null);
  }, [groupId]);

  function validateAndUpload(file: File) {
    setError(null);

    const ALLOWED_TYPES = ["application/pdf", "application/epub+zip"];

    if (!ALLOWED_TYPES.includes(file.type)) {
      setError("Only PDF and EPUB files are supported");
      return;
    }

    uploadMutation.mutate(
      { file, groupId },
      {
        onError: (err) => {
          if (err instanceof ApiError && err.status === 409) {
            const detail = extractDetail(err.body);
            setError(detail || "This file already exists in your library.");
          } else {
            setError("Upload failed. Please try again.");
          }
        },
      },
    );
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragOver(false);

    const file = event.dataTransfer.files[0];
    if (file) {
      validateAndUpload(file);
    }
  }

  function handleDragOver(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragOver(true);
  }

  function handleDragLeave(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragOver(false);
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) {
      validateAndUpload(file);
    }
    event.target.value = "";
  }

  return (
    <div className="flex flex-col items-center gap-3">
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={`flex w-full flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-8 transition-colors ${
          isDragOver
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/30 hover:border-muted-foreground/50"
        }`}
      >
        <Upload className="h-8 w-8 text-muted-foreground" />

        {uploadMutation.isPending ? (
          <p className="text-sm text-muted-foreground">Uploading...</p>
        ) : (
          <p className="text-sm text-muted-foreground">
            Drag & drop a PDF or EPUB here
          </p>
        )}
      </div>

      {!uploadMutation.isPending && (
        <div>
          <input
            ref={fileInputRef}
            id={inputId}
            type="file"
            accept=".pdf,.epub,application/pdf,application/epub+zip"
            style={{ display: "none" }}
            onChange={handleFileChange}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="mr-2 size-4" />
            Browse files
          </Button>
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}
