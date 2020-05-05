# This file dumps the logging info during oracle checking (semantic errors checking)
import datetime


class OracleCheckingLogger(object):

    def __init__(self, log_file_path):

        self.log_file_path = log_file_path
        self.log_file = open(self.log_file_path, "w")

    def start(self):

        current_datetime = datetime.datetime.now()
        start_msg = "[" + str(current_datetime) + "]\n"
        self.log_file.write(start_msg)

    def dump_log(self, msg):
        self.log_file.write(msg + "\n")

    def stop(self):
        self.log_file.flush()
        self.log_file.close()
