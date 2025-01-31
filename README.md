# obsidian-to-sql

a way to add your obsidian notes to a sql database for whatever use-cases you may have including RAG or other workflows you may come up with.

currently available for postgres databases, but may add other databases later



Clone and set up the repository:

```
git clone https://github.com/genesisdayrit/obsidian-to-sql.git
cd obsidian-to-sql
```
Create and configure your environment file:
`cp .env.example .env`

Edit .env with your values:

```
POSTGRES_USER=obsidian_user
POSTGRES_PASSWORD=obsidian_pass
POSTGRES_DB=obsidian_notes
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
OBSIDIAN_PATH=/path/to/your/obsidian/vault
```

Create Python virtual environment and install dependencies:

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Start PostgreSQL using Docker:

`docker-compose up -d`

Run the sync script:

`python sync_notes.py`

