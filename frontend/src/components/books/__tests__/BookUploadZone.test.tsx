import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test/test-utils';
import { BookUploadZone } from '@/components/books/BookUploadZone';

const mockMutate = vi.fn();

vi.mock('@/api/books', () => ({
  useUploadBook: () => ({ mutate: mockMutate, isPending: false }),
}));

function getFileInput(): HTMLInputElement {
  const input = document.querySelector('input[type="file"]');
  if (!input) throw new Error('File input not found');
  return input as HTMLInputElement;
}

describe('BookUploadZone', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the upload zone with drag and drop text', () => {
    renderWithProviders(<BookUploadZone groupId="group-1" />);

    expect(screen.getByText(/drag & drop/i)).toBeInTheDocument();
  });

  it('shows error for non-PDF files selected via file input', () => {
    renderWithProviders(<BookUploadZone groupId="group-1" />);

    const fileInput = getFileInput();
    const textFile = new File(['hello'], 'test.txt', { type: 'text/plain' });

    Object.defineProperty(fileInput, 'files', { value: [textFile], configurable: true });
    fireEvent.change(fileInput);

    expect(screen.getByText('Only PDF and EPUB files are supported')).toBeInTheDocument();
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it('calls upload mutation for valid PDF files', async () => {
    const user = userEvent.setup();
    renderWithProviders(<BookUploadZone groupId="group-1" />);

    const fileInput = getFileInput();
    const pdfFile = new File(['pdf content'], 'book.pdf', { type: 'application/pdf' });

    await user.upload(fileInput, pdfFile);

    expect(mockMutate).toHaveBeenCalledWith(
      { file: expect.any(File), groupId: 'group-1' },
      expect.objectContaining({ onError: expect.any(Function) }),
    );
  });

  it('shows duplicate error message from 409 response', async () => {
    const { ApiError } = await import('@/api/client');

    mockMutate.mockImplementation((_payload: unknown, options: { onError: (err: Error) => void }) => {
      const error = new ApiError(409, 'Conflict', '{"detail":"This file was already stored in group \\"Spark\\" as \\"High Performance Spark\\"."}');
      options.onError(error);
    });

    const user = userEvent.setup();
    renderWithProviders(<BookUploadZone groupId="group-1" />);

    const fileInput = getFileInput();
    const pdfFile = new File(['pdf content'], 'book.pdf', { type: 'application/pdf' });

    await user.upload(fileInput, pdfFile);

    await waitFor(() => {
      expect(screen.getByText(/already stored in group/)).toBeInTheDocument();
    });
  });

  it('shows generic error for non-409 failures', async () => {
    mockMutate.mockImplementation((_payload: unknown, options: { onError: (err: Error) => void }) => {
      options.onError(new Error('Network error'));
    });

    const user = userEvent.setup();
    renderWithProviders(<BookUploadZone groupId="group-1" />);

    const fileInput = getFileInput();
    const pdfFile = new File(['pdf content'], 'book.pdf', { type: 'application/pdf' });

    await user.upload(fileInput, pdfFile);

    await waitFor(() => {
      expect(screen.getByText('Upload failed. Please try again.')).toBeInTheDocument();
    });
  });

  it('clears error when groupId changes', () => {
    const { rerender } = renderWithProviders(<BookUploadZone groupId="group-1" />);

    // Trigger an error
    const fileInput = getFileInput();
    const textFile = new File(['hello'], 'test.txt', { type: 'text/plain' });
    Object.defineProperty(fileInput, 'files', { value: [textFile], configurable: true });
    fireEvent.change(fileInput);

    expect(screen.getByText('Only PDF and EPUB files are supported')).toBeInTheDocument();

    // Change group
    rerender(<BookUploadZone groupId="group-2" />);

    expect(screen.queryByText('Only PDF and EPUB files are supported')).not.toBeInTheDocument();
  });
});
