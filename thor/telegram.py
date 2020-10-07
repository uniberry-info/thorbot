from royalnet.typing import *
import asyncio
import logging
import royalnet.alchemist
import royalnet.baron
import os
from .database.base import Base

log = logging.getLogger(__name__)


async def main():
    log.info("Starting Alchemist...")
    alchemist: royalnet.alchemist.Alchemist = royalnet.alchemist.Alchemist(
        engine_args=[os.environ["SQLALCHEMY_DATABASE_URI"]],
        engine_kwargs={}
    )
    log.debug("Mapping database tables...")
    alchemist.add_metadata(Base.metadata)

    log.fatal("There isn't anything to do here yet.")


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
