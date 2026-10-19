# catalogue

Navigation records for the 719 papers: `subjects.json` (subject index), `subjects/<id>/` (page shards), `details/` (nodes too large for a page), `families/` (family records, ids written `PM-<number>`), `routes.tsv` (paper id to file path and page; tab-separated with a header row, columns `id`, `subject_id`, `paper`, `page`: the paper id such as `PM-005.1`, the numeric subject shard under `subjects/`, the repository-relative path of the paper file, and the page shard (a `pNNN.jsonl` file in the `pages` folder of that subject) that holds its record; `AGENTS.md` rung 2 reads column 3), `measurements.json` (measured sizes of the shards).

Typed relations: no separate `graph.jsonl` is shipped (the release manifest records `graph_edges` as 0 because none of the relations is verified). The 1,308 relations written in section 9 of the papers are compiled into `out/index/edges.json` by `tools/build_index_v2.py`; all of them have verification status `PENDING`, and the tuned edge weight in `out/params.json` is 0, so they do not change the ranking.

Mount: `out/protocol.json` describes the router mount of this repository, the index `out/index` and the parameters `out/params.json`. Pass those to `tools/route_v2.py` directly.
