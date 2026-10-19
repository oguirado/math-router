# catalogue

Navigation records for the 719 papers: `subjects.json` (subject index), `subjects/<id>/` (page shards), `details/` (nodes too large for a page), `families/`, `routes.tsv` (paper id to file path and page).

Typed edges: no separate `graph.jsonl` is shipped (the release manifest records `graph_edges` as 0). The per-node relations the router uses are compiled into `out/index/edges.json` by `tools/build_index_v2.py`.

Mount path: `out/protocol.json` describes the router mount as `catalogue/router`, the reference layout of the router protocol. In this repository the same index and parameters are shipped as `out/index` and `out/params.json`; pass those to `tools/route_v2.py` directly.
