'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
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

export default function NotePage() {
  const params = useParams();
  const router = useRouter();
  const [note, setNote] = useState<Note | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchNote = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/notes/${params.id}`);
        const data = await response.json();

        if (data.success) {
          setNote(data.note);
        } else {
          setError(data.error || 'Failed to fetch note');
        }
      } catch (err) {
        setError('Failed to connect to the API');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    if (params.id) {
      fetchNote();
    }
  }, [params.id]);

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const formatJSON = (obj: any) => {
    if (!obj) return 'None';
    return JSON.stringify(obj, null, 2);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-5xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
          <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !note) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
        <div className="max-w-5xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
          <Link
            href="/"
            className="inline-flex items-center text-blue-600 hover:text-blue-700 dark:text-blue-400 mb-6"
          >
            ← Back to all notes
          </Link>
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 dark:bg-red-900/20 dark:border-red-800">
            <p className="text-red-800 dark:text-red-200">{error || 'Note not found'}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="max-w-5xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Back Button */}
        <Link
          href="/"
          className="inline-flex items-center text-blue-600 hover:text-blue-700 dark:text-blue-400 mb-6 font-medium"
        >
          ← Back to all notes
        </Link>

        {/* Note Content */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
          {/* Header */}
          <div className="border-b border-gray-200 dark:border-gray-700 px-6 py-6">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              {note.title || 'Untitled'}
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {note.file_path}
            </p>
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 px-6 py-6 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-200 dark:border-gray-700">
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                Created
              </p>
              <p className="text-sm text-gray-900 dark:text-white">
                {formatDate(note.file_created_at)}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                Modified
              </p>
              <p className="text-sm text-gray-900 dark:text-white">
                {formatDate(note.file_modified_at)}
              </p>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                Last Synced
              </p>
              <p className="text-sm text-gray-900 dark:text-white">
                {formatDate(note.sync_modified_at)}
              </p>
            </div>
          </div>

          {/* Content */}
          <div className="px-6 py-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
              Content
            </h2>
            <div className="prose dark:prose-invert max-w-none">
              <pre className="whitespace-pre-wrap bg-gray-50 dark:bg-gray-900 rounded-lg p-4 text-sm text-gray-800 dark:text-gray-200 overflow-x-auto">
                {note.content || 'No content'}
              </pre>
            </div>
          </div>

          {/* Properties */}
          {note.properties && Object.keys(note.properties).length > 0 && (
            <div className="px-6 py-6 border-t border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                Properties
              </h2>
              <pre className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 text-sm text-gray-800 dark:text-gray-200 overflow-x-auto">
                {formatJSON(note.properties)}
              </pre>
            </div>
          )}

          {/* Path Metadata */}
          {note.path_metadata && Object.keys(note.path_metadata).length > 0 && (
            <div className="px-6 py-6 border-t border-gray-200 dark:border-gray-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                Path Metadata
              </h2>
              <pre className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 text-sm text-gray-800 dark:text-gray-200 overflow-x-auto">
                {formatJSON(note.path_metadata)}
              </pre>
            </div>
          )}

          {/* Note ID */}
          <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900/50 border-t border-gray-200 dark:border-gray-700">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Note ID: <span className="font-mono">{note.id}</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

