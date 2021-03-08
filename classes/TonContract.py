import re


class TonContract:
    def __init__(self, lite_client, contract_type, address):
        self.lc = lite_client
        self.type = contract_type
        self.address = address
        self.value = None
        self.params = {
            "pow": {
                "seed": None,
                "complexity": None,
                "iterations": None
            }
        }

    def get_value_grams(self):
        if self.value is None:
            return None
        else:
            return int(self.value) / 10 ** 9

    def get_shortname(self):
        return self.address[0:8]

    def get_pow_string(self):
        return "{} {} {}".format(
            self.params["pow"]["seed"],
            self.params["pow"]["complexity"],
            self.params["pow"]["iterations"]
        )

    def get_pow_complexity(self):
        return (2 ** 256) / self.params["pow"]["complexity"]

    def refresh_all(self):
        self.refresh_value()
        if self.type == "powGiver":
            self.refresh_params_pow()

    def refresh_value(self):
        out = self.lc.exec("getaccount {}".format(self.address))
        self.value = self.lc.parse_output(out, ["balance","grams","value"])

    def refresh_params_pow(self):
        out = self.lc.exec("runmethod {} get_pow_params".format(self.address))
        if out:
            out = self.lc.parse_output(out, "result")
            if out:
                out = re.match(r'^\s+?\[\s*(.+) ]', out, re.M | re.I)
                if out:
                    out = out[1].split()
                    self.params["pow"]["seed"] = int(out[0])
                    self.params["pow"]["complexity"] = int(out[1])
                    self.params["pow"]["iterations"] = int(out[2])

    # end define
# end class
