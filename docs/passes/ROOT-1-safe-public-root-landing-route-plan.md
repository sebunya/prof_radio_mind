# ROOT-1 — Add Safe Public Root Landing Route

## Objective
Add a safe, minimal GET `/` route returning a simple JSON landing response to replace the default `{"detail":"Not Found"}` when visiting the live root URL `https://tenxradar.com/`.

## Changes Made
### Application Source
* **app/main.py**: Added `@app.get("/", include_in_schema=False)` returning:
  ```json
  {
    "status": "ok",
    "service": "TenX Radar",
    "description": "Radio Music Intelligence & Automation System",
    "version": "0.1.0",
    "endpoints": {
      "health": "/health",
      "admin": "/admin",
      "api_docs": "/docs"
    },
    "components": {
      "scheduler": scheduler_status,
      "collectors": "disabled"
    }
  }
  ```

### Unit Tests
* **tests/unit/test_api.py**: Added `test_root_landing_200` to verify that GET `/` returns HTTP 200 with the correct JSON fields.

## Verification
* Unit tests (308 passed).
* Ruff and mypy linting / type checking are clean.
