from lessweb.bridge import get_mapping
from myapp.mapper import CommonDao


@get_mapping('/pet/{pet_id}')
async def get_pet_detail(common_dao: CommonDao, *, pet_id: int):
    return await common_dao.get_pet_by_pet_id(pet_id)
