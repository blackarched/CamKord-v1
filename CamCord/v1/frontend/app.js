document.addEventListener("DOMContentLoaded", () => {
    const feedImage = document.getElementById("camera-feed");
    const refreshBtn = document.getElementById("refresh-feed"); // Will need to be auth-aware
    const nightVisionBtn = document.getElementById("toggle-night-vision");
    const autofocusBtn = document.getElementById("toggle-autofocus");
    const cameraListContainer = document.getElementById("camera-list-container");

    const loginSection = document.getElementById("login-section");
    const mainAppContent = document.getElementById("main-app-content");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const loginButton = document.getElementById("login-button");
    const logoutButton = document.getElementById("logout-button");
    const loginMessage = document.getElementById("login-message");
    
    let authToken = localStorage.getItem('authToken');
    const AUTH_API_BASE = "http://localhost:8000/auth"; // For /token
    const API_BASE = "http://localhost:8000/api"; // For other API calls

    let selectedCameraId = null;
    let camerasCache = []; // To store the last loaded camera list/details
    let videoSocket = null; 

    function showLoginForm() {
        if (loginSection) loginSection.style.display = "block";
        if (mainAppContent) mainAppContent.style.display = "none";
        if (logoutButton) logoutButton.style.display = "none";
        if (loginMessage) loginMessage.textContent = ""; // Clear message on showing form
    }

    function showAppContent() {
        if (loginSection) loginSection.style.display = "none";
        if (mainAppContent) mainAppContent.style.display = "block";
        if (logoutButton) logoutButton.style.display = "block";
    }

    function updateUIForAuthState() {
        if (authToken) {
            showAppContent();
            // Attempt to load data if logged in
            loadCameras(); 
            // loadFeed(); // Postpone loadFeed until camera selection is implemented
        } else {
            showLoginForm();
        }
    }

    async function handleLogin() {
        if (!usernameInput || !passwordInput || !loginMessage) return;
        const username = usernameInput.value;
        const password = passwordInput.value;
        loginMessage.textContent = "Logging in...";

        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        try {
            const response = await fetch(`${AUTH_API_BASE}/token`, {
                method: "POST",
                body: formData // FastAPI's OAuth2PasswordRequestForm expects form data
            });

            if (response.ok) {
                const data = await response.json();
                authToken = data.access_token;
                localStorage.setItem('authToken', authToken);
                loginMessage.textContent = "";
                updateUIForAuthState(); // This will call showAppContent and load data
            } else {
                const errorData = await response.json().catch(() => ({ detail: "Login failed. Invalid credentials or server error." }));
                authToken = null;
                localStorage.removeItem('authToken');
                loginMessage.textContent = `Login failed: ${errorData.detail || "Unknown error"}`;
                showLoginForm(); // Explicitly show form on error
            }
        } catch (err) {
            console.error("Login request error:", err);
            authToken = null;
            localStorage.removeItem('authToken');
            loginMessage.textContent = "Login error. Check console.";
            showLoginForm(); // Explicitly show form on error
        }
    }
    if (loginButton) loginButton.addEventListener('click', handleLogin);

    function handleLogout() {
        if (videoSocket) {
            console.log("Logging out, closing WebSocket.");
            videoSocket.onclose = null; // Avoid default onclose logic during logout
            videoSocket.close(1000, "User logged out"); // Normal closure
            videoSocket = null;
        }
        authToken = null;
        localStorage.removeItem('authToken');
        if (feedImage) feedImage.src = ""; 
        if (cameraListContainer) cameraListContainer.innerHTML = "";
        updateUIForAuthState(); // This will call showLoginForm
    }
    if (logoutButton) logoutButton.addEventListener('click', handleLogout);

    function selectCamera(camera) {
        const cameraListItems = document.querySelectorAll("#camera-list-container li");
        
        if (!camera || camera.id === undefined) {
            console.log("No camera selected or invalid camera object.");
            selectedCameraId = null;
            if (feedImage) feedImage.src = ""; // Clear feed if no camera
            cameraListItems.forEach(item => item.classList.remove("selected-camera"));
            // TODO: Update UI or disable controls if no camera is selected
            return;
        }

        selectedCameraId = camera.id;
        console.log(`Camera selected: ID ${selectedCameraId}, Name: ${camera.name}`);

        // Update UI for selected camera
        cameraListItems.forEach(item => {
            if (item.dataset.cameraId == selectedCameraId) { // Note: dataset values are strings
                item.classList.add("selected-camera"); // Use a distinct class name
            } else {
                item.classList.remove("selected-camera");
            }
        });

        // Placeholder for loadFeed - will be implemented in next step
        if (typeof loadFeed === "function") {
            loadFeed(selectedCameraId); 
        } else {
            console.warn("loadFeed function not yet fully implemented for selected camera.");
        }
        // Placeholder for updating controls based on selected camera
        // if (typeof updateControlsForCamera === "function") {
        //    updateControlsForCamera(selectedCameraId); 
        // }
    }

    async function fetchWithAuth(url, options = {}) {
        const headers = { ...options.headers };
        if (authToken) {
            headers['Authorization'] = `Bearer ${authToken}`;
        }

        const fetchOptions = { ...options, headers };
        const response = await fetch(url, fetchOptions);

        if (response.status === 401) { // Unauthorized
            console.warn("Unauthorized request or token expired. Logging out.");
            handleLogout(); // Clear token and redirect to login
            throw new Error('Unauthorized'); // Propagate error to stop further processing in calling function
        }
        return response;
    }

  // Existing functions like loadFeed, toggleNightVision, etc. will be updated next or removed.
  // For now, just keeping the placeholders for modification.
  function loadFeed(cameraId) {
    if (videoSocket) {
        console.log(`Closing existing WebSocket connection before opening new one.`);
        videoSocket.onclose = null; // Prevent old onclose from triggering after explicit close
        videoSocket.close(1000, "Client initiated new connection"); // Normal closure
        videoSocket = null;
    }

    if (!feedImage) {
        console.error("feedImage element not found.");
        return;
    }

    if (cameraId === null || cameraId === undefined) { // Allow cameraId 0 if valid
        console.log("loadFeed called without valid cameraId for WebSocket, clearing feed.");
        feedImage.src = ""; 
        feedImage.alt = "No camera selected.";
        return;
    }

    if (!authToken) {
        console.warn("Cannot establish WebSocket video stream: No auth token.");
        feedImage.src = "";
        feedImage.alt = "Please login to view feed.";
        // Potentially call showLoginForm() or handleLogout() here if strict
        return;
    }

    // Backend needs to be adjusted to accept token via query param for WebSocket
    const wsUrl = `ws://localhost:8000/ws/stream/${cameraId}?token=${encodeURIComponent(authToken)}`;
    console.log(`Attempting to connect to WebSocket: ${wsUrl}`);
    feedImage.src = ""; // Clear previous image
    feedImage.alt = `Connecting to camera ${cameraId}...`;

    try {
        videoSocket = new WebSocket(wsUrl);
    } catch (error) {
        console.error(`Error creating WebSocket: ${error}`);
        feedImage.alt = `Failed to create WebSocket for camera ${cameraId}.`;
        videoSocket = null;
        return;
    }
    
    videoSocket.binaryType = "arraybuffer"; 

    videoSocket.onopen = () => {
        console.log(`WebSocket connection opened for camera ${cameraId}: ${wsUrl}`);
        feedImage.alt = `Live feed from camera ${cameraId}`;
    };

    let previousObjectURL = null; // To manage revoking object URLs

    videoSocket.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
            if (previousObjectURL) {
                URL.revokeObjectURL(previousObjectURL); // Revoke the old one before creating new
            }
            const arrayBufferView = new Uint8Array(event.data);
            const blob = new Blob([arrayBufferView], { type: 'image/jpeg' });
            const imageUrl = URL.createObjectURL(blob);
            feedImage.src = imageUrl;
            previousObjectURL = imageUrl; // Store for next revocation
        } else {
             console.warn("WebSocket received non-ArrayBuffer data:", event.data);
        }
    };

    videoSocket.onerror = (error) => {
        console.error(`WebSocket Error for camera ${cameraId}:`, error);
        if (feedImage) {
            feedImage.src = "";
            feedImage.alt = `Error with stream for camera ${cameraId}. Connection failed or interrupted.`;
        }
        if (previousObjectURL) {
            URL.revokeObjectURL(previousObjectURL);
            previousObjectURL = null;
        }
    };

    videoSocket.onclose = (event) => {
        console.log(`WebSocket connection closed for camera ${cameraId}. Code: ${event.code}, Reason: '${event.reason}', WasClean: ${event.wasClean}`);
        if (feedImage) {
            feedImage.src = ""; // Clear image on close
            if (!event.wasClean) {
                feedImage.alt = `Stream for camera ${cameraId} disconnected unexpectedly.`;
            } else {
                feedImage.alt = `Stream for camera ${cameraId} closed.`;
            }
        }
        if (previousObjectURL) {
            URL.revokeObjectURL(previousObjectURL);
            previousObjectURL = null;
        }
        // Only nullify if this specific socket instance is closing,
        // to prevent race conditions if a new socket was opened quickly.
        if (videoSocket === event.target) {
            videoSocket = null;
        }
    };
  }

  async function toggleNightVision() {
    // TODO: This function will need to be adapted for a selected camera
    // and use fetchWithAuth.
    console.log("toggleNightVision called - needs update");
    // try {
    //   const response = await fetch(`${API_BASE}/controls/night_vision`, { // OLD
    //     method: "POST"
    //   });
    //   const result = await response.json();
    //   alert(result.message);
    // } catch (err) {
    //   console.error("Night vision toggle failed:", err);
    // }
  }

  async function toggleAutofocus() {
    // TODO: This function will need to be adapted for a selected camera
    // and use fetchWithAuth.
    console.log("toggleAutofocus called - needs update");
    // try {
    //   const response = await fetch(`${API_BASE}/controls/autofocus`, { // OLD
    //     method: "POST"
    //   });
    //   const result = await response.json();
    //   alert(result.message);
    // } catch (err) {
    //   console.error("Autofocus toggle failed:", err);
    // }
  }

  async function loadCameras() {
    if (!authToken) return; // Don't try if not logged in
    try {
        // const response = await fetch(`${API_BASE}/cameras`); // OLD
        const response = await fetchWithAuth(`${API_BASE}/cameras`); // NEW
        if (response.ok) {
            const cameras = await response.json();
            if (cameraListContainer) {
                cameraListContainer.innerHTML = ""; // Clear previous list
                cameras.forEach((cam) => {
                    const li = document.createElement("li");
                    li.dataset.cameraId = cam.id; // Add data attribute
                    li.textContent = `${cam.name} - ${cam.is_running ? 'Running' : 'Stopped'}`;
                    li.addEventListener('click', () => selectCamera(cam)); // Add click listener
                    cameraListContainer.appendChild(li);
                });
                
                camerasCache = cameras; // Update cache

                if (cameras.length > 0) {
                    let cameraToSelect = null;
                    // Check if previously selected camera is still in the list
                    if (selectedCameraId !== null) {
                        const stillExists = cameras.find(c => c.id === selectedCameraId);
                        if (stillExists) {
                            cameraToSelect = stillExists;
                        }
                    }
                    // If no valid previous selection, or it's gone, select the first camera
                    if (!cameraToSelect) {
                        cameraToSelect = cameras[0];
                    }
                    selectCamera(cameraToSelect); // Select the determined camera
                } else {
                    // No cameras available
                    selectCamera(null); // Clear any selection, hide feed etc.
                    if (cameraListContainer) cameraListContainer.innerHTML = "<li>No cameras available.</li>";
                }
            }
        } else {
            console.error("Failed to load cameras:", response.status, await response.text());
            camerasCache = []; // Clear cache on error
            selectCamera(null); // Clear selection
        }
    } catch (err) { // Errors from fetchWithAuth (like 'Unauthorized') will be caught here
        console.error("Error in loadCameras:", err);
    }
  }

  // Comment out or adapt old event listeners
  // if (refreshBtn) refreshBtn.addEventListener("click", loadFeed); // Old loadFeed is not suitable
  if (refreshBtn) { // Ensure button exists
      refreshBtn.style.display = 'block'; // Make it visible now
      refreshBtn.addEventListener('click', () => {
          if (selectedCameraId !== null) { // Check if a camera is selected
              console.log(`Refresh button clicked for camera ID: ${selectedCameraId}`);
              loadFeed(selectedCameraId);
          } else {
              console.log("Refresh button clicked, but no camera selected.");
              loadFeed(null); // Clear feed if no camera selected
          }
      });
  }
  if (nightVisionBtn) nightVisionBtn.addEventListener("click", toggleNightVision); // Will be per-camera
  if (autofocusBtn) autofocusBtn.addEventListener("click", toggleAutofocus);   // Will be per-camera


  // Initial UI state update based on stored token
  updateUIForAuthState();
});