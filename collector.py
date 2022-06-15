#!/usr/bin/env python3
#
import sys
import os
import getopt
import json
import time
import subprocess
import classes.LiteClient as LiteClient
import classes.TonContract as TonContract
import lib.toolbox as toolbox

# Globals
#
config = None
lc = None


def init(argv):
    configfile = None
    global config, lc
    # Process input parameters
    opts, args = getopt.getopt(argv, "hc:", ["config="])
    for opt, arg in opts:
        if opt == '-h':
            print_usage()
            sys.exit(0)
        elif opt in ("-c", "--config"):
            configfile = arg
            if not os.access(configfile, os.R_OK):
                print("Configuration file " + configfile + " could not be opened")
                sys.exit(1)
    # end for

    if not configfile:
        print_usage()
        sys.exit(1)

    configfile = open(configfile, 'r')
    config = json.loads(configfile.read())
    configfile.close()

    if config["mining"]["enabled"]:
        if not toolbox.check_path_writable(config["mining"]["database_path"]):
            toolbox.console_log("Mining database path does not exist or is not writable.")
            sys.exit(1)

    if config["accounting"]["enabled"]:
        if not toolbox.check_path_writable(config["accounting"]["database_path"]):
            toolbox.console_log("Accounting database path does not exist or is not writable.")
            sys.exit(1)

    lc = LiteClient.LiteClient(config["liteClient"])


def collector():
    global config, lc

    toolbox.console_log("Starting collector")

    givers = []
    if config["mining"]["enabled"]:
        for giver in config["mining"]["powGivers"]:
            givers.append(TonContract.TonContract(lc, "powGiver", giver))

    miners = {}
    if config["accounting"]["enabled"]:
        for miner in config["accounting"]["miners"].keys():
            wallets = []
            for wallet in config["accounting"]["miners"][miner]:
                wallets.append(TonContract.TonContract(lc, "wallet", wallet))

            miners[miner] = wallets

    ts_complexity = 0
    ts_value = 0
    ts_accounting = 0
    while True:

        if givers:
            ## Check for DB, create if needed
            ##
            for giver in givers:
                file = toolbox.get_giver_db_file(config["mining"]["database_path"], giver.get_shortname())
                if not toolbox.check_file_exists(file):
                    toolbox.console_log("Creating giver DB {}".format(file))
                    args = [
                        config["rrdtool"]["bin"],
                        "create",
                        file,
                        "--start",
                        str(round(time.time())),
                        "DS:value:GAUGE:300:U:U",
                        "DS:bleed:DERIVE:300:U:U",
                        "DS:complexity:GAUGE:300:0:U",
                        "RRA:AVERAGE:0.5:288:1095",
                        "RRA:AVERAGE:0.5:100:1080",
                        "RRA:AVERAGE:0.5:24:1080",
                        "RRA:AVERAGE:0.5:8:1008",
                        "RRA:AVERAGE:0.5:2:1008",
                        "RRA:AVERAGE:0.5:1:1008",
                        "RRA:MIN:0.5:288:1095",
                        "RRA:MIN:0.5:100:1080",
                        "RRA:MIN:0.5:24:1080",
                        "RRA:MIN:0.5:8:1008",
                        "RRA:MIN:0.5:2:1008",
                        "RRA:MIN:0.5:1:1008",
                        "RRA:MAX:0.5:288:1095",
                        "RRA:MAX:0.5:100:1080",
                        "RRA:MAX:0.5:24:1080",
                        "RRA:MAX:0.5:8:1008",
                        "RRA:MAX:0.5:2:1008",
                        "RRA:MAX:0.5:1:1008"
                    ]
                    process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if process.returncode:
                        toolbox.console_log("Failure")
                        toolbox.console_log(process.stdout.decode("utf-8"))
                        toolbox.console_log(process.stderr.decode("utf-8"))
                        sys.exit(1)

            update = False
            if (time.time() - ts_complexity) > config["mining"]["intervals"]["complexity"]:
                toolbox.console_log("Refreshing givers complexity")
                ts_complexity = time.time()
                for giver in givers:
                    giver.refresh_params_pow()
                update = True

            if (time.time() - ts_value) > config["mining"]["intervals"]["value"]:
                toolbox.console_log("Refreshing givers value")
                ts_value = time.time()
                for giver in givers:
                    giver.refresh_value()
                update = True

            if update:
                toolbox.console_log("Updating databases")
                for giver in givers:
                    if giver.get_pow_complexity() is not None:
                        file = toolbox.get_giver_db_file(config["mining"]["database_path"], giver.get_shortname())
                        args = [
                            config["rrdtool"]["bin"],
                            "update",
                            file,
                            "N:{}:{}:{}".format(int(giver.get_value_grams()),int(giver.get_value_grams()),int(giver.get_pow_complexity()))
                        ]

                        process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        if process.returncode:
                            toolbox.console_log("Failure")
                            toolbox.console_log(process.stdout.decode("utf-8"))
                            toolbox.console_log(process.stderr.decode("utf-8"))
                            sys.exit(1)
                        update = False

        if miners:
            ## Check for DB, create if needed
            ##
            for miner in miners.keys():
                file = toolbox.get_giver_db_file(config["accounting"]["database_path"], miner)
                if not toolbox.check_file_exists(file):
                    toolbox.console_log("Creating miner DB {}".format(file))
                    args = [
                        config["rrdtool"]["bin"],
                        "create",
                        file,
                        "--start",
                        str(round(time.time())),
                        "DS:value:GAUGE:14400:U:U",
                        "DS:increase:DERIVE:14400:U:U",
                        "RRA:AVERAGE:0.5:8:1008",
                        "RRA:AVERAGE:0.5:2:1008",
                        "RRA:AVERAGE:0.5:1:1008",
                        "RRA:MIN:0.5:8:1008",
                        "RRA:MIN:0.5:2:1008",
                        "RRA:MIN:0.5:1:1008",
                        "RRA:MAX:0.5:8:1008",
                        "RRA:MAX:0.5:2:1008",
                        "RRA:MAX:0.5:1:1008"
                    ]
                    process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if process.returncode:
                        toolbox.console_log("Failure")
                        toolbox.console_log(process.stdout.decode("utf-8"))
                        toolbox.console_log(process.stderr.decode("utf-8"))
                        sys.exit(1)

            update = False
            if (time.time() - ts_accounting) > config["accounting"]["intervals"]["value"]:
                toolbox.console_log("Refreshing accounting")
                ts_accounting = time.time()
                for miner in miners.keys():
                    for wallet in miners[miner]:
                        wallet.refresh_value()
                update = True

            if update:
                toolbox.console_log("Updating databases")
                for miner in miners.keys():
                    total = 0
                    for wallet in miners[miner]:
                        if wallet.get_value_grams():
                            total += wallet.get_value_grams()

                    file = toolbox.get_giver_db_file(config["accounting"]["database_path"], miner)
                    args = [
                        config["rrdtool"]["bin"],
                        "update",
                        file,
                        "N:{}:{}".format(int(total),int(total))
                    ]

                    process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if process.returncode:
                        toolbox.console_log("Failure")
                        toolbox.console_log(process.stdout.decode("utf-8"))
                        toolbox.console_log(process.stderr.decode("utf-8"))
                        sys.exit(1)
                    update = False

        time.sleep(1)

def print_usage():
    print('Usage: ')
    print('collector.py --config <configfile>')


if __name__ == '__main__':
    init(sys.argv[1:])
    collector()
