from google.cloud import storage
from google.cloud import tasks_v2
import asyncio
import re

cf = "https://wowless-pxnmni7wma-uc.a.run.app/wowless"
fre = re.compile(r"addons/(\d+)-(\w+).zip$")
parent = "projects/www-wowless-dev/locations/us-central1/queues/wowless"
sa = "wowless-invoker@www-wowless-dev.iam.gserviceaccount.com"
products = {
    "Mainline": "wow",
    "TBC": "wow_classic",
    "Vanilla": "wow_classic_era",
}


def parse_filename(name):
    match = fre.search(name)
    if match is None:
        return None
    addon, version = match.group(1, 2)
    return products[version], addon


async def do_publish():
    tasks_client = tasks_v2.CloudTasksAsyncClient()
    async for _ in await tasks_client.list_tasks(parent=parent):
        print("tasks are present, so nothing to do")
        return
    print("creating tasks...")
    await asyncio.gather(
        *[
            tasks_client.create_task(
                parent=parent,
                task={
                    "http_request": {
                        "oidc_token": {
                            "audience": cf,
                            "service_account_email": sa,
                        },
                        "url": f"{cf}?product={prod}&addon={addon}&loglevel=1",
                    }
                },
            )
            for (prod, addon) in filter(
                lambda x: x is not None,
                map(
                    parse_filename,
                    [
                        x.name
                        for x in storage.Client().list_blobs(
                            "wowless.dev", prefix="addons/"
                        )
                    ],
                ),
            )
        ]
    )
    print("created tasks")


def publish(_):
    asyncio.run(do_publish())
    return ""


if __name__ == "__main__":
    publish(None)
