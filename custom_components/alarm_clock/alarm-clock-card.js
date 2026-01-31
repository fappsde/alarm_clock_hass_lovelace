/**
 * Alarm Clock Card for Home Assistant
 * A feature-rich Lovelace card for managing alarms
 *
 * SAFETY: Uses official ES module imports - no HA internals access
 * VERSION: Automatically synced from manifest.json
 */

import { LitElement, html, css } from "lit";

// Card version - will be replaced by build script with manifest.json version
const CARD_VERSION = "1.0.8";

// Log card info (only once)
if (!window._alarmClockCardLogged) {
  console.info(
    `%c ALARM-CLOCK-CARD %c ${CARD_VERSION} `,
    "color: white; background: #3498db; font-weight: bold;",
    "color: #3498db; background: white; font-weight: bold;"
  );
  window._alarmClockCardLogged = true;
}

// Register card in customCards list (with duplicate protection)
window.customCards = window.customCards || [];
if (!window.customCards.some(card => card.type === "alarm-clock-card")) {
  window.customCards.push({
    type: "alarm-clock-card",
    name: "Alarm Clock Card",
    description: "A card to manage your alarm clocks",
    preview: true,
    version: CARD_VERSION,
  });
}

class AlarmClockCard extends LitElement {
  static get properties() {
    return {
      hass: { type: Object },
      config: { type: Object },
      _expanded: { type: Boolean },
      _editMode: { type: Boolean },
      _editingAlarm: { type: Object },
      _viewMode: { type: String },
      _selectedAlarmId: { type: String },
      _showTimePicker: { type: Boolean },
    };
  }

  constructor() {
    super();
    this._expanded = false;
    this._editMode = false;
    this._editingAlarm = null;
    this._viewMode = "list"; // "list" or "editor"
    this._selectedAlarmId = null;
    this._showTimePicker = false;
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
      view_mode: "list",
    };
  }

  setConfig(config) {
    // Don't throw error for missing entity during editing
    // Just store the config and show a helpful message in render
    this.config = {
      title: "Alarm Clock",
      show_next_alarm: true,
      compact_mode: false,
      view_mode: "list",
      ...config,
    };
    // Set view mode from config
    this._viewMode = this.config.view_mode || "list";
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
        align-items: flex-start;
      }

      .alarm-header-right {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 12px;
      }

      .alarm-icon-buttons {
        display: flex;
        gap: 8px;
        align-items: center;
      }

      .icon-button {
        background: transparent;
        border: none;
        color: var(--alarm-text-secondary);
        cursor: pointer;
        padding: 4px;
        border-radius: 50%;
        transition: all 0.2s ease;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
      }

      .icon-button:hover {
        background: var(--divider-color, #e0e0e0);
        color: var(--alarm-text-primary);
      }

      .icon-button.delete:hover {
        background: var(--alarm-active-color);
        color: white;
      }

      .icon-button.skip-active {
        color: var(--alarm-primary-color);
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
        flex-wrap: nowrap;
        justify-content: space-between;
      }

      .day-pill {
        flex: 1 1 0;
        padding: 6px 2px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        user-select: none;
        min-width: 0;
        text-align: center;
        display: flex;
        align-items: center;
        justify-content: center;
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
        flex: 0 0 auto;
        padding: 8px 12px;
        font-size: 0.85em;
      }

      .action-button.delete {
        background: var(--alarm-active-color);
        color: white;
        flex: 0 0 auto;
        padding: 8px 12px;
        font-size: 0.85em;
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

      /* View mode toggle */
      .mode-toggle {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .mode-toggle-button {
        background: transparent;
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 8px;
        padding: 4px 8px;
        cursor: pointer;
        color: var(--alarm-text-secondary);
        transition: all 0.2s ease;
      }

      .mode-toggle-button:hover {
        background: var(--alarm-primary-color);
        color: white;
        border-color: var(--alarm-primary-color);
      }

      .mode-toggle-button.active {
        background: var(--alarm-primary-color);
        color: white;
        border-color: var(--alarm-primary-color);
      }

      /* Editor mode layout */
      .editor-layout {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }

      .editor-section {
        background: var(--alarm-card-background);
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 12px;
        padding: 16px;
      }

      .editor-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
      }

      .editor-time-container {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .time-picker-button {
        background: var(--alarm-primary-color);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 12px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 4px;
        transition: all 0.2s ease;
      }

      .time-picker-button:hover {
        filter: brightness(1.1);
        transform: scale(1.02);
      }

      /* Horizontal alarm list */
      .alarms-horizontal-container {
        overflow-x: auto;
        overflow-y: hidden;
        display: flex;
        gap: 12px;
        padding: 4px;
        scrollbar-width: thin;
      }

      .alarms-horizontal-container::-webkit-scrollbar {
        height: 6px;
      }

      .alarms-horizontal-container::-webkit-scrollbar-track {
        background: var(--divider-color, #e0e0e0);
        border-radius: 3px;
      }

      .alarms-horizontal-container::-webkit-scrollbar-thumb {
        background: var(--alarm-primary-color);
        border-radius: 3px;
      }

      /* Compact alarm card */
      .alarm-compact {
        min-width: 120px;
        max-width: 120px;
        background: var(--alarm-card-background);
        border: 2px solid var(--divider-color, #e0e0e0);
        border-radius: 12px;
        padding: 12px;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 8px;
      }

      .alarm-compact:hover {
        transform: translateY(-4px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      }

      .alarm-compact.selected {
        border-color: var(--alarm-primary-color);
        box-shadow: 0 0 0 2px var(--alarm-primary-color);
      }

      .alarm-compact.enabled {
        background: linear-gradient(135deg, var(--alarm-primary-color) 0%, transparent 100%);
        border-color: var(--alarm-primary-color);
      }

      .alarm-compact.disabled {
        opacity: 0.6;
      }

      .alarm-compact-time {
        font-size: 1.5em;
        font-weight: 300;
        color: var(--alarm-text-primary);
      }

      .alarm-compact-name {
        font-size: 0.7em;
        color: var(--alarm-text-secondary);
        text-align: center;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        width: 100%;
      }

      .alarm-compact-days {
        display: flex;
        gap: 2px;
        flex-wrap: wrap;
        justify-content: center;
      }

      .alarm-compact-day {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.6em;
        font-weight: 500;
      }

      .alarm-compact-day.active {
        background: var(--alarm-primary-color);
        color: white;
      }

      .alarm-compact-day.inactive {
        background: var(--disabled-color, #bdbdbd);
        color: var(--alarm-text-secondary);
        opacity: 0.4;
      }

      /* Time picker dialog */
      .time-picker-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 999;
      }

      .time-picker-dialog {
        background: var(--alarm-card-background);
        border-radius: 16px;
        padding: 24px;
        min-width: 300px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
      }

      .time-picker-header {
        font-size: 1.2em;
        font-weight: 500;
        margin-bottom: 16px;
        color: var(--alarm-text-primary);
      }

      .time-picker-inputs {
        display: flex;
        gap: 8px;
        align-items: center;
        justify-content: center;
        margin-bottom: 16px;
      }

      .time-picker-input {
        width: 80px;
        height: 60px;
        font-size: 2em;
        text-align: center;
        border: 2px solid var(--divider-color, #e0e0e0);
        border-radius: 8px;
        background: var(--alarm-card-background);
        color: var(--alarm-text-primary);
      }

      .time-picker-input:focus {
        outline: none;
        border-color: var(--alarm-primary-color);
      }

      .time-picker-separator {
        font-size: 2em;
        font-weight: 300;
        color: var(--alarm-text-primary);
      }

      .time-picker-actions {
        display: flex;
        gap: 8px;
        justify-content: flex-end;
      }

      .time-picker-button {
        padding: 8px 16px;
        border: none;
        border-radius: 8px;
        font-size: 0.9em;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
      }

      .time-picker-button.cancel {
        background: transparent;
        color: var(--alarm-text-secondary);
      }

      .time-picker-button.cancel:hover {
        background: var(--divider-color, #e0e0e0);
      }

      .time-picker-button.confirm {
        background: var(--alarm-primary-color);
        color: white;
      }

      .time-picker-button.confirm:hover {
        filter: brightness(1.1);
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
          ${this.config.show_next_alarm
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

        ${this._viewMode === "list"
          ? this._renderListMode(alarms, isCompact)
          : this._renderEditorMode(alarms)}

        ${this._showTimePicker ? this._renderTimePicker() : ""}
      </ha-card>
    `;
  }

  _renderListMode(alarms, isCompact) {
    return html`
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
    `;
  }

  _renderEditorMode(alarms) {
    if (alarms.length === 0) {
      return html`
        <div class="no-alarms">No alarms configured</div>
        <button
          class="add-alarm-btn"
          @click="${() => this._openAlarmSettings()}"
        >
          <ha-icon icon="mdi:plus"></ha-icon>
          Add Alarm
        </button>
      `;
    }

    // Ensure we have a selected alarm
    if (!this._selectedAlarmId && alarms.length > 0) {
      this._selectedAlarmId = alarms[0].attributes.alarm_id;
    }

    const selectedAlarm = alarms.find(
      (a) => a.attributes.alarm_id === this._selectedAlarmId
    );

    return html`
      <div class="editor-layout">
        ${selectedAlarm ? this._renderAlarmEditor(selectedAlarm) : ""}

        <div class="alarms-horizontal-container">
          ${alarms.map((alarm) => this._renderAlarmCompact(alarm))}
          <div
            class="alarm-compact"
            style="border-style: dashed;"
            @click="${() => this._openAlarmSettings()}"
          >
            <ha-icon icon="mdi:plus" style="font-size: 2em; opacity: 0.5;"></ha-icon>
          </div>
        </div>
      </div>
    `;
  }

  _getAlarms() {
    const alarms = [];

    // Get the entry_id of the configured entity to filter by device
    const configEntity = this.hass.states[this.config.entity];
    if (!configEntity) {
      return alarms;
    }

    // Get entry_id from the configured entity
    const configEntryId = configEntity.attributes.entry_id;

    // If no entry_id, we can't filter properly, so return empty
    if (!configEntryId) {
      console.warn("No entry_id found for configured entity:", this.config.entity);
      return alarms;
    }

    // Find all switch entities that have alarm_id attribute (alarm enable switches)
    // and belong to the same alarm clock device (same entry_id)
    Object.keys(this.hass.states).forEach((key) => {
      if (key.startsWith("switch.")) {
        const state = this.hass.states[key];
        // Check if this is an alarm entity by looking for alarm_id attribute
        // Also exclude skip_next switches
        if (
          state.attributes.alarm_id !== undefined &&
          !key.endsWith("_skip_next")
        ) {
          // Filter by device: only include alarms with matching entry_id
          if (state.attributes.entry_id === configEntryId) {
            // Only store necessary data to avoid circular references
            // that cause "Maximum call stack size exceeded" errors
            // Extract only the attributes we actually use to prevent
            // any nested circular references from HA state objects
            const attrs = state.attributes;
            alarms.push({
              entity_id: key,
              state: { state: state.state },
              attributes: {
                alarm_id: attrs.alarm_id,
                alarm_name: attrs.alarm_name,
                alarm_state: attrs.alarm_state,
                alarm_time: attrs.alarm_time,
                days: attrs.days,
                entry_id: attrs.entry_id,
                max_snooze_count: attrs.max_snooze_count,
                next_trigger: attrs.next_trigger,
                skip_next: attrs.skip_next,
                snooze_count: attrs.snooze_count,
                snooze_end_time: attrs.snooze_end_time,
              },
            });
          }
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
    if (!entity || !entity.state || entity.state === "unknown" || entity.state === "unavailable") {
      return "No next alarm";
    }

    const nextTime = new Date(entity.state);
    if (isNaN(nextTime.getTime())) {
      return "No next alarm";
    }

    const now = new Date();
    const diff = nextTime - now;

    if (diff < 0) {
      return "No next alarm";
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
    const isOneTime = days.length === 1; // One-time alarm if only one day selected
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
            <div class="alarm-time" @click="${() => this._openTimePicker(alarm)}">
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
              ${isOneTime && !isRinging && !isSnoozed && !skipNext
                ? html`<span class="status-badge">One-time</span>`
                : ""}
            </div>
            <div class="alarm-name">${attrs.alarm_name || "Alarm"}</div>
            ${attrs.next_trigger
              ? html`
                  <div class="countdown">
                    ${this._formatCountdown(attrs.next_trigger, isOneTime)}
                  </div>
                `
              : ""}
          </div>
          <div class="alarm-header-right">
            <ha-switch
              class="alarm-toggle"
              .checked="${isEnabled}"
              @change="${(e) => this._toggleAlarm(alarm, e.target.checked)}"
            ></ha-switch>
            ${!isRinging && !isSnoozed
              ? html`
                  <div class="alarm-icon-buttons">
                    <button
                      class="icon-button ${skipNext ? 'skip-active' : ''}"
                      title="${skipNext ? 'Cancel skip next occurrence' : 'Skip next occurrence'}"
                      @click="${() => this._toggleSkip(alarm, !skipNext)}"
                    >
                      <ha-icon
                        icon="${skipNext ? 'mdi:skip-next-circle' : 'mdi:skip-next'}"
                      ></ha-icon>
                    </button>
                    <button
                      class="icon-button delete"
                      title="Delete alarm"
                      @click="${() => this._deleteAlarm(alarm)}"
                    >
                      <ha-icon icon="mdi:delete"></ha-icon>
                    </button>
                  </div>
                `
              : ""}
          </div>
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
          : ""}
      </div>
    `;
  }

  _formatCountdown(nextTrigger, isOneTime = false) {
    if (!nextTrigger) return "";

    const next = new Date(nextTrigger);
    const now = new Date();
    const diff = next - now;

    if (diff < 0) return "Passed";

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    // For one-time alarms, include the date
    let countdown = "";
    if (hours > 0) {
      countdown = `in ${hours}h ${minutes}m`;
    } else {
      countdown = `in ${minutes}m`;
    }

    // Add date for one-time alarms or alarms more than 24h away
    if (isOneTime || hours > 24) {
      const dateStr = next.toLocaleDateString([], {
        weekday: 'short',
        month: 'short',
        day: 'numeric'
      });
      return `${countdown} (${dateStr})`;
    }

    return countdown;
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
    console.log("_toggleDay called", { 
      entity_id: alarm.entity_id,
      alarm_name: alarm.attributes.alarm_name,
      day, 
      currentDays 
    });

    const newDays = currentDays.includes(day)
      ? currentDays.filter((d) => d !== day)
      : [...currentDays, day];

    if (newDays.length === 0) {
      // Convert to one-time alarm
      // Calculate which day it should trigger (today if time hasn't passed, tomorrow if it has)
      const now = new Date();
      const [alarmHour, alarmMinute] = (alarm.attributes.alarm_time || "07:00").split(":").map(Number);
      const alarmToday = new Date();
      alarmToday.setHours(alarmHour, alarmMinute, 0, 0);

      // Determine trigger day
      let triggerDate;
      if (alarmToday > now) {
        // Time hasn't passed today, use today
        triggerDate = now;
      } else {
        // Time has passed, use tomorrow
        triggerDate = new Date(now);
        triggerDate.setDate(triggerDate.getDate() + 1);
      }

      const dayNames = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"];
      const triggerDay = dayNames[triggerDate.getDay()];

      console.log("Converting to one-time alarm for", triggerDay);

      this.hass.callService("alarm_clock", "set_days", {
        entity_id: alarm.entity_id,
        days: [triggerDay],
      }).catch(err => {
        console.error("Failed to set days:", err);
        alert("Failed to set alarm days: " + err.message);
      });

      // Haptic feedback
      if (navigator.vibrate) {
        navigator.vibrate(30);
      }
      return;
    }

    console.log("Calling set_days service", {
      entity_id: alarm.entity_id,
      days: newDays,
    });

    this.hass.callService("alarm_clock", "set_days", {
      entity_id: alarm.entity_id,
      days: newDays,
    }).catch(err => {
      console.error("Failed to set days:", err);
      alert("Failed to set alarm days: " + err.message);
    });

    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate(30);
    }
  }

  _adjustTime(alarm, minutes) {
    console.log("_adjustTime called", { 
      entity_id: alarm.entity_id,
      alarm_name: alarm.attributes.alarm_name,
      minutes 
    });

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

    console.log("Calling set_time service", {
      entity_id: alarm.entity_id,
      alarm_time: newTime,
    });

    this.hass.callService("alarm_clock", "set_time", {
      entity_id: alarm.entity_id,
      alarm_time: newTime,
    }).catch(err => {
      console.error("Failed to adjust time:", err);
      alert("Failed to adjust alarm time: " + err.message);
    });

    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate(30);
    }
  }

  _snoozeAlarm(alarm) {
    console.log("_snoozeAlarm called", { 
      entity_id: alarm.entity_id,
      alarm_name: alarm.attributes.alarm_name 
    });

    this.hass.callService("alarm_clock", "snooze", {
      entity_id: alarm.entity_id,
    }).catch(err => {
      console.error("Failed to snooze alarm:", err);
      alert("Failed to snooze alarm: " + err.message);
    });

    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate([50, 50, 50]);
    }
  }

  _dismissAlarm(alarm) {
    console.log("_dismissAlarm called", { 
      entity_id: alarm.entity_id,
      alarm_name: alarm.attributes.alarm_name 
    });

    this.hass.callService("alarm_clock", "dismiss", {
      entity_id: alarm.entity_id,
    }).catch(err => {
      console.error("Failed to dismiss alarm:", err);
      alert("Failed to dismiss alarm: " + err.message);
    });

    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate(100);
    }
  }

  _toggleSkip(alarm, skip) {
    console.log("_toggleSkip called", { 
      entity_id: alarm.entity_id,
      alarm_name: alarm.attributes.alarm_name,
      skip 
    });

    const service = skip ? "skip_next" : "cancel_skip";

    console.log("Calling service", service, { entity_id: alarm.entity_id });

    this.hass.callService("alarm_clock", service, {
      entity_id: alarm.entity_id,
    }).catch(err => {
      console.error("Failed to toggle skip:", err);
      alert("Failed to toggle skip: " + err.message);
    });

    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate(30);
    }
  }

  _deleteAlarm(alarm) {
    console.log("_deleteAlarm called", { 
      entity_id: alarm.entity_id,
      alarm_name: alarm.attributes.alarm_name 
    });

    const alarmName = alarm.attributes.alarm_name || "this alarm";

    if (!confirm(`Are you sure you want to delete ${alarmName}?`)) {
      return;
    }

    this.hass.callService("alarm_clock", "delete_alarm", {
      alarm_id: alarm.attributes.alarm_id,
    }).catch(err => {
      console.error("Failed to delete alarm:", err);
      alert("Failed to delete alarm: " + err.message);
    });

    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate(50);
    }
  }

  _renderAlarmCompact(alarm) {
    const attrs = alarm.attributes;
    const isEnabled = alarm.state.state === "on";
    const isSelected = attrs.alarm_id === this._selectedAlarmId;
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
        class="alarm-compact ${isEnabled ? "enabled" : "disabled"} ${isSelected ? "selected" : ""}"
        @click="${() => this._selectAlarm(attrs.alarm_id)}"
      >
        <div class="alarm-compact-time">${attrs.alarm_time || "00:00"}</div>
        <div class="alarm-compact-name">${attrs.alarm_name || "Alarm"}</div>
        <div class="alarm-compact-days">
          ${dayNames.map(
            (day, index) => html`
              <div class="alarm-compact-day ${days.includes(day) ? "active" : "inactive"}">
                ${dayLabels[index]}
              </div>
            `
          )}
        </div>
      </div>
    `;
  }

  _selectAlarm(alarmId) {
    this._selectedAlarmId = alarmId;
    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate(30);
    }
  }

  _renderAlarmEditor(alarm) {
    const attrs = alarm.attributes;
    const state = attrs.alarm_state || "armed";
    const isRinging = state === "ringing";
    const isSnoozed = state === "snoozed";
    const isPreAlarm = state === "pre_alarm";
    const isEnabled = alarm.state.state === "on";
    const skipNext = attrs.skip_next || false;
    const days = attrs.days || [];
    const isOneTime = days.length === 1; // One-time alarm if only one day selected
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
      <div class="editor-section">
        <div class="editor-header">
          <div>
            <div class="alarm-time" @click="${() => this._openTimePicker(alarm)}">
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
              ${isOneTime && !isRinging && !isSnoozed && !skipNext
                ? html`<span class="status-badge">One-time</span>`
                : ""}
            </div>
          </div>
          <div class="alarm-header-right">
            <ha-switch
              class="alarm-toggle"
              .checked="${isEnabled}"
              @change="${(e) => this._toggleAlarm(alarm, e.target.checked)}"
            ></ha-switch>
            ${!isRinging && !isSnoozed
              ? html`
                  <div class="alarm-icon-buttons">
                    <button
                      class="icon-button ${skipNext ? 'skip-active' : ''}"
                      title="${skipNext ? 'Cancel skip next occurrence' : 'Skip next occurrence'}"
                      @click="${() => this._toggleSkip(alarm, !skipNext)}"
                    >
                      <ha-icon
                        icon="${skipNext ? 'mdi:skip-next-circle' : 'mdi:skip-next'}"
                      ></ha-icon>
                    </button>
                    <button
                      class="icon-button delete"
                      title="Delete alarm"
                      @click="${() => this._deleteAlarm(alarm)}"
                    >
                      <ha-icon icon="mdi:delete"></ha-icon>
                    </button>
                  </div>
                `
              : ""}
          </div>
        </div>

        <div class="alarm-name">${attrs.alarm_name || "Alarm"}</div>
        ${attrs.next_trigger
          ? html`
              <div class="countdown">
                ${this._formatCountdown(attrs.next_trigger, isOneTime)}
              </div>
            `
          : ""}

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
          : ""}
      </div>
    `;
  }

  _openTimePicker(alarm) {
    this._timePickerAlarm = alarm;
    this._showTimePicker = true;
  }

  _renderTimePicker() {
    if (!this._timePickerAlarm) return html``;

    const currentTime = this._timePickerAlarm.attributes.alarm_time || "07:00";
    const [hours, minutes] = currentTime.split(":");

    return html`
      <div class="time-picker-overlay" @click="${(e) => {
        if (e.target === e.currentTarget) this._closeTimePicker();
      }}">
        <div class="time-picker-dialog">
          <div class="time-picker-header">Set Alarm Time</div>
          <div class="time-picker-inputs">
            <input
              type="number"
              class="time-picker-input"
              id="hours-input"
              min="0"
              max="23"
              .value="${hours}"
              @input="${(e) => this._validateTimeInput(e, 23)}"
            />
            <span class="time-picker-separator">:</span>
            <input
              type="number"
              class="time-picker-input"
              id="minutes-input"
              min="0"
              max="59"
              .value="${minutes}"
              @input="${(e) => this._validateTimeInput(e, 59)}"
            />
          </div>
          <div class="time-picker-actions">
            <button
              class="time-picker-button cancel"
              @click="${() => this._closeTimePicker()}"
            >
              Cancel
            </button>
            <button
              class="time-picker-button confirm"
              @click="${() => this._confirmTimePicker()}"
            >
              Set Time
            </button>
          </div>
        </div>
      </div>
    `;
  }

  _validateTimeInput(e, max) {
    let value = parseInt(e.target.value) || 0;
    if (value < 0) value = 0;
    if (value > max) value = max;
    e.target.value = value.toString().padStart(2, "0");
  }

  _closeTimePicker() {
    this._showTimePicker = false;
    this._timePickerAlarm = null;
  }

  _confirmTimePicker() {
    console.log("_confirmTimePicker called", { 
      entity_id: this._timePickerAlarm?.entity_id,
      alarm_name: this._timePickerAlarm?.attributes?.alarm_name
    });

    const hoursInput = this.shadowRoot.getElementById("hours-input");
    const minutesInput = this.shadowRoot.getElementById("minutes-input");

    if (!hoursInput || !minutesInput) {
      console.error("Time picker inputs not found");
      return;
    }

    const hours = hoursInput.value.padStart(2, "0");
    const minutes = minutesInput.value.padStart(2, "0");
    const newTime = `${hours}:${minutes}`;

    console.log("Calling set_time service from time picker", {
      entity_id: this._timePickerAlarm.entity_id,
      alarm_time: newTime,
    });

    this.hass.callService("alarm_clock", "set_time", {
      entity_id: this._timePickerAlarm.entity_id,
      alarm_time: newTime,
    }).catch(err => {
      console.error("Failed to set time from picker:", err);
      alert("Failed to set alarm time: " + err.message);
    });

    // Haptic feedback
    if (navigator.vibrate) {
      navigator.vibrate(50);
    }

    this._closeTimePicker();
  }

  async _openAlarmSettings() {
    console.log("_openAlarmSettings called");

    // Get the entry_id from the configured entity
    const configEntity = this.hass.states[this.config.entity];
    console.log("Config entity:", this.config.entity, configEntity);

    if (!configEntity || !configEntity.attributes.entry_id) {
      console.error("Cannot create alarm: No entry_id found for configured entity");
      alert("Cannot create alarm. Please check the card configuration.");
      return;
    }

    // Create a new alarm with default settings
    // Generate a unique name based on alarm count
    const currentAlarms = this._getAlarms();
    const alarmNumber = currentAlarms.length + 1;
    const alarmName = `Alarm ${alarmNumber}`;

    console.log("Creating alarm:", {
      name: alarmName,
      time: "07:00",
      entry_id: configEntity.attributes.entry_id,
    });

    try {
      await this.hass.callService("alarm_clock", "create_alarm", {
        name: alarmName,
        time: "07:00",
        days: ["monday", "tuesday", "wednesday", "thursday", "friday"],
        enabled: false, // Start disabled so user can configure it first
        entry_id: configEntity.attributes.entry_id,
      });

      // Haptic feedback
      if (navigator.vibrate) {
        navigator.vibrate(50);
      }

      // In editor mode, select the newly created alarm
      if (this._viewMode === "editor") {
        // Wait a bit for the alarm to be created
        setTimeout(() => {
          const alarms = this._getAlarms();
          if (alarms.length > 0) {
            this._selectedAlarmId = alarms[alarms.length - 1].attributes.alarm_id;
          }
        }, 500);
      }
    } catch (error) {
      console.error("Failed to create alarm:", error);
      alert("Failed to create alarm. Please check the logs.");
    }
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

  get _view_mode() {
    return this._config.view_mode || "list";
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

    // Get alarm clock entities - switches with alarm_id attribute OR device-level sensors
    const alarmEntities = Object.keys(this.hass.states)
      .filter((entityId) => {
        const state = this.hass.states[entityId];
        // Include alarm switches (excluding skip_next switches)
        if (entityId.startsWith("switch.") &&
            state.attributes.alarm_id !== undefined &&
            !entityId.endsWith("_skip_next")) {
          return true;
        }
        // Include device-level sensors (next_alarm and active_alarm_count)
        if (entityId.startsWith("sensor.") &&
            state.attributes.entry_id !== undefined &&
            (entityId.includes("next_alarm") || entityId.includes("active_alarm"))) {
          return true;
        }
        return false;
      })
      .sort();

    // Group entities by type for better organization
    const deviceSensors = alarmEntities.filter(e => e.startsWith("sensor."));
    const alarmSwitches = alarmEntities.filter(e => e.startsWith("switch."));

    // If we have device sensors, use those; otherwise use alarm switches
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
                <mwc-list-item value="">-- Select an entity --</mwc-list-item>
                ${deviceSensors.length > 0
                  ? html`
                      <li divider role="separator"></li>
                      <li disabled>Device-level sensors (recommended)</li>
                      ${deviceSensors.map((entityId) => {
                        const state = this.hass.states[entityId];
                        const name = state.attributes.friendly_name || entityId;
                        return html`
                          <mwc-list-item .value=${entityId}>
                            ${name}
                          </mwc-list-item>
                        `;
                      })}
                    `
                  : ""}
                ${alarmSwitches.length > 0
                  ? html`
                      <li divider role="separator"></li>
                      <li disabled>Individual alarms</li>
                      ${alarmSwitches.map((entityId) => {
                        const state = this.hass.states[entityId];
                        const name = state.attributes.friendly_name || entityId;
                        return html`
                          <mwc-list-item .value=${entityId}>
                            ${name}
                          </mwc-list-item>
                        `;
                      })}
                    `
                  : ""}
              </ha-select>
              <div class="description">
                Select a device-level sensor (recommended) or an individual alarm. Device sensors work even before alarms are created.
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

      <div class="form-row">
        <label>View Mode</label>
        <ha-select
          .value=${this._view_mode}
          .configValue=${"view_mode"}
          @selected=${this._valueChangedSelect}
          @closed=${(e) => e.stopPropagation()}
          fixedMenuPosition
          naturalMenuWidth
        >
          <mwc-list-item value="list">List View</mwc-list-item>
          <mwc-list-item value="editor">Editor View</mwc-list-item>
        </ha-select>
        <div class="description">
          List view shows all alarms in a vertical list. Editor view shows one alarm in detail with compact cards below.
        </div>
      </div>
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

// Duplicate registration protection - critical for preventing DOMException
if (!customElements.get("alarm-clock-card")) {
  customElements.define("alarm-clock-card", AlarmClockCard);
}

if (!customElements.get("alarm-clock-card-editor")) {
  customElements.define("alarm-clock-card-editor", AlarmClockCardEditor);
}
