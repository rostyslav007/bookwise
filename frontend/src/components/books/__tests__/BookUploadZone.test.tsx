import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
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

    // Use fireEvent to bypass the accept attribute filtering
    Object.defineProperty(fileInput, 'files', { value: [textFile], configurable: true });
    fireEvent.change(fileInput);

    expect(screen.getByText('Only PDF files are supported')).toBeInTheDocument();
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
});
