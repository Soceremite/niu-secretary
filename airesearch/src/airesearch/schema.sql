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

create table if not exists paper_code_links (
    id integer primary key autoincrement,
    paper_key text not null references papers(paper_key) on delete cascade,
    url text not null,
    host text not null default '',
    owner text not null default '',
    repo text not null default '',
    source_type text not null,
    source_path text not null default '',
    context text not null default '',
    created_at text not null,
    updated_at text not null,
    unique(paper_key, url, source_type, source_path)
);

create table if not exists paper_chunks (
    id integer primary key autoincrement,
    paper_key text not null references papers(paper_key) on delete cascade,
    artifact_type text not null,
    source_path text not null,
    chunk_index integer not null,
    heading text not null default '',
    text text not null,
    char_start integer not null default 0,
    char_end integer not null default 0,
    sha256 text not null,
    created_at text not null,
    updated_at text not null,
    unique(paper_key, artifact_type, source_path, chunk_index)
);

create table if not exists paper_equations (
    id integer primary key autoincrement,
    paper_key text not null references papers(paper_key) on delete cascade,
    source_path text not null,
    equation_index integer not null,
    label text not null default '',
    latex text not null,
    context text not null default '',
    created_at text not null,
    updated_at text not null,
    unique(paper_key, source_path, equation_index)
);

create table if not exists paper_citations (
    id integer primary key autoincrement,
    paper_key text not null references papers(paper_key) on delete cascade,
    source_path text not null,
    citation_index integer not null,
    citation_key text not null,
    raw_text text not null,
    context text not null default '',
    created_at text not null,
    updated_at text not null,
    unique(paper_key, source_path, citation_index, citation_key)
);

create table if not exists paper_layout_runs (
    id integer primary key autoincrement,
    paper_key text not null references papers(paper_key) on delete cascade,
    provider text not null default 'airesearch_layout',
    provider_version text not null default '',
    backend text not null default '',
    method text not null default '',
    status text not null,
    input_pdf_path text not null default '',
    output_dir text not null default '',
    artifact_json text not null default '{}',
    stats_json text not null default '{}',
    error text not null default '',
    started_at text not null,
    finished_at text,
    unique(paper_key, provider, output_dir)
);

create table if not exists paper_layout_blocks (
    id integer primary key autoincrement,
    paper_key text not null references papers(paper_key) on delete cascade,
    run_id integer not null references paper_layout_runs(id) on delete cascade,
    page_index integer not null,
    block_index integer not null,
    block_type text not null,
    bbox_json text not null default '[]',
    text text not null default '',
    asset_path text not null default '',
    metadata_json text not null default '{}',
    created_at text not null,
    unique(run_id, page_index, block_index)
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

create table if not exists research_fact_translations (
    id integer primary key autoincrement,
    fact_id integer not null references research_facts(id) on delete cascade,
    lang text not null,
    statement text not null default '',
    evidence_quote text not null default '',
    model text not null default '',
    created_at text not null,
    updated_at text not null,
    unique(fact_id, lang)
);

create table if not exists fact_extraction_cache (
    id integer primary key autoincrement,
    paper_key text not null references papers(paper_key) on delete cascade,
    provider_name text not null,
    extractor_version text not null,
    model text not null,
    evidence_hash text not null,
    prompt_json text not null,
    response_json text not null default '',
    status text not null,
    error text not null default '',
    created_at text not null,
    updated_at text not null,
    unique(paper_key, provider_name, extractor_version, model, evidence_hash)
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

create table if not exists admin_paper_overrides (
    paper_key text primary key,
    hidden integer not null default 0,
    paper_url text not null default '',
    arxiv_id text not null default '',
    github_url text not null default '',
    updated_at text not null
);

create table if not exists admin_jobs (
    id integer primary key autoincrement,
    job_type text not null,
    status text not null,
    message text not null default '',
    log text not null default '',
    params_json text not null default '{}',
    current_step text not null default '',
    result_json text not null default '{}',
    priority integer not null default 0,
    created_at text,
    started_at text not null,
    finished_at text
);

create table if not exists admin_paper_drafts (
    paper_key text primary key,
    payload_json text not null default '{}',
    updated_at text not null
);

create table if not exists paper_archives (
    paper_key text primary key references papers(paper_key) on delete cascade,
    provider text not null default 'rclone',
    remote_name text not null,
    remote_path text not null,
    archive_sha256 text not null,
    archive_size_bytes integer not null,
    source_manifest_json text not null default '{}',
    status text not null check (
        status in ('planned', 'uploaded', 'verified', 'evicted', 'restoring', 'available', 'failed')
    ),
    verified_at text,
    evicted_at text,
    restored_at text,
    last_error text,
    pinned integer not null default 0 check (pinned in (0, 1)),
    updated_at text not null
);

create table if not exists paper_blog_posts (
    paper_key text primary key references papers(paper_key) on delete cascade,
    current_version_id integer,
    title text not null default '',
    slug text not null default '',
    status text not null default 'published' check (status in ('published', 'hidden', 'failed')),
    target_audience text not null default 'ai_engineer',
    language text not null default 'zh',
    word_count integer not null default 0,
    markdown text not null default '',
    html text not null default '',
    outline_json text not null default '{}',
    image_refs_json text not null default '[]',
    model text not null default '',
    prompt_version text not null default '',
    source_hash text not null default '',
    created_at text not null,
    updated_at text not null
);

create table if not exists paper_blog_versions (
    id integer primary key autoincrement,
    paper_key text not null references papers(paper_key) on delete cascade,
    version_number integer not null,
    status text not null default 'published' check (status in ('published', 'superseded', 'hidden', 'failed')),
    title text not null default '',
    word_count integer not null default 0,
    markdown text not null default '',
    html text not null default '',
    outline_json text not null default '{}',
    image_refs_json text not null default '[]',
    generation_meta_json text not null default '{}',
    model text not null default '',
    prompt_version text not null default '',
    source_hash text not null default '',
    created_at text not null,
    unique(paper_key, version_number)
);

create table if not exists paper_blog_generation_cache (
    id integer primary key autoincrement,
    paper_key text not null references papers(paper_key) on delete cascade,
    section_key text not null,
    source_hash text not null,
    prompt_version text not null,
    model text not null,
    request_hash text not null,
    response_json text not null default '{}',
    markdown text not null default '',
    token_estimate integer not null default 0,
    created_at text not null,
    updated_at text not null,
    unique(paper_key, section_key, source_hash, prompt_version, model, request_hash)
);

create table if not exists paper_blog_formula_repairs (
    id integer primary key autoincrement,
    paper_key text not null references papers(paper_key) on delete cascade,
    source_version_id integer not null references paper_blog_versions(id) on delete cascade,
    applied_version_id integer references paper_blog_versions(id) on delete set null,
    formula_locator_json text not null default '{}',
    original_latex text not null,
    repaired_latex text not null default '',
    pdf_page integer,
    bbox_json text not null default '[]',
    crop_path text not null default '',
    context text not null default '',
    model text not null default '',
    confidence real not null default 0,
    initial_validation_status text not null default '',
    initial_validation_error text not null default '',
    validation_status text not null default '',
    validation_error text not null default '',
    repair_status text not null default 'pending',
    input_hash text not null,
    created_at text not null,
    updated_at text not null,
    unique(paper_key, source_version_id, input_hash)
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
create index if not exists idx_kg_edges_target_key on kg_edges(target_key);
create index if not exists idx_kg_provenance_source on kg_provenance(source_table, source_key);
create index if not exists idx_kg_provenance_paper on kg_provenance(source_paper_key);

create index if not exists idx_paper_code_links_paper_key on paper_code_links(paper_key);
create index if not exists idx_paper_code_links_host on paper_code_links(host);
create index if not exists idx_paper_code_links_repo on paper_code_links(owner, repo);
create index if not exists idx_paper_chunks_paper_key on paper_chunks(paper_key);
create index if not exists idx_paper_chunks_artifact on paper_chunks(artifact_type);
create index if not exists idx_paper_equations_paper_key on paper_equations(paper_key);
create index if not exists idx_paper_citations_paper_key on paper_citations(paper_key);
create index if not exists idx_paper_citations_key on paper_citations(citation_key);
create index if not exists idx_paper_layout_runs_paper on paper_layout_runs(paper_key, id desc);
create index if not exists idx_paper_layout_runs_status on paper_layout_runs(status);
create index if not exists idx_paper_layout_blocks_paper_type on paper_layout_blocks(paper_key, block_type);

create index if not exists idx_fact_extraction_runs_status on fact_extraction_runs(status);
create index if not exists idx_fact_extraction_runs_started_at on fact_extraction_runs(started_at);
create index if not exists idx_research_facts_paper_key on research_facts(paper_key);
create index if not exists idx_paper_archives_status on paper_archives(status, pinned);
create index if not exists idx_research_facts_type on research_facts(fact_type);
create index if not exists idx_research_fact_provenance_artifact on research_fact_provenance(evidence_artifact_type);
create index if not exists idx_research_fact_translations_lang on research_fact_translations(lang);

create index if not exists idx_fact_extraction_cache_lookup
on fact_extraction_cache(provider_name, model, evidence_hash, status);

create index if not exists idx_provider_query_cache_provider_key on provider_query_cache(provider, cache_key);
create index if not exists idx_provider_query_cache_expires_at on provider_query_cache(expires_at);
create index if not exists idx_provider_usage_provider_period on provider_usage(provider, period);
create index if not exists idx_admin_paper_overrides_hidden on admin_paper_overrides(hidden);
create index if not exists idx_admin_jobs_started_at on admin_jobs(started_at desc);
create index if not exists idx_admin_paper_drafts_updated_at on admin_paper_drafts(updated_at desc);
create index if not exists idx_paper_blog_posts_status on paper_blog_posts(status);
create index if not exists idx_paper_blog_versions_paper_key on paper_blog_versions(paper_key, version_number desc);
create index if not exists idx_blog_formula_repairs_paper
on paper_blog_formula_repairs(paper_key, source_version_id, repair_status);

create index if not exists idx_paper_blog_cache_lookup
on paper_blog_generation_cache(paper_key, section_key, source_hash, prompt_version, model, request_hash);
