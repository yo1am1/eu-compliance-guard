// Generated from fixtures/scorecard-synthetic.json by tests/test_plugin.py (EUCG_UPDATE_FIXTURES=1); do not edit.
// The band may import code files only.
export const SYNTHETIC_CARD = {
  "schema_version": 1,
  "scorer_version": 1,
  "project_id": "project-example",
  "run_id": "run-synthetic",
  "parent_run_id": null,
  "synthetic": true,
  "run_state": "partial",
  "ended_at": "2026-11-04T00:00:00Z",
  "assessment_date": "2026-10-18",
  "assessed_days_before_run": 17,
  "offline": true,
  "status": "in_review",
  "attention": [],
  "dimensions": [
    {
      "key": "alignment",
      "points": 5,
      "done": 1,
      "total": 2,
      "raise_points": 5,
      "raise_by": 1,
      "counts": [
        {
          "key": "supported",
          "count": 1
        },
        {
          "key": "unresolved",
          "count": 1
        }
      ],
      "reasons": [
        {
          "key": "no_mapping",
          "count": 1
        }
      ],
      "open_items": [
        {
          "id": "requirement-unmapped",
          "method": null,
          "reasons": [
            "no_mapping"
          ]
        }
      ],
      "open_total": 1,
      "ceiling": null
    },
    {
      "key": "law_text",
      "points": 10,
      "done": 2,
      "total": 2,
      "raise_points": null,
      "raise_by": null,
      "counts": [],
      "reasons": [],
      "open_items": [],
      "open_total": 0,
      "ceiling": null
    },
    {
      "key": "facts",
      "points": 3,
      "done": 1,
      "total": 3,
      "raise_points": 3,
      "raise_by": 1,
      "counts": [
        {
          "key": "declared",
          "count": 1
        },
        {
          "key": "assumed",
          "count": 1
        },
        {
          "key": "unknown",
          "count": 1
        }
      ],
      "reasons": [
        {
          "key": "assumed",
          "count": 1
        },
        {
          "key": "unknown",
          "count": 1
        },
        {
          "key": "ask_owner",
          "count": 2
        }
      ],
      "open_items": [
        {
          "id": "fact-assumed",
          "method": null,
          "reasons": [
            "assumed",
            "ask_owner"
          ]
        },
        {
          "id": "fact-unknown",
          "method": null,
          "reasons": [
            "unknown",
            "ask_owner"
          ]
        }
      ],
      "open_total": 2,
      "ceiling": null
    },
    {
      "key": "decisions",
      "points": 5,
      "done": 1,
      "total": 2,
      "raise_points": 5,
      "raise_by": 1,
      "counts": [
        {
          "key": "applicable",
          "count": 1
        },
        {
          "key": "missing",
          "count": 1
        }
      ],
      "reasons": [
        {
          "key": "missing",
          "count": 1
        }
      ],
      "open_items": [
        {
          "id": "obligation-unmapped",
          "method": null,
          "reasons": [
            "missing"
          ]
        }
      ],
      "open_total": 1,
      "ceiling": null
    },
    {
      "key": "mapping",
      "points": 5,
      "done": 1,
      "total": 2,
      "raise_points": 5,
      "raise_by": 1,
      "counts": [
        {
          "key": "unclaimed_obligations",
          "count": 1
        }
      ],
      "reasons": [
        {
          "key": "no_mapping",
          "count": 1
        }
      ],
      "open_items": [
        {
          "id": "requirement-unmapped",
          "method": null,
          "reasons": [
            "no_mapping"
          ]
        }
      ],
      "open_total": 1,
      "ceiling": null
    },
    {
      "key": "reviews",
      "points": 5,
      "done": 1,
      "total": 2,
      "raise_points": 5,
      "raise_by": 1,
      "counts": [
        {
          "key": "review_complete",
          "count": 1
        },
        {
          "key": "not_started",
          "count": 1
        },
        {
          "key": "evidence_ready",
          "count": 1
        },
        {
          "key": "evidence_declared",
          "count": 1
        }
      ],
      "reasons": [
        {
          "key": "not_started",
          "count": 1
        }
      ],
      "open_items": [
        {
          "id": "obligation-unmapped",
          "method": "organizational",
          "reasons": [
            "not_started"
          ]
        }
      ],
      "open_total": 1,
      "ceiling": null
    }
  ],
  "screening": {
    "screened": 0,
    "total": 11,
    "applicable": 0,
    "not_applicable": 0,
    "withdrawn": 0
  },
  "hygiene": [
    {
      "key": "requirements_located",
      "done": 0,
      "total": 2
    },
    {
      "key": "evidence_referenced",
      "done": 1,
      "total": 2
    },
    {
      "key": "origins_unchanged",
      "done": 0,
      "total": 0
    }
  ],
  "next_step": {
    "kind": "mapping",
    "subject": "requirement-unmapped",
    "unblocks": 1,
    "focus": "mapping"
  },
  "notes_outside": 1,
  "trend": null,
  "notice": "Points count recorded review steps in this run. They are not a compliance score or verdict."
} as const
