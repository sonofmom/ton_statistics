import re
import subprocess
import sys
import time


class TonNetwork:
    def __init__(self, lite_client):
        self.lc = lite_client
    # end define

    def get_pow_params(self, address):
        result = None

        out = self.lc.get_var(
            self.lc.exec("runmethod {} get_pow_params".format(address)),
            "result")

        if out:
            out = re.match(r'^\s+?\[\s*(.+) ]', out, re.M|re.I)
            if out:
                result = out[1]

        return result

    def get_pow_difficulty_average(self, contracts):
        return round(sum(self.get_pow_difficulty(pow["params"]) for pow in self.config["powMap"]) / len(self.config["powMap"]))

    def get_pow_hashrate(self):
        return self.get_pow_results(self.config["powMap"][0]["params"], self.config["durations"]["hashrate_check"], self.config["powMiner"]["threads"])[1]

    def get_pow_results(self, pow_params, duration, threads):
        result = [None,None]

        pow_params = pow_params.split()
        args = [
            self.config["powMiner"]["bin"],
            "-vv",
            "-w"+str(threads),
            "-t"+str(duration),
            "kf_kUHS5Q8lQXb7O-3tmLtxNcwpDIhFDwaTc84vlyb6lW1GW",
            pow_params[0],
            pow_params[1],
            pow_params[2]
        ]

        process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = process.stdout.decode("utf-8")
        err = process.stderr.decode("utf-8")

        if err:
            difficulty = re.match(r'.+for success: (\d+)', err, re.M | re.I)
            if difficulty:
                result[0] = int(difficulty[1])

            speed = re.match(r'.+speed: (.+) hps.+', err, re.MULTILINE | re.DOTALL)
            if speed:
                result[1] = round(float(speed[1]))
        return result

    def get_pow_difficulty(self, pow_params):
        pow_params = pow_params.split()
        return (2 ** 256) / int(pow_params[1])

    def rebuild_pow_map(self):
        for pow in self.config["powContracts"]:
            i = next((index for (index, d) in enumerate(self.config["powMap"]) if d["addr"] == pow), None)
            if i is None:
                record = {}
                record["addr"] = pow
                record["params"] = self.get_pow_params(pow)
                self.config["powMap"].append(record)
            else:
                self.config["powMap"][i]["params"] = self.get_pow_params(pow)

    def get_wallet_value(self, wallet):
        storage = self.lc.exec("getaccount %s" % wallet)
        if storage is None:
            return 0
        balance = self.lc.get_var(storage, "balance")
        grams = self.lc.get_var(balance, "grams")
        value = self.lc.get_var(grams, "value")
        return self.ng2g(value)

    def ng2g(self, grams):
        return int(grams)/10**9

    def create_wallet(self):
        result = {"wallet": None, "file": str(time.time()) }

        args = [
            self.config["fift"]["bin"],
            "-I"+self.config["fift"]["includes"],
            "-s",
            "new-wallet.fif",
            "-1",
            self.config["wallets"]["wallets_path"]+"/"+result["file"]
        ]

        process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = process.stdout.decode("utf-8")
        err = process.stderr.decode("utf-8")
        if output:
            result["wallet"] = re.match(r'.+\(for init\): ([\w|_|-]+)\s', output, re.MULTILINE | re.DOTALL)[1]
            addr = re.match(r'.+\(for later access\): ([\w|_|-]+)\s', output, re.MULTILINE | re.DOTALL)[1]

            log = open(self.config["wallets"]["wallets_path"]+"/index.txt", "a")
            log.write(result["file"]+"\n")
            log.write(result["wallet"]+"\n")
            log.write(addr+"\n\n")
            log.close()
        return result


# end class
