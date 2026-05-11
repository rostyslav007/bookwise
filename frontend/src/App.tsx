import { lazy, Suspense } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { LibraryPage } from '@/pages/LibraryPage'
import { BookDetailPage } from '@/pages/BookDetailPage'
import { SearchPage } from '@/pages/SearchPage'
import { Layout } from '@/components/layout/Layout'

const PdfViewerPage = lazy(() => import('@/pages/PdfViewerPage'))
const EpubViewerPage = lazy(() => import('@/pages/EpubViewerPage'))

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout><LibraryPage /></Layout>} />
          <Route path="/search" element={<Layout><SearchPage /></Layout>} />
          <Route path="/books/:bookId" element={<Layout><BookDetailPage /></Layout>} />
          <Route
            path="/books/:bookId/view"
            element={
              <Suspense fallback={<div className="flex h-screen items-center justify-center"><p className="text-muted-foreground">Loading viewer...</p></div>}>
                <PdfViewerPage />
              </Suspense>
            }
          />
          <Route
            path="/books/:bookId/epub"
            element={
              <Suspense fallback={<div className="flex h-screen items-center justify-center"><p className="text-muted-foreground">Loading viewer...</p></div>}>
                <EpubViewerPage />
              </Suspense>
            }
          />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
