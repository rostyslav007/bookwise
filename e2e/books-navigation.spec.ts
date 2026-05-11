import { test, expect } from '@playwright/test';
import path from 'path';
import fs from 'fs';

const UNIQUE_SUFFIX = Date.now();

test.describe('BooksNavigationMCP', () => {
  test.describe('Group CRUD', () => {
    test('should display the library page with Groups heading', async ({ page }) => {
      await page.goto('/');

      await expect(page.getByRole('heading', { name: 'Groups' })).toBeVisible();
      await expect(page.getByText('Select a group or upload books')).toBeVisible();
    });

    test('should create a new group', async ({ page }) => {
      await page.goto('/');
      const groupName = `Create Group ${UNIQUE_SUFFIX}`;

      await page.getByRole('button', { name: 'New Group' }).click();

      const dialog = page.getByRole('dialog', { name: 'New Group' });
      await expect(dialog).toBeVisible();

      await dialog.getByRole('textbox', { name: 'Group name' }).fill(groupName);
      await dialog.getByRole('button', { name: 'Save' }).click();

      await expect(dialog).not.toBeVisible();
      await expect(page.getByText(groupName)).toBeVisible();
    });

    test('should select a group and show upload zone', async ({ page }) => {
      await page.goto('/');
      const groupName = `Select Group ${UNIQUE_SUFFIX}`;

      // Create group first
      await page.getByRole('button', { name: 'New Group' }).click();
      await page.getByRole('dialog', { name: 'New Group' }).getByRole('textbox', { name: 'Group name' }).fill(groupName);
      await page.getByRole('dialog', { name: 'New Group' }).getByRole('button', { name: 'Save' }).click();
      await expect(page.getByRole('dialog')).not.toBeVisible();

      // Select it
      await page.getByText(groupName).click();

      // Verify upload zone appears
      await expect(page.getByText('Drag & drop a PDF here')).toBeVisible();
    });

    test('should rename a group', async ({ page }) => {
      await page.goto('/');
      const originalName = `Rename Me ${UNIQUE_SUFFIX}`;
      const renamedName = `Renamed ${UNIQUE_SUFFIX}`;

      // Create a group
      await page.getByRole('button', { name: 'New Group' }).click();
      await page.getByRole('dialog', { name: 'New Group' }).getByRole('textbox', { name: 'Group name' }).fill(originalName);
      await page.getByRole('dialog', { name: 'New Group' }).getByRole('button', { name: 'Save' }).click();
      await expect(page.getByRole('dialog')).not.toBeVisible();
      await expect(page.getByText(originalName)).toBeVisible();

      // Open actions menu
      await page.getByRole('button', { name: `Actions for ${originalName}` }).click({ force: true });
      await page.getByRole('menuitem', { name: 'Rename' }).click();

      // Fill rename dialog
      const renameDialog = page.getByRole('dialog', { name: 'Rename Group' });
      await expect(renameDialog).toBeVisible();
      await renameDialog.getByRole('textbox', { name: 'Group name' }).clear();
      await renameDialog.getByRole('textbox', { name: 'Group name' }).fill(renamedName);
      await renameDialog.getByRole('button', { name: 'Save' }).click();

      await expect(renameDialog).not.toBeVisible();
      await expect(page.getByText(renamedName)).toBeVisible();
      await expect(page.getByText(originalName)).not.toBeVisible();
    });

    test('should delete a group', async ({ page }) => {
      await page.goto('/');
      const groupName = `Delete Me ${UNIQUE_SUFFIX}`;

      // Create a group
      await page.getByRole('button', { name: 'New Group' }).click();
      await page.getByRole('dialog', { name: 'New Group' }).getByRole('textbox', { name: 'Group name' }).fill(groupName);
      await page.getByRole('dialog', { name: 'New Group' }).getByRole('button', { name: 'Save' }).click();
      await expect(page.getByRole('dialog')).not.toBeVisible();
      await expect(page.getByText(groupName)).toBeVisible();

      // Open actions menu
      await page.getByRole('button', { name: `Actions for ${groupName}` }).click({ force: true });
      await page.getByRole('menuitem', { name: 'Delete' }).click();

      // Confirm deletion
      const deleteDialog = page.getByRole('dialog', { name: 'Delete Group' });
      await expect(deleteDialog).toBeVisible();
      await deleteDialog.getByRole('button', { name: 'Delete' }).click();

      await expect(deleteDialog).not.toBeVisible();
      await expect(page.getByText(groupName)).not.toBeVisible();
    });
  });

  test.describe('Book Delete', () => {
    test('should delete a book from detail page', async ({ page, request }) => {
      await page.goto('/');
      const groupName = `Delete Book Group ${UNIQUE_SUFFIX}`;

      // Create and select a group
      await page.getByRole('button', { name: 'New Group' }).click();
      await page.getByRole('dialog', { name: 'New Group' }).getByRole('textbox', { name: 'Group name' }).fill(groupName);
      await page.getByRole('dialog', { name: 'New Group' }).getByRole('button', { name: 'Save' }).click();
      await expect(page.getByRole('dialog')).not.toBeVisible();
      await page.getByText(groupName).click();
      await expect(page.getByText('Drag & drop a PDF here')).toBeVisible();

      // Build a minimal valid PDF buffer
      const pdfContent = Buffer.from(
        '%PDF-1.4\n' +
        '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n' +
        '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n' +
        '3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n' +
        'xref\n0 4\n' +
        '0000000000 65535 f \n' +
        '0000000009 00000 n \n' +
        '0000000058 00000 n \n' +
        '0000000115 00000 n \n' +
        'trailer\n<< /Size 4 /Root 1 0 R >>\n' +
        'startxref\n190\n%%EOF',
      );

      // Upload via hidden file input
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles({
        name: 'book-to-delete.pdf',
        mimeType: 'application/pdf',
        buffer: pdfContent,
      });

      // Wait for the book card to appear
      await expect(page.getByText('book-to-delete')).toBeVisible({ timeout: 10_000 });

      // Get the book ID from the API
      const booksResponse = await request.get('/api/v1/books/');
      const books = await booksResponse.json();
      const uploadedBook = books.find((b: { title: string }) => b.title === 'book-to-delete');
      expect(uploadedBook).toBeTruthy();
      const bookId = uploadedBook.id;

      // Navigate directly to the book detail page
      await page.goto(`/books/${bookId}`);
      await expect(page.getByRole('button', { name: 'Delete book' })).toBeVisible({ timeout: 10_000 });

      // Click Delete book
      await page.getByRole('button', { name: 'Delete book' }).click();

      // Confirm in the dialog
      const deleteDialog = page.getByRole('alertdialog');
      await expect(deleteDialog).toBeVisible();
      await deleteDialog.getByRole('button', { name: 'Delete' }).click();

      // Verify redirect to library page
      await expect(page).toHaveURL('/', { timeout: 10_000 });
      await expect(page.getByRole('heading', { name: 'Groups' })).toBeVisible();

      // Verify the book is no longer shown
      await expect(page.getByText('book-to-delete')).not.toBeVisible();
    });
  });

  test.describe('PDF Upload', () => {
    test('should upload a PDF and display the book card', async ({ page }) => {
      await page.goto('/');
      const groupName = `Upload Group ${UNIQUE_SUFFIX}`;

      // Create and select a group
      await page.getByRole('button', { name: 'New Group' }).click();
      await page.getByRole('dialog', { name: 'New Group' }).getByRole('textbox', { name: 'Group name' }).fill(groupName);
      await page.getByRole('dialog', { name: 'New Group' }).getByRole('button', { name: 'Save' }).click();
      await expect(page.getByRole('dialog')).not.toBeVisible();
      await page.getByText(groupName).click();
      await expect(page.getByText('Drag & drop a PDF here')).toBeVisible();

      // Build a minimal valid PDF buffer
      const pdfContent = Buffer.from(
        '%PDF-1.4\n' +
        '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n' +
        '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n' +
        '3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n' +
        'xref\n0 4\n' +
        '0000000000 65535 f \n' +
        '0000000009 00000 n \n' +
        '0000000058 00000 n \n' +
        '0000000115 00000 n \n' +
        'trailer\n<< /Size 4 /Root 1 0 R >>\n' +
        'startxref\n190\n%%EOF',
      );

      // Upload via hidden file input
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles({
        name: 'test-design-patterns.pdf',
        mimeType: 'application/pdf',
        buffer: pdfContent,
      });

      // Book card should appear (title derived from filename)
      await expect(page.getByText('test-design-patterns')).toBeVisible({ timeout: 10_000 });

      // Wait for processing to settle; without Claude API credits, status ends up as "error"
      const statusBadge = page
        .locator('text=processing')
        .or(page.locator('text=error'))
        .or(page.locator('text=ready'));
      await expect(statusBadge.first()).toBeVisible({ timeout: 15_000 });
    });
  });
});
