// =====================================================================
// admin.js — EventZone Admin Dashboard Logic
// =====================================================================

const ADMIN_API = "http://127.0.0.1:5000";

(function guardAdmin() {
  const token = localStorage.getItem("jwt");
  if (!token) { window.location.href = "/"; return; }
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    if (payload.role !== "admin") { window.location.href = "/"; return; }
    if (payload.exp && payload.exp < Date.now() / 1000) { localStorage.removeItem("jwt"); window.location.href = "/"; }
  } catch { window.location.href = "/"; }
})();

async function adminFetch(url, options = {}) {
  const token = localStorage.getItem("jwt");
  options.headers = { "Content-Type": "application/json", "Authorization": `Bearer ${token}`, ...(options.headers || {}) };
  const res  = await fetch(ADMIN_API + url, options);
  const json = await res.json();
  if (!json.success) throw new Error(json.message || "Request failed");
  return json.data;
}

function initAdminNav() {
  const token   = localStorage.getItem("jwt");
  const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
  const actions = document.getElementById("adminActions");
  if (actions) {
    actions.innerHTML = `
      <span style="font-weight:600;font-size:13px;color:#94a3b8;">Admin: ${payload.full_name}</span>
      <button class="btn outline" style="padding:7px 14px;font-size:13px;" onclick="adminLogout()">Logout</button>`;
  }
}

function adminLogout() { localStorage.removeItem("jwt"); window.location.href = "/"; }

async function loadStats() {
  try {
    const data = await adminFetch("/api/admin/stats");
    document.getElementById("statBookings").textContent = data.total_bookings;
    document.getElementById("statRevenue").textContent  = `K${data.total_revenue.toFixed(2)}`;
    document.getElementById("statEvents").textContent   = data.active_events;
    document.getElementById("statUsers").textContent    = data.registered_users;
  } catch (err) { console.error("Stats error:", err.message); }
}

let currentPage = 1, currentStatus = "all";

async function updateBookingStatus(id, status, btn) {
  const label = status === 'confirmed' ? 'Confirm' : 'Cancel';
  if (!confirm(`${label} booking #${id}?`)) return;
  btn.disabled = true;
  try {
    await adminFetch(`/api/admin/bookings/${id}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    });
    loadBookings(currentPage, currentStatus);
    loadStats();
  } catch (err) {
    alert(err.message);
    btn.disabled = false;
  }
}

async function loadBookings(page = 1, statusFilter = "all") {
  currentPage = page; currentStatus = statusFilter;
  const tbody = document.getElementById("bookingsBody");
  tbody.innerHTML = `<tr><td colspan="7" class="loading-cell">Loading…</td></tr>`;
  try {
    const data = await adminFetch(`/api/admin/bookings?page=${page}&status=${statusFilter}`);
    if (!data.bookings || data.bookings.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="loading-cell">No bookings found.</td></tr>`;
      document.getElementById("bookingsPagination").innerHTML = "";
      return;
    }
    tbody.innerHTML = data.bookings.map(b => `
      <tr>
        <td>${b.id}</td><td>${b.guest_name || "—"}</td><td>${b.event_title || "—"}</td>
        <td>${b.event_date || "—"}</td><td>${b.ticket_quantity || "—"}</td>
        <td>K${(b.total_price || 0).toFixed(2)}</td>
        <td><span class="badge badge-${b.status}">${b.status}</span></td>
        <td class="action-cell">
          ${b.status === 'pending' ? `
            <button class="btn-action btn-confirm" onclick="updateBookingStatus(${b.id}, 'confirmed', this)">
              <i class="fas fa-check"></i> Confirm
            </button>
            <button class="btn-action btn-cancel" onclick="updateBookingStatus(${b.id}, 'cancelled', this)">
              <i class="fas fa-times"></i> Cancel
            </button>
          ` : b.status === 'confirmed' ? `
            <button class="btn-action btn-cancel" onclick="updateBookingStatus(${b.id}, 'cancelled', this)">
              <i class="fas fa-times"></i> Cancel
            </button>
          ` : '—'}
        </td>
      </tr>`).join("");
    renderPagination(data.page, data.total_pages);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" class="loading-cell" style="color:#f87171;">${err.message}</td></tr>`;
  }
}

function renderPagination(page, totalPages) {
  const el = document.getElementById("bookingsPagination");
  if (!el) return;
  el.innerHTML = `
    <button onclick="loadBookings(${page - 1}, '${currentStatus}')" ${page <= 1 ? "disabled" : ""}>← Prev</button>
    <span class="page-info">Page ${page} of ${totalPages}</span>
    <button onclick="loadBookings(${page + 1}, '${currentStatus}')" ${page >= totalPages ? "disabled" : ""}>Next →</button>`;
}

async function loadUsers() {
  const tbody = document.getElementById("usersBody");
  tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">Loading…</td></tr>`;
  try {
    const users = await adminFetch("/api/admin/users");
    if (!users || users.length === 0) { tbody.innerHTML = `<tr><td colspan="6" class="loading-cell">No users found.</td></tr>`; return; }
    tbody.innerHTML = users.map(u => `
      <tr>
        <td>${u.id}</td><td>${u.full_name}</td><td>${u.email}</td>
        <td><span class="badge badge-${u.role}">${u.role}</span></td>
        <td>${u.created_at ? u.created_at.split("T")[0] : "—"}</td>
        <td>${u.booking_count}</td>
      </tr>`).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="loading-cell" style="color:#f87171;">${err.message}</td></tr>`;
  }
}

async function loadEvents() {
  const tbody = document.getElementById("eventsBody");
  tbody.innerHTML = `<tr><td colspan="9" class="loading-cell">Loading…</td></tr>`;
  try {
    const events = await adminFetch("/api/admin/events");
    if (!events || events.length === 0) { tbody.innerHTML = `<tr><td colspan="9" class="loading-cell">No events found.</td></tr>`; return; }
    _cachedEvents = events;
    tbody.innerHTML = events.map(e => `
      <tr>
        <td>${e.id}</td><td>${e.title}</td>
        <td><span class="badge badge-${e.category}">${e.category}</span></td>
        <td>${e.venue}</td><td>${e.event_date}</td>
        <td>K${e.ticket_price.toFixed(2)}</td>
        <td>${e.tickets_sold} / ${e.total_tickets}</td>
        <td><span class="badge ${e.is_active ? "badge-confirmed" : "badge-cancelled"}">${e.is_active ? "Active" : "Inactive"}</span></td>
        <td>
          <button class="btn-action btn-confirm" onclick="openEditEvent(${e.id})" style="margin-right:6px;">
            <i class="fas fa-pen"></i> Edit
          </button>
          ${e.is_active
            ? `<button class="btn-deactivate" onclick="deactivateEvent(${e.id}, this)" style="margin-left:6px;">Deactivate</button>`
            : `<button class="btn-action btn-confirm" onclick="reactivateEvent(${e.id}, this)" style="margin-left:6px;">
                <i class="fas fa-bolt"></i> Reactivate
              </button>`}
        </td>
      </tr>`).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="9" class="loading-cell" style="color:#f87171;">${err.message}</td></tr>`;
  }
}

function closeEditEventModal() {
  const m = document.getElementById("editEventModal");
  if (m) m.style.display = "none";
}

let _cachedEvents = [];

function openEditEvent(id) {
  const m = document.getElementById("editEventModal");
  if (m) m.style.display = "block";

  const e = (_cachedEvents || []).find(x => x.id === id);
  if (!e) {
    alert("Event data not loaded yet. Please reload.");
    return;
  }

  document.getElementById("editEventId").value = e.id;
  document.getElementById("editEventTitle").value = e.title || "";
  document.getElementById("editEventCategory").value = e.category || "concert";
  document.getElementById("editEventVenue").value = e.venue || "";
  document.getElementById("editEventPrice").value = e.ticket_price ?? "";

  // event_date may be ISO string
  const dateVal = (e.event_date || "").slice(0, 10);
  document.getElementById("editEventDate").value = dateVal;
  document.getElementById("editEventTime").value = e.event_time || "";
  document.getElementById("editEventCapacity").value = e.total_tickets ?? "";
  document.getElementById("editEventImageUrl").value = e.image_url || "";
  document.getElementById("editEventDescription").value = e.description || "";
  document.getElementById("editEventIsActive").value = String(!!e.is_active);
}

async function submitEditEvent(ev) {
  ev.preventDefault();
  const id = parseInt(document.getElementById("editEventId").value, 10);
  const errEl = document.getElementById("editEventError");
  errEl.style.display = "none";

  const btn = ev.submitter || document.querySelector("#editEventForm button[type='submit']");
  if (btn) { btn.disabled = true; btn.textContent = "Saving…"; }

  try {
    const payload = {
      title: document.getElementById("editEventTitle").value.trim(),
      category: document.getElementById("editEventCategory").value,
      venue: document.getElementById("editEventVenue").value.trim(),
      ticket_price: parseFloat(document.getElementById("editEventPrice").value),
      total_tickets: parseInt(document.getElementById("editEventCapacity").value, 10),
      event_date: document.getElementById("editEventDate").value,
      event_time: document.getElementById("editEventTime").value,
      description: document.getElementById("editEventDescription").value.trim(),
      image_url: document.getElementById("editEventImageUrl").value.trim(),
      is_active: document.getElementById("editEventIsActive").value === "true",
    };

    await adminFetch(`/api/events/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });

    closeEditEventModal();
    loadEvents();
    loadStats();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.style.display = "block";
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "Save Changes"; }
  }
}

async function reactivateEvent(id, btn) {
  if (!confirm("Reactivate this event?")) return;
  btn.disabled = true; btn.textContent = "…";
  try {
    await adminFetch(`/api/events/${id}`, {
      method: "PUT",
      body: JSON.stringify({ is_active: true }),
    });
    loadEvents();
    loadStats();
  } catch (err) {
    alert(err.message);
    btn.disabled = false; btn.textContent = "Reactivate";
  }
}


async function deactivateEvent(id, btn) {
  if (!confirm("Deactivate this event?")) return;
  btn.disabled = true; btn.textContent = "…";
  try { await adminFetch(`/api/events/${id}`, { method: "DELETE" }); loadEvents(); loadStats(); }
  catch (err) { alert(err.message); btn.disabled = false; btn.textContent = "Deactivate"; }
}

async function addEvent(e) {
  e.preventDefault();
  const btn   = document.getElementById("addEventBtn");
  const errEl = document.getElementById("addEventError");
  errEl.style.display = "none";
  btn.disabled = true; btn.textContent = "Adding…";
  try {
    await adminFetch("/api/events", {
      method: "POST",
      body: JSON.stringify({
        title:         document.getElementById("eventTitle").value.trim(),
        category:      document.getElementById("eventCategory").value,
        venue:         document.getElementById("eventVenue").value.trim(),
        ticket_price:  parseFloat(document.getElementById("eventPrice").value),
        total_tickets: parseInt(document.getElementById("eventCapacity").value, 10),
        event_date:    document.getElementById("eventDate").value,
        event_time:    document.getElementById("eventTime").value,
        description:   document.getElementById("eventDescription").value.trim(),
        image_url:     document.getElementById("eventImageUrl").value.trim(),
      }),
    });
    document.getElementById("addEventForm").reset();
    loadEvents(); loadStats();
  } catch (err) { errEl.textContent = err.message; errEl.style.display = "block"; }
  finally { btn.disabled = false; btn.textContent = "Add Event"; }
}

document.addEventListener("DOMContentLoaded", () => {
  initAdminNav(); loadStats(); loadBookings(); loadUsers(); loadEvents();
});
