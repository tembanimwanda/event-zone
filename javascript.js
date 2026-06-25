// =====================================================================
// javascript.js — EventZone: events, ticketing, payment flow
// =====================================================================

const API = "http://127.0.0.1:5000";

let currentEventId        = null;
let currentEventTitle     = null;
let currentTicketPrice    = null;
let currentTicketsAvail   = null;
let currentTicketQuantity = 1;
let currentBookingId      = null;
let currentTransactionId  = null;

async function apiFetch(url, options = {}) {
  const token = localStorage.getItem("jwt");
  options.headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) options.headers["Authorization"] = `Bearer ${token}`;
  try {
    const res  = await fetch(API + url, options);
    const json = await res.json();
    if (res.status === 202) return { _status202: true, data: json.data };
    if (!json.success) throw new Error(json.message || "Request failed");
    return json.data;
  } catch (err) {
    if (err instanceof SyntaxError) throw new Error("Connection error. Please try again.");
    throw err;
  }
}

let activeCategory = "all";

function setCategory(category, btn) {
  activeCategory = category;
  document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  initEvents(category);
}

function filterEvents() {
  const category = document.getElementById("heroCategory")?.value || "all";
  const date     = document.getElementById("heroDate")?.value || null;
  activeCategory = category;
  initEvents(category, date);
  scrollToEvents();
}

function scrollToEvents() {
  document.getElementById("events")?.scrollIntoView({ behavior: "smooth" });
}

function categoryLabel(cat) {
  const map = { concert: "🎵 Concert", show: "🎪 Show", sport: "⚽ Sport" };
  return map[cat] || cat;
}

function eventCard(event) {
  const img = event.image_url || "https://images.unsplash.com/photo-1470229722913-7c0e2dbbafd3?w=800";
  const available = event.tickets_available;
  const soldOut   = available <= 0;
  const lowStock  = available > 0 && available <= 20;

  const ticketsLabel = soldOut
    ? '<span class="tickets-left" style="color:#ef4444;">Sold Out</span>'
    : lowStock
      ? `<span class="tickets-left low">⚠️ Only ${available} left!</span>`
      : `<span class="tickets-left">${available} tickets available</span>`;

  const btn = soldOut
    ? `<button class="btn outline full" disabled style="opacity:0.5;cursor:not-allowed;">Sold Out</button>`
    : `<button class="btn primary full" onclick="openTicketing(${event.id}, '${event.title.replace(/'/g, "\\'")}', ${event.ticket_price}, ${available})">🎟️ Get Tickets</button>`;

  return `
    <div class="card">
      <img src="${img}" alt="${event.title}" loading="lazy" />
      <div class="card-body">
        <span class="badge-category badge-${event.category}">${categoryLabel(event.category)}</span>
        <h3>${event.title}</h3>
        <div class="venue">📍 ${event.venue}</div>
        <div class="event-meta">
          <span>📅 ${event.event_date}</span>
          <span>🕐 ${event.event_time}</span>
        </div>
        ${ticketsLabel}
        <span class="price">K${event.ticket_price.toFixed(2)} / ticket</span>
        ${btn}
      </div>
    </div>`;
}

async function initEvents(category = "all", date = null) {
  const grid = document.getElementById("eventsGrid");
  if (!grid) return;
  grid.innerHTML = '<p style="text-align:center;padding:40px;color:#666;grid-column:1/-1;">Loading events…</p>';
  let url = "/api/events?upcoming=true";
  if (category && category !== "all") url += `&category=${encodeURIComponent(category)}`;
  try {
    let events = await apiFetch(url);
    if (!events || events.length === 0) {
      grid.innerHTML = '<p style="text-align:center;padding:40px;color:#666;grid-column:1/-1;">No events found.</p>';
      return;
    }
    if (date) {
      events = events.filter(e => e.event_date === date);
      if (events.length === 0) {
        grid.innerHTML = '<p style="text-align:center;padding:40px;color:#666;grid-column:1/-1;">No events on that date.</p>';
        return;
      }
    }
    grid.innerHTML = events.map(eventCard).join("");
  } catch (err) {
    grid.innerHTML = `<p style="text-align:center;padding:40px;color:#ef4444;grid-column:1/-1;">${err.message}</p>`;
  }
}

function openTicketing(eventId, title, price, ticketsAvailable) {
  const token = localStorage.getItem("jwt");
  if (!token) { if (typeof openLogin === "function") openLogin(); return; }
  currentEventId = eventId; currentEventTitle = title;
  currentTicketPrice = price; currentTicketsAvail = ticketsAvailable;
  currentTicketQuantity = 1;
  const titleEl = document.getElementById("bookingEventTitle");
  const infoEl  = document.getElementById("bookingEventInfo");
  if (titleEl) titleEl.textContent = title;
  if (infoEl)  infoEl.textContent  = `K${price.toFixed(2)} per ticket · ${ticketsAvailable} available`;
  updateBookingTotal();
  setBookingError("");
  const modal = document.getElementById("bookingModal");
  if (modal) modal.style.display = "flex";
}

function closeBookingModal() {
  const modal = document.getElementById("bookingModal");
  if (modal) modal.style.display = "none";
  setBookingError("");
}

function setBookingError(msg) {
  const el = document.getElementById("bookingError");
  if (!el) return;
  el.textContent = msg;
  el.style.display = msg ? "block" : "none";
}

function changeQuantity(delta) {
  const max = Math.min(currentTicketsAvail || 10, 10);
  currentTicketQuantity = Math.max(1, Math.min(max, currentTicketQuantity + delta));
  const qEl = document.getElementById("ticketQuantity");
  if (qEl) qEl.textContent = currentTicketQuantity;
  updateBookingTotal();
}

function updateBookingTotal() {
  const totalEl = document.getElementById("bookingTotalDisplay");
  if (!totalEl || !currentTicketPrice) return;
  const total = (currentTicketPrice * currentTicketQuantity).toFixed(2);
  totalEl.textContent = `Total: K${total} (${currentTicketQuantity} ticket${currentTicketQuantity > 1 ? "s" : ""})`;
}

async function submitTicketing() {
  const btn = document.getElementById("bookSubmitBtn");
  setBookingError("");
  if (!currentEventId) { setBookingError("No event selected."); return; }
  btn.disabled = true; btn.textContent = "Processing…";
  try {
    const data = await apiFetch("/api/bookings", {
      method: "POST",
      body: JSON.stringify({ event_id: currentEventId, ticket_quantity: currentTicketQuantity }),
    });
    currentBookingId = data.booking_id;
    closeBookingModal();
    openPaymentModal(data);
  } catch (err) {
    setBookingError(err.message);
  } finally {
    btn.disabled = false; btn.textContent = "Confirm Tickets";
  }
}

function openPaymentModal(bookingData) {
  const summaryEl = document.getElementById("paymentSummary");
  if (summaryEl) {
    summaryEl.innerHTML = `
      <div class="payment-summary-box">
        <strong>${bookingData.event_title}</strong><br>
        📅 ${bookingData.event_date || ""} &nbsp; 🕐 ${bookingData.event_time || ""}<br>
        🎟️ ${bookingData.ticket_quantity} ticket${bookingData.ticket_quantity > 1 ? "s" : ""}
        <div class="total-amount">Total: K${bookingData.total_price.toFixed(2)}</div>
      </div>`;
  }
  showCardPayment();
  clearPaymentErrors();
  const modal = document.getElementById("paymentModal");
  if (modal) modal.style.display = "flex";
}

function clearPaymentErrors() {
  ["cardError", "momoError", "momoPinError"].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.textContent = ""; el.style.display = "none"; }
  });
}

function showCardPayment() {
  document.getElementById("cardPaymentForm").style.display = "block";
  document.getElementById("momoPaymentForm").style.display = "none";
  document.getElementById("tabCard").classList.add("active");
  document.getElementById("tabMomo").classList.remove("active");
}

function showMomoPayment() {
  document.getElementById("cardPaymentForm").style.display = "none";
  document.getElementById("momoPaymentForm").style.display = "block";
  document.getElementById("tabMomo").classList.add("active");
  document.getElementById("tabCard").classList.remove("active");
  resetMomoFlow();
}

function resetMomoFlow() {
  document.getElementById("momoStep1").style.display = "block";
  document.getElementById("momoStep2").style.display = "none";
  const phoneEl = document.getElementById("momoPhone");
  if (phoneEl) phoneEl.value = "";
  const pinEl = document.getElementById("momoPin");
  if (pinEl) pinEl.value = "";
  clearPaymentErrors();
  currentTransactionId = null;
}

async function cancelPayment() {
  const modal = document.getElementById("paymentModal");
  if (modal) modal.style.display = "none";
  if (currentBookingId) {
    try { await apiFetch(`/api/bookings/${currentBookingId}/cancel`, { method: "PUT" }); } catch (_) {}
    currentBookingId = null;
  }
  currentTransactionId = null;
  initEvents(activeCategory);
}

async function submitCardPayment(e) {
  e.preventDefault();
  const btn        = document.getElementById("cardSubmitBtn");
  const cardNumber = document.getElementById("cardNumber")?.value.replace(/\s/g, "");
  const cardExpiry = document.getElementById("cardExpiry")?.value;
  const cardCVV    = document.getElementById("cardCVV")?.value;
  const errEl      = document.getElementById("cardError");
  if (errEl) errEl.style.display = "none";
  btn.disabled = true; btn.textContent = "Processing…";
  try {
    const data = await apiFetch("/api/payments", {
      method: "POST",
      body: JSON.stringify({ booking_id: currentBookingId, payment_method: "card", card_number: cardNumber, card_expiry: cardExpiry, card_cvv: cardCVV }),
    });
    document.getElementById("paymentModal").style.display = "none";
    showConfirmation(data);
    currentBookingId = null;
  } catch (err) {
    if (errEl) { errEl.textContent = err.message; errEl.style.display = "block"; }
  } finally {
    btn.disabled = false; btn.textContent = "Pay Now";
  }
}

async function submitMomoStep1() {
  const btn   = document.getElementById("momoStep1Btn");
  const phone = document.getElementById("momoPhone")?.value.trim();
  const errEl = document.getElementById("momoError");
  if (errEl) errEl.style.display = "none";
  btn.disabled = true; btn.textContent = "Sending…";
  try {
    const result = await apiFetch("/api/payments", {
      method: "POST",
      body: JSON.stringify({ booking_id: currentBookingId, payment_method: "mtn_momo", phone_number: phone }),
    });
    if (result._status202 && result.data) {
      currentTransactionId = result.data.transaction_id;
      document.getElementById("momoStep1").style.display = "none";
      document.getElementById("momoStep2").style.display = "block";
    } else { throw new Error("Unexpected response from server."); }
  } catch (err) {
    if (errEl) { errEl.textContent = err.message; errEl.style.display = "block"; }
  } finally {
    btn.disabled = false; btn.textContent = "Request Payment";
  }
}

async function submitMomoStep2() {
  const btn   = document.getElementById("momoStep2Btn");
  const pin   = document.getElementById("momoPin")?.value.trim();
  const errEl = document.getElementById("momoPinError");
  if (errEl) errEl.style.display = "none";
  if (!currentTransactionId) {
    if (errEl) { errEl.textContent = "Transaction expired. Please start again."; errEl.style.display = "block"; }
    return;
  }
  btn.disabled = true; btn.textContent = "Confirming…";
  try {
    const data = await apiFetch("/api/payments/confirm", {
      method: "POST",
      body: JSON.stringify({ transaction_id: currentTransactionId, pin }),
    });
    document.getElementById("paymentModal").style.display = "none";
    showConfirmation(data);
    currentBookingId = null; currentTransactionId = null;
  } catch (err) {
    if (errEl) { errEl.textContent = err.message; errEl.style.display = "block"; }
  } finally {
    btn.disabled = false; btn.textContent = "Confirm Payment";
  }
}

let currentConfirmedBookingId = null;

function showConfirmation(data) {
  const refEl       = document.getElementById("confirmationRef");
  const detailEl    = document.getElementById("confirmationDetails");
  const downloadBtn = document.getElementById("downloadTicketBtn");
  currentConfirmedBookingId = data.booking_id;
  if (refEl)    refEl.textContent    = `Booking Reference: ${data.booking_ref}`;
  if (detailEl) detailEl.textContent = `Amount paid: K${data.amount.toFixed(2)}. Your tickets are confirmed! Show this reference at the gate.`;
  if (downloadBtn) { downloadBtn.style.display = "inline-block"; downloadBtn.onclick = () => downloadTicket(data.booking_id); }
  document.getElementById("confirmationModal").style.display = "flex";
}

async function downloadTicket(bookingId) {
  const btn = document.getElementById("downloadTicketBtn");
  if (!btn) return;
  btn.disabled = true; btn.textContent = "Generating…";
  try {
    const token = localStorage.getItem("jwt");
    const response = await fetch(`${API}/api/payments/ticket/${bookingId}`, { headers: { "Authorization": `Bearer ${token}` } });
    if (!response.ok) { const json = await response.json(); throw new Error(json.message || "Failed to download ticket"); }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `EventZone_Ticket_${String(bookingId).padStart(6, "0")}.pdf`;
    document.body.appendChild(a); a.click();
    window.URL.revokeObjectURL(url); document.body.removeChild(a);
  } catch (err) { alert(`Error downloading ticket: ${err.message}`); }
  finally { btn.disabled = false; btn.textContent = "📥 Download Ticket PDF"; }
}

function closeConfirmation() {
  document.getElementById("confirmationModal").style.display = "none";
  initEvents(activeCategory);
}

document.addEventListener("DOMContentLoaded", () => {
  initEvents();
  const cardInput = document.getElementById("cardNumber");
  if (cardInput) {
    cardInput.addEventListener("input", () => {
      let val = cardInput.value.replace(/\D/g, "").substring(0, 16);
      cardInput.value = val.replace(/(.{4})/g, "$1 ").trim();
    });
  }
  const expiryInput = document.getElementById("cardExpiry");
  if (expiryInput) {
    expiryInput.addEventListener("input", () => {
      let val = expiryInput.value.replace(/\D/g, "").substring(0, 4);
      if (val.length >= 3) val = val.substring(0, 2) + "/" + val.substring(2);
      expiryInput.value = val;
    });
  }
  ["bookingModal", "paymentModal", "confirmationModal", "authModal"].forEach(id => {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.addEventListener("click", (e) => {
      if (e.target !== modal) return;
      if (id === "bookingModal")           closeBookingModal();
      else if (id === "paymentModal")      cancelPayment();
      else if (id === "confirmationModal") closeConfirmation();
      else if (id === "authModal")         closeModal();
    });
  });
  window.addEventListener("auth:login",  () => initEvents(activeCategory));
  window.addEventListener("auth:logout", () => initEvents(activeCategory));
});
