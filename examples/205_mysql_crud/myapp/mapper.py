from commondao.mapper import Mapper
from datetime import datetime, date
from lessweb.bridge import service


@service
class CommonDao(Mapper):
    async def insert_pet(
        self,
        pet_id: int = None,  # 
        name: str = None,  # 
        kind: str = None,  # 
        create_time: datetime = None,  # 

    ):
        data = {
            'pet_id': pet_id,
            'name': name,
            'kind': kind,
            'create_time': create_time,

        }
        return await self.save('tbl_pet', data=data)
    
    async def select_pet(self, query, select_clause: str = '*', extra: dict = None):
        return await self.select_by_query('tbl_pet', query, select_clause, extra)
    
    async def update_pet_by_pet_id(
        self,
        pet_id: int,  # 
        name: str = None,  # 
        kind: str = None,  # 
        create_time: datetime = None,  # 

    ):
        data = {
            'name': name,
            'kind': kind,
            'create_time': create_time,

        }
        key = {
            'pet_id': pet_id,

        }
        return await self.update_by_key('tbl_pet', key=key, data=data)
    
    async def delete_pet_by_pet_id(
        self,
        pet_id: int,  # 

    ):
        key = {
            'pet_id': pet_id,

        }
        return await self.delete_by_key('tbl_pet', key=key)
    
    async def get_pet_by_pet_id(
        self,
        pet_id: int,  # 

    ):
        key = {
            'pet_id': pet_id,

        }
        return await self.get_by_key('tbl_pet', key=key)


