// Use relative URL so it works on Render without hardcoding backendURL
const backendURL = ""; // Empty string → fetches from same origin

async function fetchSlots() {
    try {
        const response = await fetch(`${backendURL}/slots/`);
        const slots = await response.json();

        const container = document.getElementById("slot-status");
        container.innerHTML = ""; // Clear previous content

        slots.forEach(slot => {
            const div = document.createElement("div");
            div.className = `slot ${slot.is_occupied ? "occupied" : "vacant"}`;
            div.innerHTML = `
                <h4>Slot ${slot.slot_id}</h4>
                <p>Status: ${slot.is_occupied ? "Occupied" : "Vacant"}</p>
                ${slot.is_occupied ? `<p>Vehicle ID: ${slot.vehicle_id}</p>
                <a href="/slot/${slot.slot_id}">View Details</a>` : ""}
            `;
            container.appendChild(div);
        });
    } catch (error) {
        document.getElementById("slot-status").innerHTML = "<p>⚠️ Could not load slot data.</p>";
        console.error("Error fetching slots:", error);
    }
}

// Initial fetch
fetchSlots();

// Auto-refresh every 5 seconds
setInterval(fetchSlots, 5000);
