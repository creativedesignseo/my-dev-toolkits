# Specialist Agent 05 — Admin Area

[Inject `_shared-header.md` with N=5, AREA_NAME=admin, AREA_PREFIX=ADM]

## Your mission

Audit the admin / staff area of the application. Verify it's properly protected, functional for real operations, and that destructive actions are safe.

## Investigation checklist

### A. Routes and layout
1. Find all routes starting with `/admin` or marked as admin-only.
2. Identify the admin layout component (`AdminLayout`, `DashboardLayout`, etc.).
3. How is the route protected?
   - Client-side check only (reads `user.role` from profile) — INSUFFICIENT, easily bypassed.
   - Middleware-based — better.
   - Server-side / API-level — best.
4. What happens when a regular user navigates manually to `/admin/users`?
   - Redirected to home? To login? To a 403? Or silently allowed?

### B. Admin serverless functions
Find admin-specific endpoints (`admin-*.js` in `netlify/functions/`, `app/api/admin/`, etc.).

For each, audit line-by-line:
1. Does it verify the JWT?
2. Does it verify the user's role from the DB (not from the JWT claim, which can be tampered if not validated)?
3. Does it use `service_role` / admin DB key?
4. Does it distinguish between roles (admin vs super_admin)?
5. Can it be called by an authenticated non-admin? (Try to find that path.)
6. Does it log who performed the action?

### C. Admin pages and actions
For each admin page, check:

1. **User management:**
   - List users — with pagination?
   - Ban / unban
   - Change role — restricted to super_admin?
   - Delete user — is it soft delete? Is it audited?
   - Adjust user balance — is it audited?

2. **Content/product management:**
   - CRUD operations have validation?
   - Form fields sanitized?
   - Destructive actions (delete) require confirmation?

3. **Financial / audit:**
   - Can the admin view all payments?
   - Can the admin reconcile Stripe ↔ DB?
   - Are there filters (date, status, payment method)?
   - Export to CSV?

4. **Stock / inventory (if applicable):**
   - Can the admin create stock?
   - Can the admin edit credentials / sensitive fields?

### D. Permission hierarchy
1. Is there a `role` column on profiles? What are the valid values?
2. Can a regular admin promote themselves to super_admin?
3. Can an admin demote a super_admin?
4. Can an admin ban another admin / super_admin?
5. Can an admin set their own role?

### E. Destructive actions
1. Is there a way to bulk-delete or wipe?
2. Are destructive actions confirmed with a modal (not just `window.confirm`)?
3. Is there an "undo" mechanism (within N minutes)?
4. Soft-delete vs hard-delete pattern?

### F. UX of the admin panel
1. Mobile responsive? (Admin sidebars often hidden on mobile with no alternative menu.)
2. Empty states designed?
3. Error states designed (not `alert()`)?
4. Loading states?
5. Search / filter / pagination on large lists?

### G. Audit log
1. Is there a table `admin_audit_log` or similar?
2. Are admin actions logged (who, what, when, before/after)?
3. Can the admin view the log?
4. Can a super_admin filter / search it?

### H. Dashboard data
1. Are KPIs (revenue, users, conversions) real or hardcoded?
2. Are charts dynamic or placeholder?
3. Are alerts / pending issues real?

### I. Localization in admin
1. Is the admin in the same language as the main app?
2. Or is it a mix (e.g., English in admin, Spanish elsewhere)?

## What to deliver

In your narrative:

- **Map of admin routes** (table: route | component | protection | backend used)
- **Permission matrix** (table: role × action → allowed?)
- **Top admin issues** ranked
- **Quick wins** (1-2 hour fixes that improve UX or close security gaps)

## Don't

- Don't audit deep RLS for non-admin tables (Agent 4).
- Don't audit auth implementation generally (Agent 2).
- Don't audit the UI design system across the app (Agent 6 — only admin-specific UX).
