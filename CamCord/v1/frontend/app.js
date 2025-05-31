document.addEventListener("DOMContentLoaded", () => {
    const feedImage = document.getElementById("camera-feed");
    const refreshBtn = document.getElementById("refresh-feed");
    // const nightVisionBtn = document.getElementById("toggle-night-vision"); // Removed
    // const autofocusBtn = document.getElementById("toggle-autofocus"); // Removed
    const cameraListContainer = document.getElementById("camera-list-container");

    const loginSection = document.getElementById("login-section");
    const mainAppContent = document.getElementById("main-app-content");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const loginButton = document.getElementById("login-button");
    const logoutButton = document.getElementById("logout-button");
    const loginMessage = document.getElementById("login-message");
    const appMessageArea = document.getElementById("app-message-area");
    const appMessageText = document.getElementById("app-message-text");

    const selectedCameraIdDisplay = document.getElementById("selected-camera-id-display");
    const settingResolution = document.getElementById("setting-resolution");
    const settingBrightness = document.getElementById("setting-brightness");
    const brightnessValueLabel = document.getElementById("brightness-value-label");
    const settingContrast = document.getElementById("setting-contrast");
    const contrastValueLabel = document.getElementById("contrast-value-label");
    const settingSaturation = document.getElementById("setting-saturation");
    const saturationValueLabel = document.getElementById("saturation-value-label");
    const settingSharpness = document.getElementById("setting-sharpness");
    const sharpnessValueLabel = document.getElementById("sharpness-value-label");
    const settingNightVision = document.getElementById("setting-night-vision");
    const settingAutofocus = document.getElementById("setting-autofocus");
    const settingMicrophoneEnabled = document.getElementById("setting-microphone-enabled");
    const settingObjectDetectionEnabled = document.getElementById("setting-object-detection-enabled");
    const settingMotionDetectionEnabled = document.getElementById("setting-motion-detection-enabled");
    const settingMotionSensitivity = document.getElementById("setting-motion-sensitivity");
    const motionSensitivityValueLabel = document.getElementById("motion-sensitivity-value-label");
    const settingMotionMinArea = document.getElementById("setting-motion-min-area");
    const settingRecordOnMotion = document.getElementById("setting-record-on-motion");
    const saveCameraSettingsButton = document.getElementById("save-camera-settings");

    let authToken = localStorage.getItem('authToken');
    const AUTH_API_BASE = "http://localhost:8000/auth"; // For /token
    const API_BASE = "http://localhost:8000/api"; // For other API calls

    let selectedCameraId = null;
    let camerasCache = []; // To store the last loaded camera list/details
    let videoSocket = null;
    let currentCameraSettings = null;

    function showLoginForm() {
        if (loginSection) loginSection.style.display = "block";
        if (mainAppContent) mainAppContent.style.display = "none";
        if (logoutButton) logoutButton.style.display = "none";
        if (loginMessage) loginMessage.textContent = "";
        if (appMessageArea) appMessageArea.style.display = 'none'; // Clear app message too
    }

    let appMessageTimeout = null;
    function showAppMessage(message, type = 'info', duration = 3000) {
        if (!appMessageArea || !appMessageText) return;

        clearTimeout(appMessageTimeout);

        appMessageText.textContent = message;
        appMessageArea.style.display = 'block';

        switch (type) {
            case 'error':
                appMessageArea.style.color = '#721c24';
                appMessageArea.style.backgroundColor = '#f8d7da';
                appMessageArea.style.borderColor = '#f5c6cb';
                break;
            case 'success':
                appMessageArea.style.color = '#155724';
                appMessageArea.style.backgroundColor = '#d4edda';
                appMessageArea.style.borderColor = '#c3e6cb';
                break;
            case 'warning':
                appMessageArea.style.color = '#856404';
                appMessageArea.style.backgroundColor = '#fff3cd';
                appMessageArea.style.borderColor = '#ffeeba';
                break;
            default: // 'info'
                appMessageArea.style.color = '#0c5460';
                appMessageArea.style.backgroundColor = '#d1ecf1';
                appMessageArea.style.borderColor = '#bee5eb';
                break;
        }

        if (duration > 0) {
            appMessageTimeout = setTimeout(() => {
                if (appMessageArea) appMessageArea.style.display = 'none';
                if (appMessageText) appMessageText.textContent = '';
            }, duration);
        }
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
            // loadFeed() is called via selectCamera -> loadCameras
        } else {
            showLoginForm();
            fetchCameraSettings(null); // Ensure controls are reset/disabled
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
                loginMessage.textContent = ""; // Clear specific login form message
                updateUIForAuthState();
                showAppMessage("Login successful!", "success", 2000);
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

        if (cameraListContainer) cameraListContainer.innerHTML = "";
        currentCameraSettings = null;
        updateControlsUI(null); // Pass null to reset UI
        if (appMessageArea) appMessageArea.style.display = 'none';
        updateUIForAuthState();
    }
    if (logoutButton) logoutButton.addEventListener('click', handleLogout);

    function updateControlsUI(settings) { // Takes settings as argument
        const isEnabled = settings !== null && mainAppContent.style.display !== 'none';

        if (selectedCameraIdDisplay) {
            selectedCameraIdDisplay.textContent = settings ? selectedCameraId : "N/A";
        }

        // Helper to set value and disabled state
        const configureInput = (element, value, disabledState) => {
            if (element) {
                if (element.type === 'checkbox') element.checked = value;
                else element.value = value;
                element.disabled = disabledState;
            }
        };
        const configureRangeWithValue = (rangeEl, labelEl, value, disabledState) => {
            if (rangeEl) {
                rangeEl.value = value;
                rangeEl.disabled = disabledState;
            }
            if (labelEl) labelEl.textContent = disabledState ? '-' : value;
        };

        configureInput(settingResolution, settings ? settings.resolution : "1280x720", !isEnabled);
        configureRangeWithValue(settingBrightness, brightnessValueLabel, settings ? settings.brightness : 50, !isEnabled);
        configureRangeWithValue(settingContrast, contrastValueLabel, settings ? settings.contrast : 50, !isEnabled);
        configureRangeWithValue(settingSaturation, saturationValueLabel, settings ? settings.saturation : 50, !isEnabled);
        configureRangeWithValue(settingSharpness, sharpnessValueLabel, settings ? settings.sharpness : 50, !isEnabled);

        configureInput(settingNightVision, settings ? settings.night_vision : false, !isEnabled);
        configureInput(settingAutofocus, settings ? settings.autofocus : true, !isEnabled);
        configureInput(settingMicrophoneEnabled, settings ? settings.microphone_enabled : true, !isEnabled);
        configureInput(settingObjectDetectionEnabled, settings ? settings.object_detection_enabled : false, !isEnabled);

        configureInput(settingMotionDetectionEnabled, settings ? settings.motion_detection_enabled : false, !isEnabled);
        configureRangeWithValue(settingMotionSensitivity, motionSensitivityValueLabel, settings ? settings.motion_sensitivity : 30, !isEnabled);
        configureInput(settingMotionMinArea, settings ? settings.motion_min_area : 500, !isEnabled);
        configureInput(settingRecordOnMotion, settings ? settings.record_on_motion : false, !isEnabled);

        if (saveCameraSettingsButton) saveCameraSettingsButton.disabled = !isEnabled;
        // Old button references (nightVisionBtn, autofocusBtn) and their logic removed as elements are gone.
    }

    async function fetchCameraSettings(cameraId) {
        if (!mainAppContent || mainAppContent.style.display === 'none') return;

        if (!cameraId && cameraId !== 0) {
            currentCameraSettings = null;
            updateControlsUI(null); // Pass null
            return;
        }
        if (!authToken) {
            currentCameraSettings = null;
            updateControlsUI(null); // Pass null
            return;
        }

        console.log(`Fetching settings for camera ${cameraId}...`);
        try {
            const response = await fetchWithAuth(`${API_BASE}/settings/${cameraId}`);
            if (response.ok) {
                currentCameraSettings = await response.json();
                console.log(`Settings loaded for camera ${cameraId}:`, currentCameraSettings);
            } else {
                console.error(`Failed to load settings for camera ${cameraId}: ${response.status}`);
                showAppMessage(`Failed to load settings for camera ${cameraId}. Status: ${response.status}`, 'error', 5000);
                currentCameraSettings = null;
            }
        } catch (err) {
            console.error(`Error fetching settings for camera ${cameraId}:`, err);
            if (err.message !== 'Unauthorized') {
                showAppMessage(`Error fetching settings for camera ${cameraId}. Check console.`, 'error', 5000);
            }
            currentCameraSettings = null;
        }
        updateControlsUI(currentCameraSettings); // Explicitly pass currentCameraSettings or null
    }

    function selectCamera(camera) {
        const cameraListItems = document.querySelectorAll("#camera-list-container li");

        if (!camera || camera.id === undefined) {
            console.log("No camera selected or invalid camera object.");
            selectedCameraId = null;
            if (feedImage) feedImage.src = "";
            cameraListItems.forEach(item => item.classList.remove("selected-camera"));
            fetchCameraSettings(null); // Clear settings and update controls UI
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

        if (selectedCameraId !== null) {
            loadFeed(selectedCameraId);
            fetchCameraSettings(selectedCameraId);
        } else {
            loadFeed(null);
            fetchCameraSettings(null);
        }
    }

    async function updateCameraSettingsBatch(payloadObject) {
        if (selectedCameraId === null) {
            showAppMessage("No camera selected to update settings for.", "error");
            return;
        }
        if (!authToken || Object.keys(payloadObject).length === 0) {
            console.log("No settings payload to update or not authenticated.");
            return;
        }

        showAppMessage("Applying configuration...", "info", 0);

        console.log(`Updating settings for camera ${selectedCameraId} with payload:`, payloadObject);
        try {
            const response = await fetchWithAuth(`${API_BASE}/settings/${selectedCameraId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payloadObject)
            });
            if (response.ok) {
                currentCameraSettings = await response.json();
                showAppMessage("Camera settings updated successfully!", 'success');
            } else {
                const errorData = await response.json().catch(() => ({ detail: "Unknown server error" }));
                console.error(`Failed to update settings for camera ${selectedCameraId}: ${response.status}`, errorData);
                showAppMessage(`Failed to update settings: ${errorData.detail || response.statusText}`, 'error', 5000);
                if (selectedCameraId !== null) await fetchCameraSettings(selectedCameraId);
            }
        } catch (err) {
            console.error(`Error updating settings for camera ${selectedCameraId}:`, err);
            if (err.message !== 'Unauthorized') {
                showAppMessage("Error updating settings. Check console for details.", 'error', 5000);
                if (selectedCameraId !== null) await fetchCameraSettings(selectedCameraId);
            }
        }
        updateControlsUI(currentCameraSettings);
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
        showAppMessage("Cannot start video stream: User not authenticated.", "error");
        feedImage.src = "";
        feedImage.alt = "Please login to view feed.";
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
        showAppMessage(`Stream connection error for camera ${cameraId}.`, 'error', 5000);
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
                showAppMessage(`Stream for camera ${cameraId} disconnected unexpectedly.`, 'warning', 5000);
            } else {
                feedImage.alt = `Stream for camera ${cameraId} closed.`;
                showAppMessage(`Stream for camera ${cameraId} closed.`, 'info', 2000);
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

  // Old toggleNightVision and toggleAutofocus functions removed as their buttons are gone
  // and functionality is replaced by the new settings panel and save button.

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
                    selectCamera(null);
                    if (cameraListContainer) cameraListContainer.innerHTML = "<li>No cameras available.</li>";
                    showAppMessage("No cameras available to display.", "info", 0);
                }
            }
        } else {
            console.error("Failed to load cameras:", response.status, await response.text());
            showAppMessage(`Failed to load camera list. Status: ${response.status}`, 'error');
            camerasCache = [];
            selectCamera(null);
        }
    } catch (err) {
        console.error("Error in loadCameras:", err);
        if (err.message !== 'Unauthorized') {
            showAppMessage("Error loading camera list. Check console.", "error");
        }
    }
  }

  // Comment out or adapt old event listeners
  // if (refreshBtn) refreshBtn.addEventListener("click", loadFeed); // Old loadFeed is not suitable
  if (refreshBtn) {
      refreshBtn.style.display = 'block';
      refreshBtn.addEventListener('click', () => {
          if (selectedCameraId !== null) {
              console.log(`Refresh button clicked for camera ID: ${selectedCameraId}`);
              loadFeed(selectedCameraId);
          } else {
              console.log("Refresh button clicked, but no camera selected.");
              loadFeed(null);
          }
      });
  }

  // Event Listeners for new settings controls (checkboxes)
  // Event Listeners for new settings controls (checkboxes) - now only update local state if needed
  // Or simply rely on handleSaveAllSettings to read current values.
  // For simplicity, we'll let handleSaveAllSettings read directly from elements.
  // If immediate reflection in currentCameraSettings object is needed before save, add listeners like:
  // if (settingNightVision) {
  //     settingNightVision.addEventListener('change', (e) => {
  //         if (currentCameraSettings) currentCameraSettings.night_vision = e.target.checked;
  //     });
  // }
  // (This is optional for now, as handleSaveAllSettings reads from DOM elements directly)

  async function handleSaveAllSettings() {
    if (!saveCameraSettingsButton || saveCameraSettingsButton.disabled || selectedCameraId === null) {
        showAppMessage("Please select a camera.", "error");
        return;
    }

    const settingsToUpdate = {};

    if (settingResolution) settingsToUpdate.resolution = settingResolution.value;
    if (settingBrightness) settingsToUpdate.brightness = parseInt(settingBrightness.value, 10);
    if (settingContrast) settingsToUpdate.contrast = parseInt(settingContrast.value, 10);
    if (settingSaturation) settingsToUpdate.saturation = parseInt(settingSaturation.value, 10);
    if (settingSharpness) settingsToUpdate.sharpness = parseInt(settingSharpness.value, 10);

    if (settingNightVision) settingsToUpdate.night_vision = settingNightVision.checked;
    if (settingAutofocus) settingsToUpdate.autofocus = settingAutofocus.checked;
    if (settingMicrophoneEnabled) settingsToUpdate.microphone_enabled = settingMicrophoneEnabled.checked;
    if (settingObjectDetectionEnabled) settingsToUpdate.object_detection_enabled = settingObjectDetectionEnabled.checked;

    if (settingMotionDetectionEnabled) settingsToUpdate.motion_detection_enabled = settingMotionDetectionEnabled.checked;
    if (settingMotionSensitivity) settingsToUpdate.motion_sensitivity = parseInt(settingMotionSensitivity.value, 10);
    if (settingMotionMinArea) settingsToUpdate.motion_min_area = parseInt(settingMotionMinArea.value, 10);
    if (settingRecordOnMotion) settingsToUpdate.record_on_motion = settingRecordOnMotion.checked;

    if (Object.keys(settingsToUpdate).length > 0) {
        await updateCameraSettingsBatch(settingsToUpdate);
    } else {
        showAppMessage("No settings configured to save.", "info");
    }
  }

  if (saveCameraSettingsButton) {
    saveCameraSettingsButton.addEventListener('click', handleSaveAllSettings);
  }

  function setupRangeInputWithValueDisplay(rangeInput, valueLabel) {
    if (rangeInput && valueLabel) {
        valueLabel.textContent = rangeInput.value;
        rangeInput.addEventListener('input', () => {
            valueLabel.textContent = rangeInput.value;
        });
    }
  }

  setupRangeInputWithValueDisplay(settingBrightness, brightnessValueLabel);
  setupRangeInputWithValueDisplay(settingContrast, contrastValueLabel);
  setupRangeInputWithValueDisplay(settingSaturation, saturationValueLabel);
  setupRangeInputWithValueDisplay(settingSharpness, sharpnessValueLabel);
  setupRangeInputWithValueDisplay(settingMotionSensitivity, motionSensitivityValueLabel);

  // Initial UI state update based on stored token
  updateUIForAuthState();
});