# AG-DEPLOY-REF0 Task Checklist

- [x] Step 1: Verify local main branch matches origin/main and contains PR #6
- [x] Step 2: Run local quality gates (Ruff, Mypy, and Pytest pass cleanly)
- [x] Step 3: Run pre-deploy safety check on production server
- [x] Step 4: Deploy REF-0 to production by checking out main and rebuilding app container
- [x] Step 5: Apply and verify Phase E Alembic migration `c4e2a1f9b8d7` on production DB
- [x] Step 6: Perform final production safety check (verify endpoints, flags, and logs)
- [x] Step 7: Create and commit deployment documentation passes
