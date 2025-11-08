import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    const sql = `
      SELECT 
        id,
        file_path,
        title,
        content,
        properties,
        path_metadata,
        file_created_at,
        file_modified_at,
        sync_modified_at
      FROM local.notes
      WHERE id = $1
    `;

    const result = await query(sql, [id]);

    if (result.rows.length === 0) {
      return NextResponse.json(
        { success: false, error: 'Note not found' },
        { status: 404 }
      );
    }

    return NextResponse.json({
      success: true,
      note: result.rows[0],
    });
  } catch (error) {
    console.error('Database error:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch note',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}

