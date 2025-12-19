import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from aiohttp_middlewares.cors import cors_middleware

from lessweb import Bridge
from shared.error_middleware import error_middleware
from shared.jwt_gateway import JwtGatewayMiddleware
from shared.lessweb_commondao import MysqlConn, commondao_bean
from shared.redis_plugin import redis_bean

OPENAPI_FILE = Path('openapi/openapi.json')


def update_openapi(components: dict) -> None:
    """Update OpenAPI specification file with new components."""
    with OPENAPI_FILE.open('r') as f:
        openapi_json = json.load(f)

    openapi_json.update(components)

    with OPENAPI_FILE.open('w') as f:
        json.dump(openapi_json, f, indent=2, ensure_ascii=False)


def setup_bridge() -> Bridge:
    """Initialize and configure the Bridge instance."""
    bridge = Bridge('config')

    # Serve openapi directory as static files in staging environment
    env = os.environ.get('ENV', '')
    if env == 'staging':
        if Path('openapi').exists():
            bridge.app.router.add_static(prefix='/openapi/', path='openapi', show_index=True)

    bridge.beans(commondao_bean, redis_bean)
    bridge.middlewares(
        cors_middleware(allow_all=True),
        error_middleware,
        JwtGatewayMiddleware,
        MysqlConn,
    )
    bridge.scan('src')
    return bridge


def setup_pyway_env(bridge: Bridge) -> dict:
    """Setup environment variables for pyway from bridge config."""
    mysql_config = bridge.config['mysql']

    env = os.environ.copy()
    env['PYWAY_DATABASE_HOST'] = str(mysql_config['host'])
    env['PYWAY_DATABASE_PORT'] = str(mysql_config['port'])
    env['PYWAY_DATABASE_USERNAME'] = str(mysql_config['user'])
    env['PYWAY_DATABASE_PASSWORD'] = str(mysql_config['password'])
    env['PYWAY_DATABASE_NAME'] = str(mysql_config['db'])

    print(f"Connecting to: {env['PYWAY_DATABASE_HOST']}:{env['PYWAY_DATABASE_PORT']} as {env['PYWAY_DATABASE_USERNAME']}")

    return env


def pyway_init(bridge: Bridge, schema_file: str) -> None:
    """Initialize pyway by importing schema and validating."""
    env = setup_pyway_env(bridge)

    # Import schema
    print(f"Importing schema from {schema_file}...")
    result = subprocess.run(
        ['pyway', 'import', '--schema-file', schema_file],
        env=env,
        capture_output=False
    )
    if result.returncode != 0:
        sys.exit(result.returncode)

    # Validate
    print("Validating...")
    result = subprocess.run(['pyway', 'validate'], env=env, capture_output=False)
    sys.exit(result.returncode)


def pyway_migrate(bridge: Bridge) -> None:
    """Run pyway migration."""
    env = setup_pyway_env(bridge)

    result = subprocess.run(['pyway', 'migrate'], env=env, capture_output=False)
    sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description='My SaaS Skeleton')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Subcommand: run (default)
    subparsers.add_parser('run', help='Run the web application (default)')

    # Subcommand: dump-openapi
    subparsers.add_parser('dump-openapi', help='Dump OpenAPI components and exit')

    # Subcommand: pyway-init
    pyway_init_parser = subparsers.add_parser('pyway-init', help='Initialize pyway (import schema and validate)')
    pyway_init_parser.add_argument('schema_file', help='SQL file name to import (e.g., V01_01_01__init_tables.sql)')

    # Subcommand: pyway-migrate
    subparsers.add_parser('pyway-migrate', help='Run pyway database migration')

    args = parser.parse_args()

    # Default to 'run' if no command specified
    command = args.command or 'run'

    bridge = setup_bridge()

    if command == 'dump-openapi':
        components = bridge.dump_openapi_components()
        update_openapi(components)
        print(f'OpenAPI components dumped to {OPENAPI_FILE}')
    elif command == 'pyway-init':
        pyway_init(bridge, args.schema_file)
    elif command == 'pyway-migrate':
        pyway_migrate(bridge)
    else:  # 'run'
        components = bridge.dump_openapi_components()
        update_openapi(components)
        bridge.run_app()


if __name__ == '__main__':
    main()
