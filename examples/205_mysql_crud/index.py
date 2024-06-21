from commondao.mapper import mysql_cleanup, mysql_connect, mysql_startup

from lessweb.bridge import Bridge


def start_server():
    bridge = Bridge('config.toml')
    bridge.add_config_ctx(mysql_startup, mysql_cleanup)
    bridge.add_middleware(mysql_connect)
    bridge.add_route_scan('myapp.endpoint')
    bridge.run_app()


if __name__ == '__main__':
    start_server()
