document.addEventListener("DOMContentLoaded", () => {
  const feedImage = document.getElementById("camera-feed");
  const refreshBtn = document.getElementById("refresh-feed");
  const nightVisionBtn = document.getElementById("toggle-night-vision");
  const autofocusBtn = document.getElementById("toggle-autofocus");
  const cameraListContainer = document.getElementById("camera-list-container");

  const API_BASE = "http://localhost:8000/api";

  async function loadFeed() {
    try {
      const response = await fetch(`${API_BASE}/live_feed`);
      if (response.ok) {
        const blob = await response.blob();
        feedImage.src = URL.createObjectURL(blob);
      } else {
        console.error("Failed to load feed");
      }
    } catch (err) {
      console.error("Error loading feed:", err);
    }
  }

  async function toggleNightVision() {
    try {
      const response = await fetch(`${API_BASE}/controls/night_vision`, {
        method: "POST"
      });
      const result = await response.json();
      alert(result.message);
    } catch (err) {
      console.error("Night vision toggle failed:", err);
    }
  }

  async function toggleAutofocus() {
    try {
      const response = await fetch(`${API_BASE}/controls/autofocus`, {
        method: "POST"
      });
      const result = await response.json();
      alert(result.message);
    } catch (err) {
      console.error("Autofocus toggle failed:", err);
    }
  }

  async function loadCameras() {
    try {
      const response = await fetch(`${API_BASE}/cameras`);
      const cameras = await response.json();
      cameraListContainer.innerHTML = "";
      cameras.forEach((cam) => {
        const li = document.createElement("li");
        li.textContent = `${cam.name} - ${cam.status}`;
        cameraListContainer.appendChild(li);
      });
    } catch (err) {
      console.error("Failed to load cameras:", err);
    }
  }

  refreshBtn.addEventListener("click", loadFeed);
  nightVisionBtn.addEventListener("click", toggleNightVision);
  autofocusBtn.addEventListener("click", toggleAutofocus);

  // Initial load
  loadFeed();
  loadCameras();
});