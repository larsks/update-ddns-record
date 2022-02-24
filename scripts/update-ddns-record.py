#!/usr/bin/python2

# Python-2 compatible update script for use on EdgeRouter's and similar
# devices.

import argparse
import json
import logging
import os
import time
import urllib

from contextlib import closing

LOG = logging.getLogger(__name__)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "-f", "--force", action="store_true", default=os.getenv("DDNS_FORCE")
    )
    p.add_argument("-t", "--token", default=os.getenv("DDNS_TOKEN"))
    p.add_argument("-T", "--token-file", default=os.getenv("DDNS_TOKEN_FILE"))
    p.add_argument("-U", "--url", default=os.getenv("DDNS_URL"))
    p.add_argument("-H", "--hostname", default=os.getenv("DDNS_HOSTNAME"))
    p.add_argument("-v", "--verbose", action="count", default=0)
    p.add_argument(
        "-l",
        "--last-update-file",
        default=os.getenv("DDNS_LAST_UPDATE_FILE", "/run/ddns_last_update"),
    )
    p.add_argument(
        "-m",
        "--max-interval",
        type=int,
        default=os.getenv("DDNS_MAX_INTERVAL", "86400"),
    )
    p.add_argument("--old-ip-address", default=os.getenv("old_ip_address"))
    p.add_argument("--new-ip-address", default=os.getenv("new_ip_address"))
    return p.parse_args()


def ip_address_changed(args):
    res = args.old_ip_address != args.new_ip_address
    LOG.debug("ip address %s changed", "has" if res else "has not")
    return res


def get_last_update(path):
    try:
        with open(path, "r") as fd:
            try:
                lastupdate = float(fd.read().strip())
            except ValueError as err:
                LOG.warning("invalid last update data: %s", err)
                lastupdate = 0
    except IOError as err:
        LOG.warning("failed to read last update: %s", err)
        lastupdate = 0

    LOG.debug("last update was at %s", time.ctime(lastupdate))
    return lastupdate


def too_long_since_last_update(args):
    lastupdate = get_last_update(args.last_update_file)
    delta = time.time() - lastupdate
    res = delta >= args.max_interval
    LOG.debug("%stoo long since last update", "" if res else "not ")
    return res


def main():
    args = parse_args()
    loglevel = ["WARNING", "INFO", "DEBUG"][min(args.verbose, 2)]
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=loglevel,
    )

    if args.token:
        token = args.token
    elif args.token_file:
        with open(args.token_file) as fd:
            token = fd.read().strip()
    else:
        raise ValueError("missing token")

    if args.hostname is None:
        raise ValueError("missing hostname")

    if args.url is None:
        raise ValueError("missing url")

    if ip_address_changed(args) or too_long_since_last_update(args) or args.force:
        qs = urllib.urlencode({"hostname": args.hostname, "token": token})
        url = "{}?{}".format(args.url, qs)
        fd = urllib.urlopen(url)
        with closing(fd):
            res = json.loads(fd.read())
        if res["Status"] == "success":
            LOG.info("updated address for %s to %s", args.hostname, res["Address"])
            with open(args.last_update_file, "w") as fd:
                fd.write("{}".format(time.time()))
        else:
            LOG.error(
                "failed to update address for %s: %s",
                args.hostname,
                res.get("Message", "unknown error"),
            )
    else:
        LOG.info("not updating address for %s", args.hostname)


if __name__ == "__main__":
    main()
