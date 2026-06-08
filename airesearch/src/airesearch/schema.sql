create table if not exists papers (
    paper_key text primary key,
    title text,
    authors_json text not null default '[]',
    year integer,
    venue text,
    ids_json text not null default '{}',
    paper_dir text not null,
    meta_json text not null default '{}',
    created_at text not null,
    updated_at text not null
);

create table if not exists paper_sources (
    id integer primary key autoincrement,
    paper_key text not null references papers(paper_key) on delete cascade,
    source_type text not null,
    source_value text not null,
    created_at text not null,
    unique(paper_key, source_type, source_value)
);

create table if not exists paper_artifacts (
    id integer primary key autoincrement,
    paper_key text not null references papers(paper_key) on delete cascade,
    artifact_type text not null,
    path text not null,
    sha256 text not null,
    size_bytes integer not null,
    updated_at text not null,
    unique(paper_key, artifact_type, path)
);

create table if not exists ingest_runs (
    id integer primary key autoincrement,
    manifest_path text,
    total_items integer not null default 0,
    success_count integer not null default 0,
    failed_count integer not null default 0,
    duplicate_count integer not null default 0,
    skipped_count integer not null default 0,
    started_at text not null,
    finished_at text,
    status text not null
);

create table if not exists ingest_items (
    id integer primary key autoincrement,
    run_id integer not null references ingest_runs(id) on delete cascade,
    line_number integer not null,
    raw_input text not null,
    status text not null,
    resolved_paper_key text,
    stdout text not null default '',
    stderr text not null default '',
    error text not null default '',
    started_at text not null,
    finished_at text,
    unique(run_id, line_number)
);

create table if not exists sync_events (
    id integer primary key autoincrement,
    paper_db_path text not null,
    papers_seen integer not null,
    artifacts_seen integer not null,
    started_at text not null,
    finished_at text not null,
    status text not null,
    error text not null default ''
);


create table if not exists research_profiles (
    name text primary key,
    description text not null,
    keywords_json text not null,
    preferred_venues_json text not null,
    preferred_organizations_json text not null,
    preferred_scholars_json text not null,
    exception_keywords_json text not null,
    primary_since text not null,
    exception_since text not null,
    created_at text not null,
    updated_at text not null
);

create table if not exists discovery_runs (
    id integer primary key autoincrement,
    profile_name text not null references research_profiles(name) on delete cascade,
    provider_names_json text not null default '[]',
    total_seen integer not null default 0,
    stored_count integer not null default 0,
    skipped_count integer not null default 0,
    started_at text not null,
    finished_at text,
    status text not null,
    error text not null default ''
);

create table if not exists research_candidates (
    id integer primary key autoincrement,
    profile_name text not null references research_profiles(name) on delete cascade,
    source text not null,
    source_id text not null,
    title text not null,
    url text not null default '',
    authors_json text not null default '[]',
    organizations_json text not null default '[]',
    venue text not null default '',
    published_date text not null default '',
    year integer,
    abstract text not null default '',
    score real not null default 0,
    score_reasons_json text not null default '[]',
    status text not null default 'candidate',
    created_at text not null,
    updated_at text not null,
    unique(profile_name, source, source_id)
);

create table if not exists candidate_papers (
    canonical_key text primary key,
    title text not null,
    url text not null default '',
    venue text not null default '',
    published_date text not null default '',
    year integer,
    abstract text not null default '',
    best_score real not null default 0,
    profiles_json text not null default '[]',
    sources_json text not null default '[]',
    source_urls_json text not null default '[]',
    candidate_ids_json text not null default '[]',
    status text not null default 'candidate',
    created_at text not null,
    updated_at text not null
);

create table if not exists candidate_paper_links (
    canonical_key text not null references candidate_papers(canonical_key) on delete cascade,
    research_candidate_id integer not null references research_candidates(id) on delete cascade,
    profile_name text not null,
    source text not null,
    score real not null default 0,
    created_at text not null,
    primary key(canonical_key, research_candidate_id)
);

create table if not exists extraction_runs (
    id integer primary key autoincrement,
    extractor_name text not null,
    extractor_version text not null,
    paper_key text,
    limit_count integer,
    papers_seen integer not null default 0,
    cards_written integer not null default 0,
    nodes_written integer not null default 0,
    edges_written integer not null default 0,
    provenance_written integer not null default 0,
    started_at text not null,
    finished_at text,
    status text not null,
    error text not null default ''
);

create table if not exists paper_cards (
    paper_key text primary key references papers(paper_key) on delete cascade,
    title text not null default '',
    authors_json text not null default '[]',
    year integer,
    venue text not null default '',
    ids_json text not null default '{}',
    artifact_types_json text not null default '[]',
    source_dir text not null default '',
    status text not null default 'complete',
    extractor_version text not null,
    created_at text not null,
    updated_at text not null
);

create table if not exists kg_nodes (
    node_key text primary key,
    node_type text not null,
    label text not null default '',
    properties_json text not null default '{}',
    extractor_name text not null default 'deterministic_paper_card',
    source_paper_key text references papers(paper_key) on delete cascade,
    created_at text not null,
    updated_at text not null
);

create table if not exists kg_edges (
    id integer primary key autoincrement,
    source_key text not null references kg_nodes(node_key) on delete cascade,
    relation text not null,
    target_key text not null references kg_nodes(node_key) on delete cascade,
    properties_json text not null default '{}',
    extractor_name text not null default 'deterministic_paper_card',
    source_paper_key text references papers(paper_key) on delete cascade,
    created_at text not null,
    updated_at text not null,
    unique(source_key, relation, target_key, extractor_name)
);

create table if not exists kg_provenance (
    id integer primary key autoincrement,
    entity_type text not null,
    entity_key text not null,
    source_table text not null,
    source_key text not null,
    source_field text not null default '',
    confidence real not null default 1.0,
    extractor_name text not null default 'deterministic_paper_card',
    source_paper_key text references papers(paper_key) on delete cascade,
    created_at text not null,
    unique(entity_type, entity_key, source_table, source_key, source_field, extractor_name)
);

create table if not exists fact_extraction_runs (
    id integer primary key autoincrement,
    provider_name text not null,
    extractor_version text not null,
    fixture_path text,
    paper_key text,
    limit_count integer,
    papers_seen integer not null default 0,
    facts_written integer not null default 0,
    provenance_written integer not null default 0,
    started_at text not null,
    finished_at text,
    status text not null,
    error text not null default ''
);

create table if not exists research_facts (
    id integer primary key autoincrement,
    paper_key text not null references papers(paper_key) on delete cascade,
    fact_type text not null,
    name text not null default '',
    statement text not null,
    confidence real not null default 0,
    metadata_json text not null default '{}',
    provider_name text not null,
    extractor_version text not null,
    created_at text not null,
    updated_at text not null,
    unique(paper_key, fact_type, statement, provider_name, extractor_version)
);

create table if not exists research_fact_provenance (
    id integer primary key autoincrement,
    fact_id integer not null references research_facts(id) on delete cascade,
    evidence_quote text not null,
    evidence_artifact_type text not null default '',
    evidence_source_path text not null default '',
    created_at text not null,
    unique(fact_id, evidence_quote, evidence_artifact_type)
);

create table if not exists provider_query_cache (
    id integer primary key autoincrement,
    provider text not null,
    cache_key text not null,
    profile_name text not null,
    query text not null,
    limit_count integer not null,
    response_json text not null,
    created_at text not null,
    expires_at text not null,
    unique(provider, cache_key)
);

create table if not exists provider_usage (
    provider text not null,
    period text not null,
    request_count integer not null default 0,
    updated_at text not null,
    primary key(provider, period)
);

create index if not exists idx_paper_artifacts_paper_key on paper_artifacts(paper_key);
create index if not exists idx_ingest_items_run_id on ingest_items(run_id);
create index if not exists idx_ingest_items_status on ingest_items(status);
create index if not exists idx_sync_events_started_at on sync_events(started_at);

create index if not exists idx_discovery_runs_profile_name on discovery_runs(profile_name);
create index if not exists idx_research_candidates_profile_score on research_candidates(profile_name, score desc);
create index if not exists idx_research_candidates_status on research_candidates(status);

create index if not exists idx_candidate_papers_best_score on candidate_papers(best_score desc);
create index if not exists idx_candidate_papers_status on candidate_papers(status);
create index if not exists idx_candidate_paper_links_candidate_id on candidate_paper_links(research_candidate_id);

create index if not exists idx_extraction_runs_started_at on extraction_runs(started_at);
create index if not exists idx_paper_cards_updated_at on paper_cards(updated_at desc);
create index if not exists idx_kg_nodes_type on kg_nodes(node_type);
create index if not exists idx_kg_nodes_source_paper on kg_nodes(source_paper_key);
create index if not exists idx_kg_edges_relation on kg_edges(relation);
create index if not exists idx_kg_edges_source_paper on kg_edges(source_paper_key);
create index if not exists idx_kg_provenance_source on kg_provenance(source_table, source_key);
create index if not exists idx_kg_provenance_paper on kg_provenance(source_paper_key);

create index if not exists idx_fact_extraction_runs_status on fact_extraction_runs(status);
create index if not exists idx_fact_extraction_runs_started_at on fact_extraction_runs(started_at);
create index if not exists idx_research_facts_paper_key on research_facts(paper_key);
create index if not exists idx_research_facts_type on research_facts(fact_type);
create index if not exists idx_research_fact_provenance_artifact on research_fact_provenance(evidence_artifact_type);

create index if not exists idx_provider_query_cache_provider_key on provider_query_cache(provider, cache_key);
create index if not exists idx_provider_query_cache_expires_at on provider_query_cache(expires_at);
create index if not exists idx_provider_usage_provider_period on provider_usage(provider, period);
