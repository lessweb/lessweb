from lessweb.utils import scan_import

if __name__ == '__main__':
    ret = scan_import(('lessweb', 'tests'))
    for k, v in ret.items():
        print(k, v)
