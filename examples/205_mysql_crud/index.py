from lessweb.bridge import Bridge
from commondao.mapper import mysql_startup, mysql_cleanup, mysql_connect


def start_server():
    bridge = Bridge('config.toml')
    bridge.add_mod_ctx(mysql_startup, mysql_cleanup)
    bridge.add_middleware(mysql_connect)
    bridge.add_route_scan('myapp.endpoint')
    bridge.run_app()


if __name__ == '__main__':
    start_server()