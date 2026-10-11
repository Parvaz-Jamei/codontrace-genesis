"""Explicit CLI: engineering probes, journal verification or secure MQTT bridge."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from codontrace.swarm.experiments import run_seed
from codontrace.swarm.protocol import canonical
from codontrace.swarm.runtime import SwarmCoordinator


def _emit(message: str, *, flush: bool = False) -> None:
    sys.stdout.write(message + '\n')
    if flush:
        sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='mode', required=True)
    demo = sub.add_parser('probe'); demo.add_argument('--output', type=Path, required=True)
    demo.add_argument('--seeds', type=int, default=8); demo.add_argument('--samples', type=int, default=64)
    replay = sub.add_parser('replay'); replay.add_argument('--swarm-id', required=True); replay.add_argument('--journal', type=Path, required=True)
    mqtt = sub.add_parser('mqtt'); mqtt.add_argument('--swarm-id', required=True); mqtt.add_argument('--journal', type=Path, required=True)
    mqtt.add_argument('--host', required=True); mqtt.add_argument('--port', type=int, default=8883); mqtt.add_argument('--ca-file')
    serve = sub.add_parser('serve'); serve.add_argument('--host', default='127.0.0.1'); serve.add_argument('--port', type=int, default=8765)
    serve.add_argument('--swarm-id', default='lab'); serve.add_argument('--mqtt-host'); serve.add_argument('--mqtt-port', type=int, default=8883); serve.add_argument('--ca-file')
    args = parser.parse_args()
    if args.mode == 'probe':
        if not 1 <= args.seeds <= 256:
            parser.error('seeds must be 1..256')
        args.output.mkdir(parents=True, exist_ok=True)
        with (args.output/'metrics.jsonl').open('w', encoding='utf-8') as handle:
            for seed in range(args.seeds):
                for row in run_seed(seed, samples=args.samples):
                    handle.write(canonical(row)+'\n'); handle.flush()
                _emit(f'seed {seed+1}/{args.seeds} recorded', flush=True)
        (args.output/'manifest.json').write_text(json.dumps({'schema': 'swarm_probe_v1', 'synthetic': True,
            'seeds': args.seeds, 'samples': args.samples, 'physical_validation': False,
            'hypotheses_supported': None, 'scope': 'engineering_probes_only'}, indent=2))
    elif args.mode == 'serve':
        import threading

        from codontrace.console.server import make_server
        from codontrace.swarm.service import coordinator
        if args.host not in ('127.0.0.1', 'localhost', '::1') and not os.environ.get('CODONTRACE_API_TOKEN'):
            parser.error('network serving requires CODONTRACE_API_TOKEN')
        server = make_server(args.host, args.port)
        client = None
        stop = threading.Event()
        try:
            if args.mqtt_host:
                from codontrace.swarm.mqtt import MqttSwarmBridge
                username = os.environ.get('CODONTRACE_MQTT_USERNAME', '')
                password = os.environ.get('CODONTRACE_MQTT_PASSWORD', '')
                if not username or not password:
                    parser.error('MQTT credentials required')
                bridge = MqttSwarmBridge(coordinator(args.swarm_id))
                client = bridge.connect(args.mqtt_host, port=args.mqtt_port, username=username,
                                        password=password, ca_file=args.ca_file)
                client.loop_start()
                def dispatch() -> None:
                    import time
                    while not stop.wait(.25):
                        try:
                            bridge.drain(client, now_ms=int(time.time()*1000))
                        except (ValueError, OSError):
                            bridge.last_error = 'command_dispatch_failed'
                threading.Thread(target=dispatch, daemon=True).start()
            _emit(f'Swarm console: http://{args.host}:{server.server_address[1]}/swarm.html', flush=True)
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            stop.set(); server.server_close()
            if client is not None:
                client.loop_stop(); client.disconnect()
    elif args.mode == 'replay':
        swarm = SwarmCoordinator(args.swarm_id, journal=args.journal)
        _emit(canonical(swarm.snapshot(now_ms=swarm._state['now_ms'])))
    else:
        from codontrace.swarm.mqtt import MqttSwarmBridge
        username = os.environ.get('CODONTRACE_MQTT_USERNAME', '')
        password = os.environ.get('CODONTRACE_MQTT_PASSWORD', '')
        if not username or not password:
            parser.error('MQTT credential environment variables required')
        swarm = SwarmCoordinator(args.swarm_id, journal=args.journal)
        bridge = MqttSwarmBridge(swarm)
        client = bridge.connect(args.host, port=args.port, username=username, password=password, ca_file=args.ca_file)
        try:
            client.loop_forever()
        finally:
            client.disconnect()


if __name__ == '__main__':
    main()
