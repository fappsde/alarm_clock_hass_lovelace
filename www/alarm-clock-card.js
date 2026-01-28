/**
 * Alarm Clock Card for Home Assistant
 * A feature-rich Lovelace card for managing alarms
 */

const LitElement = Object.getPrototypeOf(
  customElements.get("ha-panel-lovelace")
);
const html = LitElement.prototype.html;
const css = LitElement.prototype.css;

// Card version
const CARD_VERSION = "1.0.0";

// Log card info
console.info(
  `%c ALARM-CLOCK-CARD %c ${CARD_VERSION} `,
  "color: white; background: #3498db; font-weight: bold;",
  "color: #3498db; background: white; font-weight: bold;"
);

// Register card
window.customCards = window.customCards || [];
window.customCards.push({
  type: "alarm-clock-card",
  name: "Alarm Clock Card",
  description: "A card to manage your alarm clocks",
  preview: true,
});

class AlarmClockCard extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      config: { type: Object },
      _expanded: { type: Boolean },
      _editMode: { type: Boolean },
      _editingAlarm: { type: Object },
    };
  }

  constructor() {
    super();
    this._expanded = false;
    this._editMode = false;
    this._editingAlarm = null;
  }

  static getConfigElement() {
    return document.createElement("alarm-clock-card-editor");
  }

  static getStubConfig(hass) {
    // Try to find an alarm clock entity automatically
    let defaultEntity = "";
    if (hass && hass.states) {
      const alarmEntity = Object.keys(hass.states).find(
        (entityId) =>
          entityId.startsWith("switch.alarm_clock") ||
          (entityId.startsWith("switch.alarm_") &&
            hass.states[entityId].attributes?.alarm_id)
      );
      if (alarmEntity) {
        defaultEntity = alarmEntity;
      }
    }

    return {
      entity: defaultEntity,
      title: "Alarm Clock",
      show_next_alarm: true,
      compact_mode: false,
    };
  }

  setConfig(config) {
    // Don't throw error for missing entity during editing
    // Just store the config and show a helpful message in render
    this.config = {
      title: "Alarm Clock",
      show_next_alarm: true,
      compact_mode: false,
      ...config,
    };
  }

  getCardSize() {
    return this.config.compact_mode ? 2 : 4;
  }

  static get styles() {
    return css`
      :host {
        --alarm-primary-color: var(--primary-color, #03a9f4);
        --alarm-active-color: var(--error-color, #db4437);
        --alarm-snoozed-color: var(--warning-color, #ffa726);
        --alarm-card-background: var(
          --ha-card-background,
          var(--card-background-color, white)
        );
        --alarm-text-primary: var(--primary-text-color, #212121);
        --alarm-text-secondary: var(--secondary-text-color, #727272);
      }

      ha-card {
        padding: 16px;
        overflow: hidden;
      }

      .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
      }

      .title {
        font-size: 1.2em;
        font-weight: 500;
        color: var(--alarm-text-primary);
      }

      .next-alarm {
        font-size: 0.9em;
        color: var(--alarm-text-secondary);
      }

      .next-alarm-time {
        font-weight: 500;
        color: var(--alarm-primary-color);
      }

      .alarms-container {
        display: flex;
        flex-direction: column;
        gap: 12px;
      }

      .alarm-card {
        background: var(--alarm-card-background);
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 12px;
        padding: 12px 16px;
        transition: all 0.3s ease;
      }

      .alarm-card.ringing {
        border-color: var(--alarm-active-color);
        animation: pulse 1s infinite;
      }

      .alarm-card.snoozed {
        border-color: var(--alarm-snoozed-color);
      }

      @keyframes pulse {
        0%,
        100% {
          box-shadow: 0 0 0 0 rgba(219, 68, 55, 0.4);
        }
        50% {
          box-shadow: 0 0 0 10px rgba(219, 68, 55, 0);
        }
      }

      .alarm-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .alarm-time {
        font-size: 2em;
        font-weight: 300;
        color: var(--alarm-text-primary);
        cursor: pointer;
        user-select: none;
      }

      .alarm-time:hover {
        color: var(--alarm-primary-color);
      }

      .alarm-name {
        font-size: 0.9em;
        color: var(--alarm-text-secondary);
        margin-top: 4px;
      }

      .alarm-toggle {
        --mdc-theme-secondary: var(--alarm-primary-color);
      }

      .days-container {
        display: flex;
        gap: 4px;
        margin-top: 12px;
        flex-wrap: wrap;
      }

      .day-pill {
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        user-select: none;
        min-width: 32px;
        text-align: center;
      }

      .day-pill.active {
        background: var(--alarm-primary-color);
        color: white;
      }

      .day-pill.inactive {
        background: var(--disabled-color, #bdbdbd);
        color: var(--alarm-text-secondary);
        opacity: 0.5;
      }

      .day-pill:hover {
        transform: scale(1.1);
      }

      .alarm-actions {
        display: flex;
        gap: 8px;
        margin-top: 12px;
      }

      .action-button {
        flex: 1;
        padding: 12px;
        border: none;
        border-radius: 8px;
        font-size: 0.9em;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
      }

      .action-button.snooze {
        background: var(--alarm-snoozed-color);
        color: white;
      }

      .action-button.dismiss {
        background: var(--alarm-active-color);
        color: white;
      }

      .action-button.skip {
        background: var(--disabled-color, #bdbdbd);
        color: var(--alarm-text-primary);
      }

      .action-button:hover {
        transform: scale(1.02);
        filter: brightness(1.1);
      }

      .action-button:active {
        transform: scale(0.98);
      }

      .ringing-actions {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-top: 16px;
      }

      .ringing-actions .action-button {
        padding: 16px;
        font-size: 1.1em;
      }

      .snooze-info {
        font-size: 0.8em;
        color: var(--alarm-text-secondary);
        text-align: center;
        margin-top: 4px;
      }

      .time-adjuster {
        display: flex;
        gap: 8px;
        margin-top: 8px;
      }

      .time-adjust-btn {
        padding: 4px 8px;
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 4px;
        background: transparent;
        color: var(--alarm-text-primary);
        cursor: pointer;
        font-size: 0.75em;
        transition: all 0.2s ease;
      }

      .time-adjust-btn:hover {
        background: var(--alarm-primary-color);
        color: white;
        border-color: var(--alarm-primary-color);
      }

      .status-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 0.7em;
        font-weight: 500;
        text-transform: uppercase;
        margin-left: 8px;
      }

      .status-badge.ringing {
        background: var(--alarm-active-color);
        color: white;
      }

      .status-badge.snoozed {
        background: var(--alarm-snoozed-color);
        color: white;
      }

      .status-badge.pre-alarm {
        background: var(--alarm-primary-color);
        color: white;
      }

      .status-badge.skip {
        background: var(--disabled-color, #bdbdbd);
        color: var(--alarm-text-primary);
      }

      .countdown {
        font-size: 0.8em;
        color: var(--alarm-text-secondary);
        margin-top: 4px;
      }

      .expand-toggle {
        display: flex;
        justify-content: center;
        margin-top: 12px;
      }

      .expand-toggle button {
        background: transparent;
        border: none;
        color: var(--alarm-text-secondary);
        cursor: pointer;
        padding: 4px 12px;
        font-size: 0.85em;
        display: flex;
        align-items: center;
        gap: 4px;
      }

      .expand-toggle button:hover {
        color: var(--alarm-primary-color);
      }

      .no-alarms {
        text-align: center;
        padding: 24px;
        color: var(--alarm-text-secondary);
      }

      .add-alarm-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        width: 100%;
        padding: 12px;
        border: 2px dashed var(--divider-color, #e0e0e0);
        border-radius: 12px;
        background: transparent;
        color: var(--alarm-text-secondary);
        cursor: pointer;
        font-size: 0.9em;
        transition: all 0.2s ease;
        margin-top: 12px;
      }

      .add-alarm-btn:hover {
        border-color: var(--alarm-primary-color);
        color: var(--alarm-primary-color);
      }

      /* Compact mode styles */
      .compact .alarm-card {
        padding: 8px 12px;
      }

      .compact .alarm-time {
        font-size: 1.5em;
      }

      .compact .days-container {
        margin-top: 8px;
      }

      .compact .day-pill {
        padding: 2px 6px;
        font-size: 0.65em;
      }

      /* Mobile friendly touch targets */
      @media (max-width: 600px) {
        .action-button {
          padding: 16px;
          min-height: 48px;
        }

        .day-pill {
          padding: 8px 12px;
          min-height: 36px;
        }

        .alarm-time {
          font-size: 2.5em;
        }
      }
    `;
  }

  render() {
    if (!this.hass || !this.config) {
      return html``;
    }

    // Show helpful message if no entity is configured
    if (!this.config.entity) {
      return html`
        <ha-card>
          <div class="no-alarms">
            <ha-icon icon="mdi:alarm-plus" style="font-size: 48px; opacity: 0.5; margin-bottom: 16px;"></ha-icon>
            <div>No entity configured</div>
            <div style="font-size: 0.9em; margin-top: 8px;">
              Edit this card to select an alarm clock entity
            </div>
          </div>
        </ha-card>
      `;
    }

    const entity = this.hass.states[this.config.entity];
    if (!entity) {
      return html`
        <ha-card>
          <div class="no-alarms">
            <ha-icon icon="mdi:alert-circle-outline" style="font-size: 32px; opacity: 0.5; margin-bottom: 8px;"></ha-icon>
            <div>Entity not found: ${this.config.entity}</div>
            <div style="font-size: 0.9em; margin-top: 8px;">
              Please check if the entity exists or select a different one
            </div>
          </div>
        </ha-card>
      `;
    }

    // Get all alarm entities
    const alarms = this._getAlarms();

    // Get next alarm info
    const nextAlarmEntity = this._getNextAlarmEntity();

    const isCompact = this.config.compact_mode;

    return html`
      <ha-card class="${isCompact ? "compact" : ""}">
        <div class="header">
          <div class="title">${this.config.title}</div>
          ${this.config.show_next_alarm && nextAlarmEntity
            ? html`
                <div class="next-alarm">
                  Next:
                  <span class="next-alarm-time">
                    ${this._formatNextAlarm(nextAlarmEntity)}
                  </span>
                </div>
              `
            : ""}
        </div>

        <div class="alarms-container">
          ${alarms.length > 0
            ? alarms.map((alarm) => this._renderAlarm(alarm))
            : html` <div class="no-alarms">No alarms configured</div> `}
        </div>

        ${!isCompact
          ? html`
              <button
                class="add-alarm-btn"
                @click="${() => this._openAlarmSettings()}"
              >
                <ha-icon icon="mdi:plus"></ha-icon>
                Add Alarm
              </button>
            `
          : ""}
      </ha-card>
    `;
  }

  _getAlarms() {
    const alarms = [];

    // Find all switch entities that have alarm_id attribute (alarm enable switches)
    // These are the main alarm entities created by the integration
    Object.keys(this.hass.states).forEach((key) => {
      if (key.startsWith("switch.")) {
        const state = this.hass.states[key];
        // Check if this is an alarm entity by looking for alarm_id attribute
        // Also exclude skip_next switches
        if (
          state.attributes.alarm_id !== undefined &&
          !key.endsWith("_skip_next")
        ) {
          alarms.push({
            entity_id: key,
            state: state,
            attributes: state.attributes,
          });
        }
      }
    });

    // Sort by time
    alarms.sort((a, b) => {
      const timeA = a.attributes.alarm_time || "00:00";
      const timeB = b.attributes.alarm_time || "00:00";
      return timeA.localeCompare(timeB);
    });

    return alarms;
  }

  _getNextAlarmEntity() {
    const entityId = this.config.entity.replace("switch.", "sensor.").replace(/_enable$/, "") + "_next_alarm";

    // Try to find next_alarm sensor
    const nextAlarmSensor = Object.keys(this.hass.states).find(
      (key) =>
        key.includes("next_alarm") && key.startsWith("sensor.alarm_clock")
    );

    return nextAlarmSensor ? this.hass.states[nextAlarmSensor] : null;
  }

  _formatNextAlarm(entity) {
    if (!entity || !entity.state || entity.state === "unknown") {
      return "None";
    }

    const nextTime = new Date(entity.state);
    if (isNaN(nextTime.getTime())) {
      return "None";
    }

    const now = new Date();
    const diff = nextTime - now;

    if (diff < 0) {
      return "None";
    }

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    const timeStr = nextTime.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    if (hours > 24) {
      const days = Math.floor(hours / 24);
      return `${timeStr} (in ${days}d)`;
    } else if (hours > 0) {
      return `${timeStr} (in ${hours}h ${minutes}m)`;
    } else {
      return `${timeStr} (in ${minutes}m)`;
    }
  }

  _renderAlarm(alarm) {
    const attrs = alarm.attributes;
    const state = attrs.alarm_state || "armed";
    const isRinging = state === "ringing";
    const isSnoozed = state === "snoozed";
    const isPreAlarm = state === "pre_alarm";
    const isEnabled = alarm.state.state === "on";
    const skipNext = attrs.skip_next || false;

    const days = attrs.days || [];
    const dayLabels = ["M", "T", "W", "T", "F", "S", "S"];
    const dayNames = [
      "monday",
      "tuesday",
      "wednesday",
      "thursday",
      "friday",
      "saturday",
      "sunday",
    ];

    return html`
      <div
        class="alarm-card ${isRinging ? "ringing" : ""} ${isSnoozed
          ? "snoozed"
          : ""}"
      >
        <div class="alarm-header">
          <div>
            <div class="alarm-time" @click="${() => this._showTimePicker(alarm)}">
              ${attrs.alarm_time || "00:00"}
              ${isRinging
                ? html`<span class="status-badge ringing">Ringing</span>`
                : ""}
              ${isSnoozed
                ? html`<span class="status-badge snoozed">Snoozed</span>`
                : ""}
              ${isPreAlarm
                ? html`<span class="status-badge pre-alarm">Pre-alarm</span>`
                : ""}
              ${skipNext && !isRinging && !isSnoozed
                ? html`<span class="status-badge skip">Skip</span>`
                : ""}
            </div>
            <div class="alarm-name">${attrs.alarm_name || "Alarm"}</div>
            ${attrs.next_trigger
              ? html`
                  <div class="countdown">
                    ${this._formatCountdown(attrs.next_trigger)}
                  </div>
                `
              : ""}
          </div>
          <ha-switch
            class="alarm-toggle"
            .checked="${isEnabled}"
            @change="${(e) => this._toggleAlarm(alarm, e.target.checked)}"
          ></ha-switch>
        </div>

        ${!this.config.compact_mode
          ? html`
              <div class="time-adjuster">
                <button
                  class="time-adjust-btn"
                  @click="${() => this._adjustTime(alarm, -5)}"
                >
                  -5m
                </button>
                <button
                  class="time-adjust-btn"
                  @click="${() => this._adjustTime(alarm, 5)}"
                >
                  +5m
                </button>
                <button
                  class="time-adjust-btn"
                  @click="${() => this._adjustTime(alarm, 10)}"
                >
                  +10m
                </button>
                <button
                  class="time-adjust-btn"
                  @click="${() => this._adjustTime(alarm, 60)}"
                >
                  +1h
                </button>
              </div>
            `
          : ""}

        <div class="days-container">
          ${dayNames.map(
            (day, index) => html`
              <div
                class="day-pill ${days.includes(day) ? "active" : "inactive"}"
                @click="${() => this._toggleDay(alarm, day, days)}"
              >
                ${dayLabels[index]}
              </div>
            `
          )}
        </div>

        ${isRinging || isSnoozed
          ? html`
              <div class="ringing-actions">
                ${isSnoozed
                  ? html`
                      <div class="snooze-info">
                        Snooze ${attrs.snooze_count}/${attrs.max_snooze_count}
                        ${attrs.snooze_end_time
                          ? ` - ${this._formatSnoozeEnd(attrs.snooze_end_time)}`
                          : ""}
                      </div>
                    `
                  : ""}
                ${attrs.snooze_count < attrs.max_snooze_count
                  ? html`
                      <button
                        class="action-button snooze"
                        @click="${() => this._snoozeAlarm(alarm)}"
                      >
                        <ha-icon icon="mdi:alarm-snooze"></ha-icon>
                        Snooze
                      </button>
                    `
                  : ""}
                <button
                  class="action-button dismiss"
                  @click="${() => this._dismissAlarm(alarm)}"
                >
                  <ha-icon icon="mdi:alarm-off"></ha-icon>
                  Dismiss
                </button>
              </div>
            `
          : html`
              <div class="alarm-actions">
                <button
                  class="action-button skip"
                  @click="${() => this._toggleSkip(alarm, !skipNext)}"
                >
                  <ha-icon
                    icon="${skipNext ? "mdi:skip-next-circle" : "mdi:skip-next"}"
                  ></ha-icon>
                  ${skipNext ? "Unskip" : "Skip Next"}
                </button>
              </div>
            `}
      </div>
    `;
  }

  _formatCountdown(nextTrigger) {
    if (!nextTrigger) return "";

    const next = new Date(nextTrigger);
    const now = new Date();
    const diff = next - now;

    if (diff < 0) return "Passed";

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) {
      return `in ${hours}h ${minutes}m`;
    }
    return `in ${minutes}m`;
  }

  _formatSnoozeEnd(snoozeEnd) {
    if (!snoozeEnd) return "";

    const end = new Date(snoozeEnd);
    return end.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  _toggleAlarm(alarm, enabled) {
    this.hass.callService("homeassistant", enabled ? "turn_on" : "turn_off", {
      entity_id: alarm.entity_id,
    });

    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate(50);
    }
  }

  _toggleDay(alarm, day, currentDays) {
    const newDays = currentDays.includes(day)
      ? currentDays.filter((d) => d !== day)
      : [...currentDays, day];

    if (newDays.length === 0) {
      // Don't allow removing all days
      return;
    }

    this.hass.callService("alarm_clock", "set_days", {
      entity_id: alarm.entity_id,
      days: newDays,
    });

    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate(30);
    }
  }

  _adjustTime(alarm, minutes) {
    const currentTime = alarm.attributes.alarm_time || "07:00";
    const [hours, mins] = currentTime.split(":").map(Number);

    let totalMinutes = hours * 60 + mins + minutes;
    if (totalMinutes < 0) totalMinutes += 24 * 60;
    if (totalMinutes >= 24 * 60) totalMinutes -= 24 * 60;

    const newHours = Math.floor(totalMinutes / 60);
    const newMins = totalMinutes % 60;
    const newTime = `${String(newHours).padStart(2, "0")}:${String(
      newMins
    ).padStart(2, "0")}`;

    this.hass.callService("alarm_clock", "set_time", {
      entity_id: alarm.entity_id,
      alarm_time: newTime,
    });

    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate(30);
    }
  }

  _showTimePicker(alarm) {
    // For now, just cycle through common times
    // A proper implementation would show a time picker dialog
    const commonTimes = [
      "06:00",
      "06:30",
      "07:00",
      "07:30",
      "08:00",
      "08:30",
      "09:00",
    ];
    const currentTime = alarm.attributes.alarm_time || "07:00";
    const currentIndex = commonTimes.indexOf(currentTime);
    const nextIndex = (currentIndex + 1) % commonTimes.length;

    this.hass.callService("alarm_clock", "set_time", {
      entity_id: alarm.entity_id,
      alarm_time: commonTimes[nextIndex],
    });
  }

  _snoozeAlarm(alarm) {
    this.hass.callService("alarm_clock", "snooze", {
      entity_id: alarm.entity_id,
    });

    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate([50, 50, 50]);
    }
  }

  _dismissAlarm(alarm) {
    this.hass.callService("alarm_clock", "dismiss", {
      entity_id: alarm.entity_id,
    });

    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate(100);
    }
  }

  _toggleSkip(alarm, skip) {
    const service = skip ? "skip_next" : "cancel_skip";
    this.hass.callService("alarm_clock", service, {
      entity_id: alarm.entity_id,
    });

    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate(30);
    }
  }

  _openAlarmSettings() {
    // Navigate to config flow to add alarm
    // This would typically open the options flow
    const event = new CustomEvent("hass-more-info", {
      bubbles: true,
      composed: true,
      detail: { entityId: this.config.entity },
    });
    this.dispatchEvent(event);
  }
}

// Card Editor
class AlarmClockCardEditor extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      _config: { type: Object },
      _entities: { type: Array },
    };
  }

  constructor() {
    super();
    this._config = {};
    this._entities = [];
  }

  setConfig(config) {
    this._config = { ...config };
  }

  get _entity() {
    return this._config.entity || "";
  }

  get _title() {
    return this._config.title || "Alarm Clock";
  }

  get _show_next_alarm() {
    return this._config.show_next_alarm !== false;
  }

  get _compact_mode() {
    return this._config.compact_mode === true;
  }

  static get styles() {
    return css`
      .form-row {
        margin-bottom: 16px;
      }

      .form-row label {
        display: block;
        margin-bottom: 4px;
        font-weight: 500;
        color: var(--primary-text-color);
      }

      ha-entity-picker {
        display: block;
        width: 100%;
      }

      ha-textfield,
      ha-text-field {
        display: block;
        width: 100%;
      }

      ha-formfield {
        display: block;
        margin-bottom: 8px;
        padding: 8px 0;
      }

      .description {
        font-size: 0.85em;
        color: var(--secondary-text-color);
        margin-top: 4px;
      }
    `;
  }

  render() {
    if (!this.hass) {
      return html``;
    }

    // Get alarm clock entities - switches with alarm_id attribute
    const alarmEntities = Object.keys(this.hass.states)
      .filter((entityId) => {
        if (!entityId.startsWith("switch.")) return false;
        const state = this.hass.states[entityId];
        // Include entities with alarm_id attribute (excluding skip_next switches)
        return (
          state.attributes.alarm_id !== undefined &&
          !entityId.endsWith("_skip_next")
        );
      })
      .sort();

    // If no alarm entities found, show all switches as fallback
    const hasAlarmEntities = alarmEntities.length > 0;

    return html`
      <div class="form-row">
        ${hasAlarmEntities
          ? html`
              <ha-select
                label="Alarm Entity (Required)"
                .value=${this._entity}
                .configValue=${"entity"}
                @selected=${this._valueChangedSelect}
                @closed=${(e) => e.stopPropagation()}
                fixedMenuPosition
                naturalMenuWidth
              >
                <mwc-list-item value="">-- Select an alarm --</mwc-list-item>
                ${alarmEntities.map((entityId) => {
                  const state = this.hass.states[entityId];
                  const name = state.attributes.friendly_name || entityId;
                  return html`
                    <mwc-list-item .value=${entityId}>
                      ${name}
                    </mwc-list-item>
                  `;
                })}
              </ha-select>
              <div class="description">
                Select an alarm clock entity created by the integration
              </div>
            `
          : html`
              <ha-entity-picker
                label="Entity (Required)"
                .hass=${this.hass}
                .value=${this._entity}
                .configValue=${"entity"}
                .includeDomains=${["switch"]}
                @value-changed=${this._valueChanged}
                allow-custom-entity
              ></ha-entity-picker>
              <div class="description">
                No alarm entities found. Please add alarms via the integration settings first,
                or select any switch entity.
              </div>
            `}
      </div>

      <div class="form-row">
        <ha-textfield
          label="Card Title"
          .value=${this._title}
          .configValue=${"title"}
          @input=${this._valueChangedText}
        ></ha-textfield>
      </div>

      <ha-formfield label="Show Next Alarm">
        <ha-switch
          .checked=${this._show_next_alarm}
          .configValue=${"show_next_alarm"}
          @change=${this._valueChangedBool}
        ></ha-switch>
      </ha-formfield>

      <ha-formfield label="Compact Mode">
        <ha-switch
          .checked=${this._compact_mode}
          .configValue=${"compact_mode"}
          @change=${this._valueChangedBool}
        ></ha-switch>
      </ha-formfield>
    `;
  }

  _valueChanged(ev) {
    if (!this._config || !this.hass) {
      return;
    }
    const target = ev.target;
    const value = ev.detail?.value ?? target.value;
    const configValue = target.configValue;

    if (configValue && this._config[configValue] !== value) {
      this._config = {
        ...this._config,
        [configValue]: value,
      };
      this._fireConfigChanged();
    }
  }

  _valueChangedSelect(ev) {
    if (!this._config || !this.hass) {
      return;
    }
    const target = ev.target;
    const value = target.value;
    const configValue = target.configValue;

    if (configValue && this._config[configValue] !== value) {
      this._config = {
        ...this._config,
        [configValue]: value,
      };
      this._fireConfigChanged();
    }
  }

  _valueChangedText(ev) {
    if (!this._config || !this.hass) {
      return;
    }
    const target = ev.target;
    const value = target.value;
    const configValue = target.configValue;

    if (configValue && this._config[configValue] !== value) {
      this._config = {
        ...this._config,
        [configValue]: value,
      };
      this._fireConfigChanged();
    }
  }

  _valueChangedBool(ev) {
    if (!this._config || !this.hass) {
      return;
    }
    const target = ev.target;
    const value = target.checked;
    const configValue = target.configValue;

    if (configValue && this._config[configValue] !== value) {
      this._config = {
        ...this._config,
        [configValue]: value,
      };
      this._fireConfigChanged();
    }
  }

  _fireConfigChanged() {
    const event = new CustomEvent("config-changed", {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}

customElements.define("alarm-clock-card", AlarmClockCard);
customElements.define("alarm-clock-card-editor", AlarmClockCardEditor);
