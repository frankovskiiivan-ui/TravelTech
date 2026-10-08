const API = "";

// ==========================================
// ШАГ 1: Поиск рейсов
// ==========================================
document.getElementById("search-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const city_from = document.getElementById("city_from").value.trim();
    const city_to = document.getElementById("city_to").value.trim();
    const date = document.getElementById("date").value || null;

    const list = document.getElementById("flights-list");
    list.innerHTML = "<p class='hint'>Поиск...</p>";

    try {
        const res = await fetch(`${API}/api/search-flights`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ city_from, city_to, date }),
        });
        const data = await res.json();
        renderFlights(data.flights || []);
    } catch (err) {
        list.innerHTML = `<p class="error">Ошибка: ${err.message}</p>`;
    }
});

function renderFlights(flights) {
    const list = document.getElementById("flights-list");

    if (!flights.length) {
        list.innerHTML = "<p class='hint'>Рейсы не найдены. Проверьте города и дату.</p>";
        return;
    }

    list.innerHTML = flights.map(f => {
        const price = Number(f.price_per_ticket) || 0;
        const seats = Number(f.seats_left) || 0;
        const flightIata = f.flight_iata || "—";
        const depIata = f.dep_iata || "—";
        const arrIata = f.arr_iata || "—";

        return `
            <div class="flight-card">
                <div class="flight-info">
                    <b>${flightIata}</b>
                    <span class="route">${depIata} → ${arrIata}</span>
                    <small>${f.dep_time || "?"} → ${f.arr_time || "?"}</small>
                    <small>Мест: ${seats} | Цена: ${price.toLocaleString("ru-RU")} ₽</small>
                </div>
                <div class="flight-actions">
                    <input type="number" min="1" max="9" value="1"
                           id="pax-${flightIata}" class="pax-input">
                    <button onclick="bookFlight('${flightIata}')">Забронировать</button>
                </div>
            </div>
        `;
    }).join("");
}

// ==========================================
// ШАГ 2: Бронирование
// ==========================================
async function bookFlight(flight_iata) {
    const paxInput = document.getElementById(`pax-${flight_iata}`);
    const passengers = parseInt(paxInput.value) || 1;
    const user_id = "user_" + Math.floor(Math.random() * 1000);

    try {
        const res = await fetch(`${API}/api/book-trip`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id, flight_iata, passengers }),
        });

        const trip = await res.json();

        // Проверяем статус в теле ответа, а не HTTP-код
        if (trip.status === "FLIGHT_NOT_FOUND") {
            alert("Рейс не найден в API. Попробуйте другой рейс.");
            return;
        }
        if (trip.status === "NO_SEATS") {
            alert(trip.message || "Недостаточно мест");
            return;
        }
        if (trip.status === "ERROR") {
            alert(trip.message || "Ошибка бронирования");
            return;
        }

        renderBooking(trip);
        await loadTrips();
        await loadStats();
    } catch (err) {
        alert("Ошибка: " + err.message);
    }
}

// ==========================================
// ШАГ 3: Отрисовка брони + отелей
// ==========================================
function renderBooking(trip) {
    const section = document.getElementById("hotels-section");
    section.classList.remove("hidden");

    const f = trip.flight || {};
    const summary = document.getElementById("booking-summary");

    // Безопасное извлечение
    const totalPrice = Number(trip.total_price) || 0;
    const passengers = Number(trip.passengers) || 1;
    const flightIata = f.flight_iata || f.flight || "—";
    const depIata = f.dep_iata || "—";
    const arrIata = f.arr_iata || "—";

    summary.innerHTML = `
        <div class="summary-card">
            <h3>✅ Бронирование ${trip.trip_id || "—"}</h3>
            <p>Рейс <b>${flightIata}</b> (${depIata} → ${arrIata})</p>
            <p>Пассажиров: <b>${passengers}</b></p>
            <p>Итого: <b>${totalPrice.toLocaleString("ru-RU")} ₽</b></p>
            <p>Город прибытия: <b>${trip.city || "не определён"}</b></p>
        </div>
    `;

    const list = document.getElementById("hotels-list");
    const hotels = trip.hotels || [];

    if (!hotels.length) {
        list.innerHTML = `
            <p class="hint">
                Отели не найдены для города "${trip.city || "не определён"}".<br>
                Возможные причины: город не поддерживается StayingAPI или сервис временно недоступен.
            </p>
        `;
        return;
    }

    // Предупреждение про sandbox
    const isSandbox = hotels.some(h =>
        h.actual_city && trip.city &&
        !trip.city.toLowerCase().includes((h.actual_city || "").toLowerCase())
    );

    let html = "";
    if (isSandbox) {
        html += `<p style="opacity:0.65;font-size:0.85em;margin-bottom:12px;">
            ⚠️ Данные из sandbox-режима StayingAPI: цены реальные, но города фиксированные.
            Для реальных отелей нужен боевой ключ <code>stay_live_...</code>
        </p>`;
    }

    html += hotels.map(h => renderHotelCard(h)).join("");
    list.innerHTML = html;
}

// ==========================================
// Карточка одного отеля
// ==========================================
function renderHotelCard(h) {
    const price = Number(h.price) || 0;
    const nightly = Number(h.nightly_price) || 0;
    const rating = Number(h.rating) || 0;
    const ratingScale = Number(h.rating_scale) || 5;
    const currency = h.currency || "EUR";
    const platform = (h.platform || h.source || "").toLowerCase();
    const nights = Number(h.nights) || 1;
    const reviews = Number(h.review_count) || 0;
    const bedrooms = h.bedrooms;
    const bathrooms = h.bathrooms;
    const maxOcc = h.max_occupancy;
    const propertyType = h.property_type || "";
    const isSuperhost = h.is_superhost;
    const hostName = h.host_name || "";
    const image = h.image || "";
    const url = h.url || "";
    const listingId = h.listing_id || "";

    // Нормализуем рейтинг к 5-балльной шкале
    const ratingNorm = ratingScale > 0 ? (rating / ratingScale) * 5 : rating;

    // Иконка платформы
    const platformIcon = platform.includes("airbnb") ? "🏠" : "🏨";
    const platformLabel = platform.charAt(0).toUpperCase() + platform.slice(1);

    // Мета-строка
    const metaParts = [];
    if (propertyType) metaParts.push(propertyType);
    if (bedrooms) metaParts.push(`${bedrooms} спален`);
    if (bathrooms) metaParts.push(`${bathrooms} ванн`);
    if (maxOcc) metaParts.push(`до ${maxOcc} гостей`);

    return `
        <div class="hotel-card">
            ${image ? `<img class="hotel-image" src="${image}" alt="${escapeHtml(h.hotel)}" onerror="this.style.display='none'">` : ""}
            <div class="hotel-body">
                <div class="hotel-header">
                    <b>${escapeHtml(h.hotel || "Unknown")}</b>
                    <span class="platform platform-${platform}">${platformIcon} ${platformLabel}</span>
                    ${isSuperhost ? `<span class="superhost">⭐ Superhost</span>` : ""}
                </div>
                ${metaParts.length ? `<p class="hotel-meta">${metaParts.join(" · ")}</p>` : ""}
                <div class="hotel-rating">
                    <span class="stars">${"★".repeat(Math.round(ratingNorm))}${"☆".repeat(5 - Math.round(ratingNorm))}</span>
                    <span>${rating.toFixed(1)}/${ratingScale}</span>
                    ${reviews ? `<span class="reviews">(${reviews} отзывов)</span>` : ""}
                </div>
                ${hostName ? `<p class="hotel-host">Хозяин: ${escapeHtml(hostName)}</p>` : ""}
                ${h.actual_city && h.actual_city !== h.city ? `
                    <p class="hotel-location">
                        📍 ${escapeHtml(h.actual_city)}${h.country ? ", " + h.country : ""}
                    </p>
                ` : ""}
            </div>
            <div class="hotel-price">
                <div class="price-total">${price.toLocaleString("ru-RU")} ${currency}</div>
                <div class="price-nights">${nightly.toLocaleString("ru-RU")} ${currency} × ${nights} ноч.</div>
                ${url ? `<a href="${url}" target="_blank" class="book-link">Забронировать</a>` : `<span class="no-link">Ссылка недоступна</span>`}
            </div>
        </div>
    `;
}

// ==========================================
// История поездок
// ==========================================
async function loadTrips() {
    try {
        const res = await fetch(`${API}/api/trips`);
        const trips = await res.json();
        const list = document.getElementById("trips-list");

        if (!trips.length) {
            list.innerHTML = "<p class='hint'>Пока нет бронирований</p>";
            return;
        }

        list.innerHTML = trips.map(t => {
            const f = t.flight || {};
            const status = f.status || "UNKNOWN";
            const flightIata = f.flight_iata || f.flight || "—";
            const price = Number(t.total_price) || 0;

            return `
                <div class="trip-item">
                    <div>
                        <b>${t.trip_id}</b> — ${flightIata}
                        <span class="badge ${status}">${status}</span>
                        <small>${t.user_id || ""} | ${t.city || ""} | ${price.toLocaleString("ru-RU")} ₽</small>
                    </div>
                </div>
            `;
        }).join("");
    } catch (err) {
        console.error("loadTrips error:", err);
    }
}

// ==========================================
// Статистика
// ==========================================
async function loadStats() {
    try {
        const res = await fetch(`${API}/api/stats`);
        const s = await res.json();

        const set = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        set("stat-total", s.total_trips || 0);
        set("stat-ontime", s.on_time || 0);
        set("stat-delayed", s.delayed || 0);
        set("stat-cancelled", s.cancelled || 0);
        set("stat-rating", s.avg_rating || 0);
        set("stat-notifs", s.notifications_sent || 0);
    } catch (_) {}
}

// ==========================================
// Хелперы
// ==========================================
function escapeHtml(str) {
    if (typeof str !== "string") return "";
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ==========================================
// Инициализация
// ==========================================
loadTrips();
loadStats();
setInterval(loadStats, 5000);
