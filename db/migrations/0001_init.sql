-- after the tables from 02-causeway.md §13, add:

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