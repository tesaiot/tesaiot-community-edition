import { Node, NodeDef, NodeInitializer } from 'node-red';
import { AxiosInstance } from 'axios';

interface TesaiotDeviceDataConfig extends NodeDef {
  gateway: string;
  limit?: number;
  debugOutput?: boolean | string;
}

type TesaiotDeviceDataNode = Node & {
  getClient: () => AxiosInstance;
};

const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000;
const DEFAULT_WINDOW_DAYS = 14;
const TRUTHY_FLAGS = new Set(['1', 'true', 'yes', 'on']);

const parseEnvDefaultWindow = (): number => {
  const raw = process.env.TESAIOT_DEVICE_DATA_DEFAULT_WINDOW_DAYS;
  if (!raw) {
    return DEFAULT_WINDOW_DAYS;
  }
  const parsed = Number(raw);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return DEFAULT_WINDOW_DAYS;
  }
  return parsed;
};

const DEFAULT_DURATION_MS = parseEnvDefaultWindow() * MILLISECONDS_PER_DAY;
const ENV_DEBUG_FLAG = (() => {
  const raw = process.env.TESAIOT_DEVICE_DATA_DEBUG;
  return typeof raw === 'string' && TRUTHY_FLAGS.has(raw.trim().toLowerCase());
})();

const toBoolean = (value: unknown): boolean => {
  if (typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'string') {
    return TRUTHY_FLAGS.has(value.trim().toLowerCase());
  }
  return false;
};

interface TesaiotApiGatewayNode extends Node {
  getClient: () => AxiosInstance;
}

const clampLimit = (value: number): number => {
  if (!Number.isFinite(value) || value <= 0) {
    return 100;
  }
  return Math.max(1, Math.min(value, 1000));
};

const parseSince = (expr: unknown): number | undefined => {
  if (!expr || typeof expr !== 'string') {
    return undefined;
  }
  const match = expr.trim().toLowerCase().match(/^(\d+)([smhdw])$/);
  if (!match) {
    return undefined;
  }
  const value = Number(match[1]);
  const unit = match[2];
  const unitMap: Record<string, number> = {
    s: 1000,
    m: 60 * 1000,
    h: 60 * 60 * 1000,
    d: 24 * 60 * 60 * 1000,
    w: 7 * 24 * 60 * 60 * 1000,
  };
  return Number.isFinite(value) && value > 0 ? value * unitMap[unit] : undefined;
};

const parseDate = (value: unknown): Date | undefined => {
  if (!value) {
    return undefined;
  }
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    return value;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? undefined : date;
  }
  if (typeof value === 'string') {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? undefined : date;
  }
  return undefined;
};

const toIso = (date: Date | undefined): string | undefined =>
  date ? date.toISOString() : undefined;

const nodeInit: NodeInitializer = (RED): void => {
  function TesaiotDeviceData(this: TesaiotDeviceDataNode, config: TesaiotDeviceDataConfig): void {
    RED.nodes.createNode(this, config);

    const gatewayNode = RED.nodes.getNode(config.gateway) as TesaiotApiGatewayNode | null;

    if (!gatewayNode) {
      this.status({ fill: 'red', shape: 'ring', text: 'missing gateway' });
      this.error('TESAIoT Device Data node requires a TESAIoT API Gateway config node.');
      return;
    }

    this.status({ fill: 'yellow', shape: 'ring', text: 'idle' });

    this.on('input', async (msg: any, send: (value: any) => void, done: (err?: any) => void) => {
      const payload = msg?.tesaiot?.deviceData || {};
      const deviceId = payload.deviceId || msg.deviceId || msg.tesaiot?.deviceId;

      if (!deviceId) {
        const message = 'TESAIoT device data node requires `deviceId` (msg.tesaiot.deviceData.deviceId or msg.deviceId).';
        this.status({ fill: 'red', shape: 'ring', text: 'missing deviceId' });
        this.error(message, msg);
        done(message);
        return;
      }

      const limit = clampLimit(Number(payload.limit ?? msg.limit ?? config.limit ?? 200));

      const sinceMs = parseSince(payload.since ?? msg.since);
      const windowHours = Number(payload.windowHours ?? payload.window_hours ?? msg.windowHours ?? msg.window_hours);
      const windowDays = Number(payload.windowDays ?? payload.window_days ?? msg.windowDays ?? msg.window_days);
      const windowMinutes = Number(payload.windowMinutes ?? payload.window_minutes ?? msg.windowMinutes ?? msg.window_minutes);

      const explicitStart = payload.start_time ?? payload.startTime ?? msg.start_time ?? msg.startTime;
      const explicitEnd = payload.end_time ?? payload.endTime ?? msg.end_time ?? msg.endTime;

      let endDate = parseDate(explicitEnd) ?? new Date();
      let startDate = parseDate(explicitStart);

      if (!startDate) {
        let durationMs: number | undefined = sinceMs;
        if (!durationMs && Number.isFinite(windowMinutes) && windowMinutes > 0) {
          durationMs = windowMinutes * 60 * 1000;
        }
        if (!durationMs && Number.isFinite(windowHours) && windowHours > 0) {
          durationMs = windowHours * 60 * 60 * 1000;
        }
        if (!durationMs && Number.isFinite(windowDays) && windowDays > 0) {
          durationMs = windowDays * 24 * 60 * 60 * 1000;
        }
        if (!durationMs) {
          durationMs = DEFAULT_DURATION_MS;
        }
        startDate = new Date(endDate.getTime() - durationMs);
      }

      if (startDate.getTime() > endDate.getTime()) {
        const tmp = startDate;
        startDate = endDate;
        endDate = tmp;
      }

      try {
        const client = gatewayNode.getClient();
        const params: Record<string, unknown> = {
          limit,
          start_time: toIso(startDate),
          end_time: toIso(endDate)
        };
        const windowInfo = {
          start: params.start_time,
          end: params.end_time,
          limit
        };

        const { data } = await client.get(`/devices/${deviceId}/telemetry`, { params });

        this.status({ fill: 'green', shape: 'dot', text: `telemetry (${limit})` });
        msg.payload = data;
        msg.metadata = {
          ...(msg.metadata || {}),
          source: 'tesaiot-device-data',
          deviceId,
          fetchedAt: new Date().toISOString(),
          window: {
            ...windowInfo
          },
          count: typeof data?.count === 'number' ? data.count : undefined,
          latestTimestamp: typeof data?.latest_timestamp === 'string' ? data.latest_timestamp : undefined
        };

        const debugEnabled =
          ENV_DEBUG_FLAG ||
          toBoolean(config.debugOutput) ||
          toBoolean(payload.debugOutput ?? payload.debug) ||
          toBoolean(msg.debugOutput ?? msg.debug) ||
          toBoolean(msg.tesaiot?.debugOutput ?? msg.tesaiot?.debug);

        if (debugEnabled) {
          const telemetry = Array.isArray(data?.telemetry) ? data.telemetry : [];
          const preview = telemetry.slice(0, Math.min(telemetry.length, 5));

          this.debug(
            JSON.stringify(
              {
                deviceId,
                limit,
                start: params.start_time,
                end: params.end_time,
                count: typeof data?.count === 'number' ? data.count : telemetry.length,
                latestTimestamp: typeof data?.latest_timestamp === 'string' ? data.latest_timestamp : undefined,
                preview
              },
              null,
              2
            )
          );
        }

        send(msg);
        done();
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        this.status({ fill: 'red', shape: 'ring', text: 'error' });
        const safeError =
          error instanceof Error
            ? { message: error.message, name: error.name, stack: error.stack }
            : { message };

        this.error(message, msg);

        const fallbackWindow = {
          start: toIso(startDate),
          end: toIso(endDate),
          limit
        };

        msg.payload = {
          telemetry: [],
          error: message
        };
        msg.error = safeError;
        msg.metadata = {
          ...(msg.metadata || {}),
          source: 'tesaiot-device-data',
          deviceId,
          fetchedAt: new Date().toISOString(),
          window: fallbackWindow,
          error: message
        };

        send(msg);
        done(message);
      }
    });
  }

  RED.nodes.registerType('tesaiot-device-data', TesaiotDeviceData as any, {
    category: 'tesaiot',
    color: '#cc1f2f',
    inputs: 1,
    outputs: 1,
    icon: 'bridge.svg',
    paletteLabel: 'TESAIoT device data',
    defaults: {
      name: { value: '' },
      gateway: { value: '', required: true },
      limit: { value: 200 },
      debugOutput: { value: false }
    }
  } as any);
};

export = nodeInit;
