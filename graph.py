#!/usr/bin/env python3
#

import os
import sys
import json
import getopt
import subprocess
import classes.TonContract as TonContract
import lib.toolbox as toolbox

# Globals
#
config = None

def init(argv):
    configfile = None
    global config
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

        if not toolbox.check_path_writable(config["mining"]["graphs_path"]):
            toolbox.console_log("Mining graphs path does not exist or is not writable.")
            sys.exit(1)

def graph():
    global config

    if config["mining"]["enabled"]:
        toolbox.console_log("Generating mining graphs")

        givers = []
        for giver in config["mining"]["powGivers"]:
            givers.append(TonContract.TonContract(None, "powGiver", giver))

        for period in config["mining"]["periods"]:
            print("\t"+period["title"])
            print("\t\tBleed", end=" ")
            sys.stdout.flush()
            args = [
                config["rrdtool"]["bin"],
                "graph",
                config["mining"]["graphs_path"] + "/bleed_" + period["filename"] + ".png",
                "--start",
                period["offset"],
                "--width=800",
                "--height=200",
                "--title=Givers "+period["title"]+" bleed rate",
                "--vertical-label=Grams per second",
                "--font=DEFAULT:12:Courier New",
                "--font=TITLE:18:Courier New",
            ]

            for idx, giver in enumerate(givers):
                db_file = toolbox.get_giver_db_file(config["mining"]["database_path"], giver.get_shortname())
                args.append("DEF:"
                            + giver.get_shortname()
                            + "-bleed-avg-raw="
                            + db_file
                            + ":bleed:AVERAGE"
                            )

                args.append("CDEF:"
                            + giver.get_shortname()
                            + "-bleed-avg-positive="
                            + giver.get_shortname()
                            + "-bleed-avg-raw"
                            + ",-1,*"
                            )

                args.append("DEF:"
                            + giver.get_shortname()
                            + "-value-raw="
                            + db_file
                            + ":value:AVERAGE"
                            )

                args.append("DEF:"
                            + giver.get_shortname()
                            + "-value-last-raw="
                            + db_file
                            + ":value:LAST"
                            )

                args.append("VDEF:"
                            + giver.get_shortname()
                            + "-bleed-minimum-vdef="
                            + giver.get_shortname()
                            + "-bleed-avg-positive"
                            + ",MINIMUM"
                            )

                args.append("VDEF:"
                            + giver.get_shortname()
                            + "-bleed-average-vdef="
                            + giver.get_shortname()
                            + "-bleed-avg-positive"
                            + ",AVERAGE"
                            )

                args.append("VDEF:"
                            + giver.get_shortname()
                            + "-bleed-maximum-vdef="
                            + giver.get_shortname()
                            + "-bleed-avg-positive"
                            + ",MAXIMUM"
                            )

                args.append("CDEF:"
                            + giver.get_shortname()
                            + "-bleed-total-mod="
                            + giver.get_shortname()
                            + "-bleed-avg-positive"
                            + ",UN,"
                            + giver.get_shortname()
                            + "-bleed-average-vdef"
                            + ","
                            + giver.get_shortname()
                            + "-bleed-avg-positive"
                            + ",IF"
                            )

                args.append("VDEF:"
                            + giver.get_shortname()
                            + "-bleed-total-vdef="
                            + giver.get_shortname()
                            + "-bleed-total-mod"
                            + ",TOTAL"
                            )

                args.append("CDEF:"
                            + giver.get_shortname()
                            + "-time-to-live="
                            + giver.get_shortname()
                            + "-value-last-raw"
                            + ","
                            + giver.get_shortname()
                            + "-bleed-average-vdef"
                            + ",86400"
                            + ",*,/"
                            )

            string = "CDEF:all-bleed-average-positive="
            for idx, giver in enumerate(givers):
                if idx > 0:
                    string += ","
                string += giver.get_shortname() + "-bleed-avg-positive"

            for idx in range(0, len(givers)-1):
                string += ",+"
            args.append(string)

            string = "CDEF:all-bleed-total-positive="
            for idx, giver in enumerate(givers):
                if idx > 0:
                    string += ","
                string += giver.get_shortname() + "-bleed-total-mod"

            for idx in range(0, len(givers)-1):
                string += ",+"
            args.append(string)

            args.append("VDEF:"
                        + "all-bleed-total-vdef="
                        + "all-bleed-total-positive"
                        + ",TOTAL"
                        )

            string = "CDEF:all-value-total="
            for idx, giver in enumerate(givers):
                if idx > 0:
                    string += ","
                string += giver.get_shortname() + "-value-last-raw"

            for idx in range(0, len(givers)-1):
                string += ",+"
            args.append(string)

            args.append("CDEF:"
                        + "all-time-to-live="
                        + "all-value-total"
                        + ",all-bleed-average-positive"
                        + ",86400"
                        + ",*,/"
                        )

            args.append("VDEF:"
                        + "all-time-to-live-vdef="
                        + "all-time-to-live"
                        + ",AVERAGE"
                        )

            args.append("VDEF:"
                        + "all-bleed-average-positive-vdef="
                        + "all-bleed-average-positive"
                        + ",AVERAGE"
                        )

            for idx, giver in enumerate(givers):
                db_file = toolbox.get_giver_db_file(config["mining"]["database_path"], giver.get_shortname())
                if idx == 0:
                    args.append("COMMENT:"
                                +"Giver\t\t    Minimum  Average  Maximum\t  Est.Total\t      Balance\tDepleted in\\n"
                                )
                    args.append("COMMENT:------------------------------------------------------------------------------------------\\n")
                    stack = ""
                else:
                    stack = ":STACK"


                args.append("AREA:"
                            + giver.get_shortname()
                            + "-bleed-avg-positive"
                            + config["colorstack"][idx]
                            + ":"
                            + giver.get_shortname()
                            + "..."
                            + "   "
                            + stack
                            )

                args.append("GPRINT:"
                            + giver.get_shortname()
                            + "-bleed-minimum-vdef"
                            + ":%3.2lf"
                            + "   "
                            )
                args.append("GPRINT:"
                            + giver.get_shortname()
                            + "-bleed-average-vdef"
                            + ":%3.2lf"
                            + "  "
                            )
                args.append("GPRINT:"
                            + giver.get_shortname()
                            + "-bleed-maximum-vdef"
                            + ":%3.2lf"
                            + "    "
                            )

                args.append("GPRINT:"
                            + giver.get_shortname()
                            + "-bleed-total-vdef"
                            + ":%7.2lf"
                            + "  "
                            )

                args.append("GPRINT:"
                            + giver.get_shortname()
                            + "-value-last-raw"
                            + ":AVERAGE"
                            + ":%9.2lf"
                            + "\t"
                            )

                args.append("GPRINT:"
                            + giver.get_shortname()
                            + "-time-to-live"
                            + ":AVERAGE"
                            + ":   %4.0lf days"
                            + "\\n"
                            )

            args.append("HRULE:"
                        + "all-bleed-average-positive-vdef#ff0000"
                        )

            args.append("COMMENT:------------------------------------------------------------------------------------------\\n")
            args.append("GPRINT:"
                        + "all-bleed-average-positive-vdef"
                        + ":\t\t\t\t   "
                        + "%3.2lf"
                        + "\t\t"
                        )

            args.append("GPRINT:"
                        + "all-bleed-total-vdef"
                        + ":%7.2lf"
                        + " "
                        )

            args.append("GPRINT:"
                        + "all-value-total"
                        + ":AVERAGE"
                        + ":%9.2lf"
                        + "\t "
                        )

            args.append("GPRINT:"
                        + "all-time-to-live-vdef"
                        + ":   %4.0lf days"
                        + "\\n"
                        )
            args.append("COMMENT:TS\: "+toolbox.get_datetime_string().replace(':','\:')+"\\n")

            process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode:
               toolbox.console_log("Failure")
               toolbox.console_log(process.stdout.decode("utf-8"))
               toolbox.console_log(process.stderr.decode("utf-8"))
               sys.exit(1)

            print("Hashrate", end=" ")
            sys.stdout.flush()

            args = [
                config["rrdtool"]["bin"],
                "graph",
                config["mining"]["graphs_path"] + "/hashrate_" + period["filename"] + ".png",
                "--start",
                period["offset"],
                "--width=800",
                "--height=200",
                "--title=Estimated mining "+period["title"]+" hash rate",
                "--vertical-label=HPS",
                "--font=DEFAULT:12:Courier New",
                "--font=TITLE:18:Courier New",
            ]

            for idx, giver in enumerate(givers):
                db_file = toolbox.get_giver_db_file(config["mining"]["database_path"], giver.get_shortname())
                args.append("DEF:"
                            + giver.get_shortname()
                            + "-bleed-average-raw="
                            + db_file
                            + ":bleed:AVERAGE"
                            )

                args.append("CDEF:"
                            + giver.get_shortname()
                            + "-bleed-average-positive="
                            + giver.get_shortname()
                            + "-bleed-average-raw"
                            + ",-1,*"
                            )

                args.append("DEF:"
                            + giver.get_shortname()
                            + "-complexity-average="
                            + db_file
                            + ":complexity:AVERAGE"
                            )

                args.append("CDEF:"
                            + giver.get_shortname()
                            + "-hashrate="
                            + "100,"
                            + giver.get_shortname()
                            + "-bleed-average-positive"
                            + ",/"
                            )

            string = "CDEF:all-bleed="
            for idx, giver in enumerate(givers):
                if idx > 0:
                    string += ","
                string += giver.get_shortname() + "-bleed-average-positive"

            for idx in range(0, len(givers)-1):
                string += ",+"
            args.append(string)

            string = "CDEF:all-complexity-average="
            for idx, giver in enumerate(givers):
                if idx > 0:
                    string += ","
                string += giver.get_shortname() + "-complexity-average"

            string += ","+str(len(givers))
            string += ",AVG"
            args.append(string)

            string = "CDEF:all-hashrate="
            string += "all-complexity-average"
            string += ",100"
            string += ",all-bleed"
            string += ",/,/"
            args.append(string)

            args.append("VDEF:"
                        + "all-hashrate-average-vdef="
                        + "all-hashrate"
                        + ",AVERAGE"
                        )

            args.append("VDEF:"
                        + "all-hashrate-minimum-vdef="
                        + "all-hashrate"
                        + ",MINIMUM"
                        )

            args.append("VDEF:"
                        + "all-hashrate-maximum-vdef="
                        + "all-hashrate"
                        + ",MAXIMUM"
                       )

            args.append("HRULE:"
                        + "all-hashrate-average-vdef#ff0000"
                        )

            args.append("COMMENT:"
                        +"\t\t      Minimum       Average        Maximum\\n"
                        )
            args.append("COMMENT:------------------------------------------------------------------------------------------\\n")

            args.append("LINE1:"
                        + "all-hashrate"+config["colorstack"][0]
                        + ":Hashrate"
                        )

            args.append("GPRINT:"
                        + "all-hashrate-minimum-vdef"
                        + ":%2.6le"
                        + ""
                        )

            args.append("GPRINT:"
                        + "all-hashrate-average-vdef"
                        + ":%2.6le"
                        + ""
                        )

            args.append("GPRINT:"
                        + "all-hashrate-maximum-vdef"
                        + ":%2.6le"
                        + "\t\t\t\t\\n"
                        )
            args.append("COMMENT:TS\: "+toolbox.get_datetime_string().replace(':','\:')+"\\n")

            process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode:
               toolbox.console_log("Failure")
               toolbox.console_log(process.stdout.decode("utf-8"))
               toolbox.console_log(process.stderr.decode("utf-8"))
               sys.exit(1)

            print("Machines", end=" ")
            config["mining"]["machines"] = sorted(config["mining"]["machines"], key=lambda i: i['hashrate'])
            sys.stdout.flush()
            args = [
                config["rrdtool"]["bin"],
                "graph",
                config["mining"]["graphs_path"] + "/machines_" + period["filename"] + ".png",
                "--start",
                period["offset"],
                "--width=800",
                "--height=200",
                "--title=Estimated mining hashrate to hardware "+period["title"],
                "--vertical-label=Machines",
                "--font=DEFAULT:12:Courier New",
                "--font=TITLE:18:Courier New",
            ]

            for idx, giver in enumerate(givers):
                db_file = toolbox.get_giver_db_file(config["mining"]["database_path"], giver.get_shortname())
                args.append("DEF:"
                            + giver.get_shortname()
                            + "-bleed-average-raw="
                            + db_file
                            + ":bleed:AVERAGE"
                            )

                args.append("CDEF:"
                            + giver.get_shortname()
                            + "-bleed-average-positive="
                            + giver.get_shortname()
                            + "-bleed-average-raw"
                            + ",-1,*"
                            )

                args.append("DEF:"
                            + giver.get_shortname()
                            + "-complexity-average="
                            + db_file
                            + ":complexity:AVERAGE"
                            )

                args.append("CDEF:"
                            + giver.get_shortname()
                            + "-hashrate="
                            + "100,"
                            + giver.get_shortname()
                            + "-bleed-average-positive"
                            + ",/"
                            )

            string = "CDEF:all-bleed="
            for idx, giver in enumerate(givers):
                if idx > 0:
                    string += ","
                string += giver.get_shortname() + "-bleed-average-positive"

            for idx in range(0, len(givers)-1):
                string += ",+"
            args.append(string)

            string = "CDEF:all-complexity-average="
            for idx, giver in enumerate(givers):
                if idx > 0:
                    string += ","
                string += giver.get_shortname() + "-complexity-average"

            string += ","+str(len(givers))
            string += ",AVG"
            args.append(string)

            string = "CDEF:all-hashrate="
            string += "all-complexity-average"
            string += ",100"
            string += ",all-bleed"
            string += ",/,/"
            args.append(string)

            for idx, machine in enumerate(config["mining"]["machines"]):
                string = "CDEF:machine-"+str(idx)+"-qty="
                string += "all-hashrate"
                string += ","+str(machine["hashrate"])
                string += ",/"
                args.append(string)

                args.append("VDEF:"
                            + "machine-"+str(idx)+"-qty-average-vdef="
                            + "machine-"+str(idx)+"-qty"
                            + ",AVERAGE"
                            )

                args.append("VDEF:"
                            + "machine-"+str(idx)+"-qty-minimum-vdef="
                            + "machine-"+str(idx)+"-qty"
                            + ",MINIMUM"
                            )

                args.append("VDEF:"
                            + "machine-"+str(idx)+"-qty-maximum-vdef="
                            + "machine-"+str(idx)+"-qty"
                            + ",MAXIMUM"
                           )

            args.append("COMMENT:"
                        +"       \tMinimum   Average   Maximum\t  Hashrate\t  Config\\n"
                        )
            args.append("COMMENT:------------------------------------------------------------------------------------------\\n")

            for idx, machine in enumerate(config["mining"]["machines"]):
                args.append("HRULE:"
                            + "machine-"+str(idx)+"-qty-average-vdef"+machine["color"]
                            )

                args.append("LINE1:"
                            + "machine-"+str(idx)+"-qty"
                            + machine["color"]
                            + ":Machine "+str(idx+1)
                            )

                args.append("GPRINT:"
                            + "machine-"+str(idx)+"-qty-minimum-vdef"
                            + ": %4.2lf"
                            + "\t  "
                            )
                args.append("GPRINT:"
                            + "machine-"+str(idx)+"-qty-average-vdef"
                            + ":%4.2lf"
                            + "\t "
                            )
                args.append("GPRINT:"
                            + "machine-"+str(idx)+"-qty-maximum-vdef"
                            + ":%4.2lf"
                            + "\t"
                            )
                args.append("COMMENT:{:e}".format(machine["hashrate"])+"  ")
                args.append("COMMENT:"+machine["config"]+"\\n")

            args.append("COMMENT:TS\: "+toolbox.get_datetime_string().replace(':','\:')+"\\n")

            process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if process.returncode:
               toolbox.console_log("Failure")
               toolbox.console_log(process.stdout.decode("utf-8"))
               toolbox.console_log(process.stderr.decode("utf-8"))
               sys.exit(1)

            print("")

def print_usage():
    print('Usage: ')
    print('graph.py --config <configfile>')

if __name__ == '__main__':
    init(sys.argv[1:])
    graph()