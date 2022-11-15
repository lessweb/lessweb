from lessweb.bridge import post_mapping
from myapp.mapper import CommonDao


@post_mapping('/pet')
async def create_pet(pet: dict, /, common_dao: CommonDao):
    await common_dao.insert_pet(**pet)
    return {}
