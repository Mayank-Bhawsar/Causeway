CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE node_version (
  node_id   text      NOT NULL,
  kind      text      NOT NULL CHECK (kind IN
              ('Service','Pod','Deployment','K8sService','Database','Topic','Node')),
  attrs     jsonb     NOT NULL DEFAULT '{}',
  spec_hash bytea     NOT NULL,
  validity  tstzrange NOT NULL,
  PRIMARY KEY (node_id, validity),
  EXCLUDE USING gist (node_id WITH =, validity WITH &&)
);

CREATE TABLE edge_observation (
  src        text      NOT NULL,
  dst        text      NOT NULL,
  rel        text      NOT NULL,
  bucket     tstzrange NOT NULL,
  calls      bigint    NOT NULL DEFAULT 0,
  errors     bigint    NOT NULL DEFAULT 0,
  p50_ms     real,
  p95_ms     real,
  call_share real      NOT NULL,
  lat_share  real      NOT NULL,
  err_share  real      NOT NULL,
  PRIMARY KEY (src, dst, rel, bucket)
);
CREATE INDEX ON edge_observation USING gist (bucket);
CREATE INDEX ON edge_observation (dst, bucket);

CREATE TABLE topology_snapshot (
  snapshot_id text PRIMARY KEY,
  taken_at    timestamptz NOT NULL,
  node_count  int NOT NULL,
  edge_count  int NOT NULL,
  body        bytea NOT NULL
);

CREATE TABLE signal (
  signal_id   text PRIMARY KEY,
  kind        text NOT NULL,
  node_id     text NOT NULL,
  severity    real NOT NULL CHECK (severity BETWEEN 0 AND 1),
  onset_at    timestamptz NOT NULL,
  observed_at timestamptz NOT NULL,
  fingerprint text,
  payload     jsonb NOT NULL,
  embedding   vector(384)
);
CREATE INDEX ON signal (onset_at);
CREATE INDEX ON signal USING hnsw (embedding vector_cosine_ops);

CREATE TABLE incident (
  incident_id   text PRIMARY KEY,
  parent_id     text REFERENCES incident(incident_id),
  merged_from   text[],
  win           tstzrange NOT NULL,
  snapshot_id   text NOT NULL REFERENCES topology_snapshot(snapshot_id),
  signal_count  int NOT NULL,
  status        text NOT NULL,
  fiedler_value real,
  fiedler_null  real,
  created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE cause_candidate (
  incident_id text REFERENCES incident(incident_id),
  node_id     text NOT NULL,
  rank        int  NOT NULL,
  score       real NOT NULL,
  confidence  real NOT NULL,
  conformal_k int  NOT NULL,
  features    jsonb NOT NULL,
  PRIMARY KEY (incident_id, node_id)
);

CREATE TABLE audit_log (
  audit_id    bigserial PRIMARY KEY,
  at          timestamptz NOT NULL DEFAULT now(),
  actor       text NOT NULL,
  incident_id text,
  action      jsonb NOT NULL,
  prev_hash   bytea,
  row_hash    bytea NOT NULL
);

CREATE TABLE ground_truth (
  scenario  text PRIMARY KEY,
  true_root text NOT NULL,
  onset_at  timestamptz NOT NULL,
  blast     text[] NOT NULL
);

CREATE TABLE feedback (
  incident_id  text REFERENCES incident(incident_id),
  actual_root  text NOT NULL,
  correct_rank int,
  submitted_by text NOT NULL,
  submitted_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (incident_id, submitted_by)
);

CREATE TABLE incident_signal (
  incident_id text NOT NULL REFERENCES incident(incident_id),
  signal_id   text NOT NULL REFERENCES signal(signal_id),
  PRIMARY KEY (incident_id, signal_id)
);

CREATE TABLE evidence_pack (
  incident_id text PRIMARY KEY REFERENCES incident(incident_id),
  pack        jsonb NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE narrative (
  incident_id text PRIMARY KEY REFERENCES incident(incident_id),
  body        jsonb,
  provider    text,
  created_at  timestamptz NOT NULL DEFAULT now()
);