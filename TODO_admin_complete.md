# TODO: Admin dashboard completion (Phase 1 & Phase 2)

## Phase 1 — UI completeness (no backend breakage)
- [ ] Redesign `admin.html` sections to support: Events (add + edit), Bookings (search/filter), Users (view + moderation UI placeholders)
- [ ] Implement Event Edit modal/form in UI using existing backend endpoint: `PUT /api/events/<id>`
- [ ] Add event activate/reactivate controls (if backend supports, else placeholders)
- [ ] Improve Events table to show image + active/inactive and support edit
- [ ] Add “Edit” action to each event row; prefill form from event payload
- [ ] Update `admin.js` to include `loadEventById` (if needed) + `updateEvent` call
- [ ] Update `admin.css` for modal/form styles used by edit

## Phase 2 — Backend missing features (full completion)
> Requires new models/endpoints (not present yet):
- [ ] Contact inbox (model + endpoints)
- [ ] Audit log (model + endpoints)
- [ ] User moderation endpoints (block/suspend/role change)
- [ ] Payment admin endpoints (list + refund/verify)
- [ ] Ticket check-in/scan endpoints (model + endpoints)
- [ ] Reports/export endpoints

## Validation
- [ ] Run backend
- [ ] Open `/admin.html` in browser and verify each section loads
- [ ] Verify Event Add/Deactivate/Edit works end-to-end
- [ ] Verify Booking status updates still update event inventory correctly

