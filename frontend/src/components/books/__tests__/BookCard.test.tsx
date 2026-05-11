import { describe, it, expect, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/test/test-utils';
import { BookCard } from '@/components/books/BookCard';
import type { Book } from '@/api/books';

vi.mock('@/hooks/useSSE', () => ({
  useSSE: () => null,
}));

vi.mock('@/components/books/ProgressBar', () => ({
  ProgressBar: () => null,
}));

function createBook(overrides: Partial<Book> = {}): Book {
  return {
    id: 'book-1',
    group_id: 'group-1',
    title: 'Clean Code',
    author: null,
    file_path: '/books/clean-code.pdf',
    page_count: null,
    status: 'ready',
    created_at: '2024-01-01',
    updated_at: '2024-01-01',
    format: 'pdf',
    ...overrides,
  };
}

describe('BookCard', () => {
  it('renders the book title', () => {
    renderWithProviders(<BookCard book={createBook()} />);

    expect(screen.getByText('Clean Code')).toBeInTheDocument();
  });

  it('shows status badge with correct text', () => {
    renderWithProviders(<BookCard book={createBook({ status: 'ready' })} />);

    expect(screen.getByText('ready')).toBeInTheDocument();
  });

  it('shows "processing" badge with animate-pulse class', () => {
    renderWithProviders(<BookCard book={createBook({ status: 'processing' })} />);

    const badge = screen.getByText('processing');
    expect(badge).toBeInTheDocument();
    expect(badge.className).toContain('animate-pulse');
  });

  it('shows author when available', () => {
    renderWithProviders(
      <BookCard book={createBook({ author: 'Robert C. Martin' })} />,
    );

    expect(screen.getByText('Robert C. Martin')).toBeInTheDocument();
  });

  it('shows page count when available', () => {
    renderWithProviders(
      <BookCard book={createBook({ page_count: 464 })} />,
    );

    expect(screen.getByText('464 pages')).toBeInTheDocument();
  });

  it('does not show author when null', () => {
    renderWithProviders(<BookCard book={createBook({ author: null })} />);

    expect(screen.queryByText('Robert C. Martin')).not.toBeInTheDocument();
  });
});
