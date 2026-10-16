-- Optional local search index (rebuilt from papers/; never committed as a database).
CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE papers(pm_id TEXT PRIMARY KEY, slug TEXT NOT NULL, title TEXT NOT NULL, paper TEXT NOT NULL,
  subject_id INTEGER NOT NULL, status TEXT NOT NULL, paper_sha256 TEXT NOT NULL);
CREATE VIRTUAL TABLE pos USING fts5(pm_id UNINDEXED, kind UNINDEXED, anchor UNINDEXED, text,
  tokenize='unicode61 remove_diacritics 2');
CREATE VIRTUAL TABLE neg USING fts5(pm_id UNINDEXED, query, reason, tokenize='unicode61 remove_diacritics 2');
CREATE TABLE vec(pm_id TEXT PRIMARY KEY, dim INTEGER NOT NULL, v BLOB NOT NULL);
