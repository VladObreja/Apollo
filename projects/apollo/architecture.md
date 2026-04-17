# Apollo Architecture

## Text-form component diagram

```text
                                  [ ADMINISTRATOR / OPERATOR ]
                                              |
                                              v
                                  [ APOLLO ADMIN INTERFACE ]
                               (single governing interaction point)
                                              |
                                              v
                                [ OPENCLAW ORCHESTRATION CORE ]
                         task typing | routing | policy | execution control
                           project scope | tool use | agent coordination
                                              |
                  ----------------------------------------------------------------
                  |                         |                         |            |
                  v                         v                         v            v
        [ INGESTION CONTROL ]     [ QUERY / ANALYSIS CONTROL ]   [ DEV CONTROL ] [ MODULE CONTROL ]
      intake routing, queues,      retrieval orchestration,       optional        project modules:
      processing state, retries    synthesis, evidence bundling   later           Aurelius, RV, etc.
                  |                         |
                  v                         v
      ------------------------      ------------------------
      |          |         |        |          |          |
      v          v         v        v          v          v
 [TEXT PATH] [OCR PATH] [WEB/MEDIA] [LightRAG] [MODEL RT] [MEMORY]
                        EXTRACTION                         LAYERS
      |          |         |        |          |          |
      ------------------------      ------------------------
                  |                         |
                  v                         v
                [ NORMALIZATION / CANONICAL ARTIFACT LAYER ]
         source record | raw artifact | extracted artifact | normalized artifact
                  provenance | project binding | metadata | structure | confidence
                                              |
                                              v
                              [ STORAGE AND KNOWLEDGE SUBSTRATE ]
                 -----------------------------------------------------------
                 |                         |                              |
                 v                         v                              v
          [ RAW ARTIFACT STORE ]   [ METADATA / REGISTRY ]       [ INDEX / RETRIEVAL STORE ]
         originals, captures,      project registry, source      LightRAG structures,
         snapshots, media          registry, processing status   retrieval units, links
                                              |
                                              v
                                   [ RESPONSE / ACTION OUTPUTS ]
                         grounded answers | summaries | reports | task proposals
```

## Responsibility boundaries
### OpenClaw
Owns orchestration, task routing, tool use, project scope, and session execution.

### Open WebUI
Owns the human-facing interaction surface.

### LightRAG
Owns retrieval structures and evidence recall over the curated corpus.

### Vault/Clean
Acts as the current clean corpus and evidence-preparation layer.

### projects/apollo
Acts as the canonical control layer for mission, progress, and handoff.

## Current architectural stance
For now Apollo should remain thin:
- one admin interface
- one curated corpus path
- one retrieval layer
- one query loop

Complex agent orchestration is deferred until this foundation is proven.