import subprocess

class LiteClient:
    def __init__(self, config):
        self.config = config

    def exec(self, cmd):
        verbosity = "0"
        if self.config["mode"] == "config":
            args = [self.config["bin"], "--global-config", self.config["config"],
                    "--verbosity", verbosity, "--cmd", cmd]
        else:
            args = [self.config["bin"], "--pub", self.config["certificate"],
                    "--addr", self.config["address"], "--verbosity", verbosity, "--cmd", cmd]
        process = subprocess.run(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 timeout=self.config["timeout"])
        output = process.stdout.decode("utf-8")
        err = process.stderr.decode("utf-8")
        if len(err) > 0:
            raise Exception("LiteClient error: {err}".format(err=err))

        return output

    # Based on code by https://github.com/igroman787/mytonctrl
    #
    def parse_output(self, text, path):
        result = None
        if path is None or text is None:
            return None

        if not isinstance(path, list):
            path = [path]

        for idx, element in enumerate(path):
            if ':' not in element:
                element += ':'
            if element not in text:
                break

            start = text.find(element) + len(element)
            count = 0
            bcount = 0
            textLen = len(text)
            end = textLen
            for i in range(start, textLen):
                letter = text[i]
                if letter == '(':
                    count += 1
                    bcount += 1
                elif letter == ')':
                    count -= 1
                if letter == ')' and count < 1:
                    end = i + 1
                    break
                elif letter == '\n' and count < 1:
                    end = i
                    break
            text = text[start:end]
            if count != 0 and bcount == 0:
                text = text.replace(')', '')

            if idx+1 == len(path):
                result = text

        return result
    # end define
# end class
