"""init legacy tables

Memindahkan tiga tabel eksisting (Alfin, Arza, Atha) apa adanya ke satu database.

Revision ID: 001
Revises:
"""
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Alfin
    op.execute("""
        CREATE TABLE public.tabel_berita_ai (
            judul text,
            tanggal date,
            link varchar(255),
            gambar text,
            isi_berita text,
            sumber varchar(50),
            kategori_bisnis varchar(100),
            ringkasan_ai text,
            teknologi_dibahas text[],
            kategori_lisensi varchar(50),
            skor_relevansi_it integer,
            waktu_scrape timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT constraint_link_unique UNIQUE (link)
        )
    """)

    # Arza
    op.execute("""
        CREATE TABLE public.data_center_news (
            id serial NOT NULL,
            title text,
            published_date date,
            summary text,
            article_url text,
            image_url text,
            source varchar(100),
            tag varchar(200),
            sector varchar(100),
            topic varchar(100),
            relevance varchar(50),
            relevance_score integer,
            technology text,
            investment_value text,
            investment_type text,
            capacity text,
            capacity_type text,
            company text,
            organization text,
            project_location text,
            insight_type text,
            content text,
            subtopic text,
            pipeline_last_updated timestamp with time zone,
            record_type varchar(20) DEFAULT 'ARTICLE',
            summary_source varchar(50),
            summary_total_articles integer,
            summary_latest_article_date date,
            summary_generated_at timestamp without time zone,
            CONSTRAINT data_center_news_pkey PRIMARY KEY (id)
        )
    """)
    op.execute("""
        CREATE UNIQUE INDEX data_center_news_article_url_unique
            ON public.data_center_news USING btree (article_url)
    """)

    # Atha
    op.execute("""
        CREATE TABLE public.sector3_articles (
            article_id varchar(64) NOT NULL,
            title text NOT NULL,
            url text NOT NULL,
            published_at timestamp without time zone,
            channel text,
            source text,
            topic text,
            subtopic text,
            technology text,
            industry text,
            business_action text,
            impact text,
            insight_summary text,
            content_status text,
            scraped_at timestamp without time zone,
            event_type text,
            CONSTRAINT sector3_articles_pkey PRIMARY KEY (article_id),
            CONSTRAINT sector3_articles_url_key UNIQUE (url)
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE public.sector3_articles")
    op.execute("DROP TABLE public.data_center_news")
    op.execute("DROP TABLE public.tabel_berita_ai")