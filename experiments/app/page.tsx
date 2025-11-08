'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

interface Note {
  id: string;
  file_path: string;
  title: string;
  content: string;
  properties: any;
  path_metadata: any;
  file_created_at: string;
  file_modified_at: string;
  sync_modified_at: string;
}

export default function Home() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchNotes = useCallback(async (searchTerm: string) => {
    setLoading(true);
    setError(null);
    try {
      const url = searchTerm 
        ? `/api/notes?search=${encodeURIComponent(searchTerm)}`
        : '/api/notes';
      
      const response = await fetch(url);
      const data = await response.json();

      if (data.success) {
        setNotes(data.notes);
      } else {
        setError(data.error || 'Failed to fetch notes');
      }
    } catch (err) {
      setError('Failed to connect to the API');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchNotes('');
  }, [fetchNotes]);

  // Debounced search as user types
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchNotes(search);
    }, 300); // 300ms debounce

    return () => clearTimeout(timer);
  }, [search, fetchNotes]);

  const handleClear = () => {
    setSearch('');
  };

  const truncate = (str: string | null, length: number) => {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Obsidian Notes Database
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Search and browse your notes
          </p>
        </div>

        {/* Search Bar */}
        <div className="mb-6">
          <div className="flex gap-2">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title, content, or file path..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:border-gray-700 dark:text-white"
              autoFocus
            />
            {search && (
              <button
                type="button"
                onClick={handleClear}
                className="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors font-medium dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg dark:bg-red-900/20 dark:border-red-800">
            <p className="text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        ) : (
          <>
            {/* Results Count */}
            <div className="mb-4 text-sm text-gray-600 dark:text-gray-400">
              {notes.length} {notes.length === 1 ? 'note' : 'notes'} found
            </div>

            {/* Notes Table */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-900">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Title
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        File Path
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Content Preview
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        Modified
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {notes.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                          No notes found
                        </td>
                      </tr>
                    ) : (
                      notes.map((note) => (
                        <tr key={note.id} className="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors cursor-pointer">
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            <Link 
                              href={`/notes/${note.id}`}
                              className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                            >
                              {truncate(note.title, 40)}
                            </Link>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                            <Link 
                              href={`/notes/${note.id}`}
                              className="hover:text-gray-900 dark:hover:text-gray-200"
                            >
                              {truncate(note.file_path, 50)}
                            </Link>
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400 max-w-md">
                            <Link 
                              href={`/notes/${note.id}`}
                              className="hover:text-gray-900 dark:hover:text-gray-200"
                            >
                              {truncate(note.content, 100)}
                            </Link>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                            <Link 
                              href={`/notes/${note.id}`}
                              className="hover:text-gray-900 dark:hover:text-gray-200"
                            >
                              {note.file_modified_at ? new Date(note.file_modified_at).toLocaleDateString() : 'N/A'}
                            </Link>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
