import time

from sqlalchemy.orm import Session

from models.data_dump import DataDump, DumpType


class DataDumpStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_data_dump(self, dump_type: DumpType, data: dict) -> DataDump:
        data_dump = DataDump(type=dump_type, data=data, created_at=int(time.time()))

        self.session.add(data_dump)

        return data_dump
