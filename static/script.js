const backendURL = "https://your-backend-url.onrender.com"; // ⚠️ Change this

async function fetchSlots() {
    try {
        const response = await fetch(`${backendURL}/slots/`);
        const slots = await response.json();

        const container = document.getElementById("slot-status");
        container.innerHTML = "";

        slots.forEach(slot => {
            const div = document.createElement("div");
            div.className = `slot ${slot.is_occupied ? "occupied" : "vacant"}`;
            div.innerHTML = `
                <h4>Slot ${slot.slot_id}</h4>
                <p>Status: ${slot.is_occupied ? "Occupied" : "Vacant"}</p>
                ${slot.is_occupied ? `<p>Vehicle ID: ${slot.vehicle_id}</p>` : ""}
            `;
            container.appendChild(div);
        });
    } catch (error) {
        document.getElementById("slot-status").innerHTML = "<p>⚠️ Could not load slot data.</p>";
        console.error("Error fetching slots:", error);
    }
}

fetchSlots();
setInterval(fetchSlots, 5000); // Refresh every 5s
