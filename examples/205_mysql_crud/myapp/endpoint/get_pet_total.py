from lessweb.bridge import get_mapping
from myapp.mapper import CommonDao


@get_mapping('/pet-total')
async def get_pet_total(common_dao: CommonDao, kind: str):
    return await common_dao.select_all('select count(*) as total, kind from tbl_pet group by kind where kind=:kind', {'kind': kind})
