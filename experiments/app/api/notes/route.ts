import { NextRequest, NextResponse } from 'next/server';
import { query } from '@/lib/db';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const search = searchParams.get('search');

    let sql = `
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
    `;

    const params: any[] = [];

    if (search && search.trim()) {
      sql += `
        WHERE 
          title ILIKE $1 
          OR content ILIKE $1 
          OR file_path ILIKE $1
      `;
      params.push(`%${search}%`);
    }

    sql += ' ORDER BY sync_modified_at DESC LIMIT 100';

    const result = await query(sql, params.length > 0 ? params : undefined);

    return NextResponse.json({
      success: true,
      notes: result.rows,
      count: result.rows.length,
    });
  } catch (error) {
    console.error('Database error:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch notes',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}

